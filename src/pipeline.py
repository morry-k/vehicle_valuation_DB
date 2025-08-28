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

# src/pipeline.py の run_phase3_calculate_value 関数

# src/pipeline.py

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
        # --- 1. 既存の車種マスターを辞書として一度に読み込む（高速化） ---
        existing_vehicles = {v.model_code: v for v in session.query(VehicleMaster).all()}
        print(f"  - 既存の車種マスター（{len(existing_vehicles)}件）を読み込みました。")

        # --- 2. 今回のPDFから出現回数を計算 ---
        key_cols = ['maker', 'car_name', 'model_code']
        appearance_counts = all_vehicles_df.groupby(key_cols).size().reset_index(name='new_appearance_count')
        
        # --- 3. 今回のユニークな車種情報と出現回数を結合 ---
        update_data = pd.merge(enriched_df, appearance_counts, on=key_cols, how="left")

        # --- 4. データベース内の車種マスターを更新または新規登録 ---
        for record in update_data.to_dict('records'):
            model_code = record.get('model_code')
            if not model_code:
                continue

            # 辞書を使って既存レコードを検索
            vehicle = existing_vehicles.get(model_code)
            
            if vehicle:
                # 存在すれば、出現回数を加算し、情報を更新
                vehicle.appearance_count += record.get('new_appearance_count', 0)
                vehicle.weight_kg = record.get('weight_kg')
                vehicle.engine_model = record.get('engine_model')
                vehicle.catalyst_model = record.get('catalyst_model')
                vehicle.year = record.get('year')
                vehicle.grade = record.get('grade')
                vehicle.updated_at = datetime.utcnow()
            else:
                # 存在しなければ、新しいレコードとして作成
                vehicle = VehicleMaster(**record)
                vehicle.appearance_count = record.get('new_appearance_count', 0)
                # 新しいレコードなので、existing_vehicles辞書にも追加
                existing_vehicles[model_code] = vehicle
            
            session.add(vehicle)
        
        session.commit()
        print("  - 車種マスターの更新が完了しました。")

        # --- 5. 落札実績テーブルから、型式ごとの件数を集計 ---
        sales_counts_df = pd.read_sql(
            "SELECT model_code, COUNT(id) as sales_count FROM saleshistory GROUP BY model_code",
            engine
        )
        print("  - 落札実績の集計が完了しました。")

        # --- 6. 最新の車種マスターをDBから読み出し、落札実績件数を結合 ---
        final_master_df = pd.read_sql("SELECT * FROM vehiclemaster", engine)
        final_output_df = pd.merge(final_master_df, sales_counts_df, on='model_code', how='left')
        final_output_df['sales_count'] = final_output_df['sales_count'].fillna(0).astype(int)

    finally:
        session.close()

    return final_output_df