# src/data_processing/scraper.py

import pandas as pd

def enrich_vehicle_data(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    車種マスターリストに、Webなどから収集した追加情報（重量など）を付与する
    """
    print("  - 車両データの拡充処理を開始します...")
    
    enriched_data = []
    # DataFrameの各行をループ処理
    for index, row in master_df.iterrows():
        # row['maker'], row['car_name'], row['model_code'] などをキーに情報を検索
        print(f"    - 処理中: {row['maker']} {row['car_name']} ({row['model_code']})")

        # --- ここにスクレイピングやAPI呼び出しのロジックを実装 ---
        # 現時点ではダミーデータを追加
        weight_kg = 1200 # ダミーの重量
        engine_model = "DUMMY-ENGINE" # ダミーのエンジン型式
        # ----------------------------------------------------

        # 元の行データに新しい情報を追加
        new_row = row.to_dict()
        new_row['weight_kg'] = weight_kg
        new_row['engine_model'] = engine_model
        enriched_data.append(new_row)
    
    print("  - データ拡充処理が完了しました。")
    return pd.DataFrame(enriched_data)