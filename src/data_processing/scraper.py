
import pandas as pd
import time
# 変更後
from src.data_processing.llm_client import get_specs_from_llm

def enrich_vehicle_data(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    車種マスターリストに、生成AIから収集した追加情報を付与する
    """
    print("  - 車両データの拡充処理を生成AIで開始します...")
    
    enriched_data = []
    total_vehicles = len(master_df)

    # DataFrameの各行をループ処理
    for index, row in master_df.iterrows():
        # 進捗を表示
        print(f"    - 処理中 ({index + 1}/{total_vehicles}): {row['maker']} {row['car_name']} ({row['model_code']})")
        
        # LLMからスペック情報を取得
        specs = get_specs_from_llm(row['maker'], row['car_name'], row['model_code'])
        
        # 元の行データに新しい情報を追加
        new_row = row.to_dict()
        new_row['weight_kg'] = specs.get('weight_kg')
        new_row['engine_model'] = specs.get('engine_model')
        new_row['catalyst_model'] = specs.get('catalyst_model')
        enriched_data.append(new_row)
        
        time.sleep(1.5) # APIのレートリミットを避けるため、リクエスト間に待機時間を設ける
    
    print("  - データ拡充処理が完了しました。")
    return pd.DataFrame(enriched_data)