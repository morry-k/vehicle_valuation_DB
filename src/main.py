# src/main.py

from src import config
from src import pipeline
import pandas as pd

def main():
    print("🚀 パイプライン処理を開始します...")

    # --- フェーズ1 ---
    print("⚙️ フェーズ1: 全車両データを抽出中...")
    all_vehicles_df = pipeline.run_phase1_extract_all_vehicles()
    if all_vehicles_df.empty:
        print("❌ PDFからデータが抽出されませんでした。")
        return
    print(f"✅ フェーズ1完了: {len(all_vehicles_df)}件の車両データを抽出しました。")
    
    # --- フェーズ2 ---
    print("\n🤖 フェーズ2: AI処理をスキップします...")
    unique_vehicles_df = all_vehicles_df.drop_duplicates(subset=['maker', 'car_name', 'model_code'])

    # ▼▼▼ .head() の制限を解除し、全件を処理対象とします ▼▼▼
    enriched_df = pipeline.run_phase2_enrich_data(unique_vehicles_df.copy())

    # --- フェーズ3 ---
    print("\n💸 フェーズ3: データベースを更新中...")
    final_db = pipeline.run_phase3_update_database(all_vehicles_df, enriched_df)

    # --- CSVファイルに保存 ---
    try:
        final_db.to_csv(config.VEHICLE_VALUE_LIST_PATH, index=False, encoding='utf-8-sig')
        print(f"\n✅ パイプライン処理が完了し、最終結果をファイルに保存しました。")
        print(f"出力ファイル: {config.VEHICLE_VALUE_LIST_PATH}")
        print("--- 最終結果（先頭5件）---")
        print(final_db.head())
    except Exception as e:
        print(f"❌ ファイルの保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()