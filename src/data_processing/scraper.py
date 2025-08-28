import pandas as pd
import time
from src.data_processing.llm_client import get_specs_from_llm

def enrich_vehicle_data(master_df: pd.DataFrame) -> pd.DataFrame:
    print("  - AIによるデータ拡充処理を開始します...")
    enriched_records = []
    total_vehicles = len(master_df)

    for index, row in master_df.iterrows():
        model_code = row.get('model_code')
        print(f"    - 処理中 ({index + 1}/{total_vehicles}): 型式 ({model_code})")
        
        # 既に情報が十分にあればスキップ
        if pd.notna(row.get('car_name')) and pd.notna(row.get('engine_model')):
            print("      -> 既に情報があるためスキップします。")
            enriched_records.append(row.to_dict())
            continue

        # AIに型式だけを渡す
        specs = get_specs_from_llm(model_code)
        
        new_record = row.to_dict()
        new_record.update(specs)
        enriched_records.append(new_record)
        
        time.sleep(0.1)
    
    print("  - データ拡充処理が完了しました。")
    return pd.DataFrame(enriched_records)