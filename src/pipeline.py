# src/pipeline.py

import pandas as pd
from pathlib import Path
# 変更後
from src import config
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.data_processing.scraper import enrich_vehicle_data

def run_phase1_extract_all_vehicles() -> pd.DataFrame:
    """
    フェーズ1: inputフォルダ内の全PDFを解析し、ユニークな車種マスターリストを作成する
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
    
    # drop_duplicates を削除し、全データをそのまま返す
    return df

# ▼▼▼ この関数が不足していました ▼▼▼
def run_phase2_enrich_data(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    フェーズ2 (模擬): AI処理と待機時間をスキップし、受け取ったデータをそのまま返す
    """
    print("  - [スキップ] AIによるデータ拡充処理をスキップします。")
    
    # AIで取得するはずだった列を、空の状態で追加しておく
    # これにより、後のフェーズ3がエラーなく動作する
    master_df['weight_kg'] = None
    master_df['engine_model'] = None
    master_df['catalyst_model'] = None
    
    return master_df

import pandas as pd
from datetime import datetime
from src import config
from src.db.database import SessionLocal, engine
from src.db.models import VehicleMaster, SalesHistory, SQLModel

# ... (run_phase1 と run_phase2 は変更なし) ...

def run_phase3_update_database(all_vehicles_df: pd.DataFrame, enriched_df: pd.DataFrame) -> pd.DataFrame:
    """
    フェーズ3: データベースを更新し、落札実績を集計して最終的なリストを返す
    """
    print("  - データベースの更新と落札実績の集計を開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        # --- 1. 既存の車種マスターを辞書として一度に読み込む ---
        existing_vehicles_db = {v.model_code: v for v in session.query(VehicleMaster).all()}
        print(f"  - 既存の車種マスター（{len(existing_vehicles_db)}件）を読み込みました。")

        # --- 2. 今回のPDFから更新・追加すべきデータを準備 ---
        key_cols = ['maker', 'car_name', 'model_code']
        appearance_counts = all_vehicles_df.groupby(key_cols).size().reset_index(name='new_appearance_count')
        update_data_from_pdf = pd.merge(enriched_df, appearance_counts, on=key_cols, how="left")

        # --- 3. メモリ上で更新・追加処理を行う ---
        # PDFからのデータで更新
        for record in update_data_from_pdf.to_dict('records'):
            model_code = record.get('model_code')
            if not model_code: continue
            
            vehicle = existing_vehicles_db.get(model_code)
            if vehicle: # 存在すれば更新
                vehicle.appearance_count += record.get('new_appearance_count', 0)
                vehicle.year, vehicle.grade = record.get('year'), record.get('grade')
                vehicle.weight_kg, vehicle.engine_model = record.get('weight_kg'), record.get('engine_model')
                vehicle.updated_at = datetime.utcnow()
            else: # 存在しなければ新規作成
                vehicle = VehicleMaster(**record)
                vehicle.appearance_count = record.get('new_appearance_count', 0)
                existing_vehicles_db[model_code] = vehicle
            
            session.add(vehicle)

        # --- 4. 落札実績にしか存在しない車種をメモリ上で追加 ---
        sales_only_query = session.query(
            SalesHistory.maker, SalesHistory.car_name, SalesHistory.model_code
        ).distinct()
        
        for sale in sales_only_query.all():
            if sale.model_code not in existing_vehicles_db: # メモリ上の辞書に存在しないかチェック
                vehicle = VehicleMaster(
                    maker=sale.maker, car_name=sale.car_name, model_code=sale.model_code,
                    appearance_count=0
                )
                session.add(vehicle)
                existing_vehicles_db[sale.model_code] = vehicle # 辞書にも追加

        # --- 5. すべての変更を一度にDBに書き込む ---
        session.commit()
        print("  - 車種マスターの更新が完了しました。")

        # --- 6. 最終的な結果を生成 ---
        sales_counts_df = pd.read_sql(
            "SELECT model_code, COUNT(id) as sales_count FROM saleshistory GROUP BY model_code", engine
        )
        final_master_df = pd.read_sql("SELECT * FROM vehiclemaster", engine)
        final_output_df = pd.merge(final_master_df, sales_counts_df, on='model_code', how='left')
        final_output_df['sales_count'] = final_output_df['sales_count'].fillna(0).astype(int)

    finally:
        session.close()

    return final_output_df