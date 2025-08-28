# enrich_database.py
import pandas as pd
from sqlalchemy import or_
from src.db.database import SessionLocal, engine
from src.db.models import VehicleMaster, SQLModel
from src.data_processing.scraper import enrich_vehicle_data


def run_full_enrichment():
    print("データベース全体のデータ拡充処理を開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        # --- 1. DBから、スペック情報が欠けている車種をすべて取得 ---
        query = session.query(VehicleMaster).filter(
            or_(
                VehicleMaster.engine_model == None,
                VehicleMaster.total_weight_kg == None,
                VehicleMaster.drive_type == None,
                VehicleMaster.body_type == None
            )
        )
        
        incomplete_vehicles_df = pd.read_sql(query.statement, engine)
        
        if incomplete_vehicles_df.empty:
            print("✅ すべての車種にスペック情報が登録済みです。処理の必要はありません。")
            return

        print(f"--- スペック情報が不足している {len(incomplete_vehicles_df)} 件の車種を対象に処理を実行します ---")

        # --- 2. AIでデータ拡充を実行 ---
        enriched_df = enrich_vehicle_data(incomplete_vehicles_df)

        # --- 3. データベースを更新 ---
        print("--- データベースを更新中... ---")
        update_count = 0
        for record in enriched_df.to_dict('records'):
            vehicle = session.query(VehicleMaster).filter_by(id=record['id']).first()
            if vehicle:
                vehicle.engine_model = record.get('engine_model')
                vehicle.drive_type = record.get('drive_type')
                vehicle.body_type = record.get('body_type')
                vehicle.total_weight_kg = record.get('total_weight_kg')
                vehicle.engine_weight_kg = record.get('engine_weight_kg')
                update_count += 1
        
        session.commit()
        print(f"✅ {update_count}件の車種情報を更新しました。")

    finally:
        session.close()


if __name__ == "__main__":
    run_full_enrichment()