import pandas as pd
from datetime import datetime
from src import config
from src.db.database import SessionLocal, engine
from src.db.models import VehicleMaster, SalesHistory, SQLModel
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.data_processing.scraper import enrich_vehicle_data
from src.utils import normalize_text

def run_phase1_extract_all_vehicles() -> pd.DataFrame:
    """
    フェーズ1: inputフォルダ内の全PDFを解析し、「重複を含む」全車両データを返す
    """
    all_vehicles = []
    
    pdf_files = list(config.AUCTION_SHEETS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print("警告: data/input/auction_sheets/ ディレクトリにPDFファイルが見つかりません。")
        return pd.DataFrame()

    print(f"{len(pdf_files)}個のPDFファイルを処理します...")

    for pdf_path in pdf_files:
        print(f"  - 解析中: {pdf_path.name}")
        extracted_data = extract_vehicles_from_pdf(pdf_path)
        all_vehicles.extend(extracted_data)

    if not all_vehicles:
        print("警告: PDFから車両データを1件も抽出できませんでした。")
        return pd.DataFrame()

    df = pd.DataFrame(all_vehicles)
    df = df[df['maker'] != 'メーカー'].copy()
    
    # ▼▼▼ maker, car_name, model_code の3つすべてを正規化 ▼▼▼
    for col in ['maker', 'car_name', 'model_code']:
        if col in df.columns:
            df[col] = df[col].apply(normalize_text)

    return df

# run_phase2_enrich_dataは不要になるため削除（または後述のenrich_database.pyに移動）

def run_phase3_update_database(all_vehicles_df: pd.DataFrame, unique_vehicles_df: pd.DataFrame) -> pd.DataFrame:
    """
    フェーズ3: データベースを更新し、落札実績を集計して最終的なリストを返す
    """
    print("  - データベースの更新と落札実績の集計を開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        # 1. 既存の車種マスターを辞書として一度に読み込む
        existing_vehicles = {v.model_code: v for v in session.query(VehicleMaster).all()}
        print(f"  - 既存の車種マスター（{len(existing_vehicles)}件）を読み込みました。")

        # 2. PDF由来のデータをデータベースに追加・更新
        for record in unique_vehicles_df.to_dict('records'):
            model_code = record.get('model_code')
            if not model_code: continue
            
            # 既存か新規かチェック
            vehicle = existing_vehicles.get(model_code)
            if vehicle:
                # 既存の場合は出品回数を更新
                vehicle.updated_at = datetime.utcnow()
            else:
                # 新規の場合は追加
                vehicle = VehicleMaster(**{k: v for k, v in record.items() if k in VehicleMaster.__fields__})
                session.add(vehicle)
                existing_vehicles[model_code] = vehicle

        # 3. 落札実績にしかいない車種をデータベースに追加
        sales_only_query = session.query(
            SalesHistory.maker, SalesHistory.car_name, SalesHistory.model_code
        ).distinct()
        
        for sale in sales_only_query.all():
            if sale.model_code not in existing_vehicles:
                vehicle = VehicleMaster(
                    maker=sale.maker, car_name=sale.car_name, model_code=sale.model_code, appearance_count=0
                )
                session.add(vehicle)
                existing_vehicles[sale.model_code] = vehicle

        # 4. すべての変更を一度にDBに書き込む
        session.commit()
        print("  - 車種マスターの更新が完了しました。")

        # 5. 出品回数を集計して反映
        appearance_counts = all_vehicles_df.groupby('model_code').size().reset_index(name='appearance_count')
        for record in appearance_counts.to_dict('records'):
            vehicle = session.query(VehicleMaster).filter_by(model_code=record['model_code']).first()
            if vehicle:
                vehicle.appearance_count = record['appearance_count']
        session.commit()

        # 6. 最終的な結果を生成
        sales_counts_df = pd.read_sql("SELECT model_code, COUNT(id) as sales_count FROM saleshistory GROUP BY model_code", engine)
        final_master_df = pd.read_sql("SELECT * FROM vehiclemaster", engine)
        final_output_df = pd.merge(final_master_df, sales_counts_df, on='model_code', how='left')
        final_output_df['sales_count'] = final_output_df['sales_count'].fillna(0).astype(int)

    finally:
        session.close()

    return final_output_df