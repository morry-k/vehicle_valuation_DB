# src/main.py

from src import config
from src import pipeline
import pandas as pd

def main():
    print("🚀 パイプライン処理を開始します...")

    # --- フェーズ1: PDFから「重複を含む」全車両データを抽出 ---
    print("⚙️ フェーズ1: 全車両データを抽出中...")
    all_vehicles_df = pipeline.run_phase1_extract_all_vehicles()
    
    if all_vehicles_df.empty:
        print("❌ PDFからデータが抽出されませんでした。")
        return
    print(f"✅ フェーズ1完了: {len(all_vehicles_df)}件の車両データを抽出しました。")
    
    # --- フェーズ2はスキップ ---

    # --- フェーズ3: DBの更新と集計 ---
    print("\n💸 フェーズ3: データベースを更新中...")
    # フェーズ1の全データを直接フェーズ3に渡す
    final_db = pipeline.run_phase3_calculate_value(all_vehicles_df)

    # --- CSVファイルに保存 ---
    try:
        final_db.to_csv(config.VEHICLE_VALUE_LIST_PATH, index=False, encoding='utf-8-sig')
        print(f"\n✅ パイプライン処理が完了し、結果をファイルに保存しました。")
        print(f"出力ファイル: {config.VEHICLE_VALUE_LIST_PATH}")
    except Exception as e:
        print(f"❌ ファイルの保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()