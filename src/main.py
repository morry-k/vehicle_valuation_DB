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
    
    # --- フェーズ2: ユニークな車種リストに対してのみ、データ拡充を行う ---
    print("\n🤖 フェーズ2: 未知の車種のデータをAIで収集中...")
    unique_vehicles_df = all_vehicles_df.drop_duplicates(subset=['maker', 'car_name', 'model_code'])

    # ▼▼▼ この2行で処理件数を10件に絞ります ▼▼▼
    print(f"\n[テストモード] 先頭10件のデータのみをAIで処理します。")
    test_df = unique_vehicles_df.head(10)
    
    # 10件に絞ったデータフレームをAI処理に渡す
    enriched_df = pipeline.run_phase2_enrich_data(test_df.copy())

    # --- フェーズ3: DBの更新と集計 ---
    print("\n💸 フェーズ3: データベースを更新中...")
    # フェーズ1の全データ(出現回数用)と、フェーズ2の拡充済みデータ(スペック用)の両方を渡す
    final_db = pipeline.run_phase3_calculate_value(all_vehicles_df, enriched_df)

    # --- CSVファイルに保存 ---
    try:
        final_db.to_csv(config.VEHICLE_VALUE_LIST_PATH, index=False, encoding='utf-8-sig')
        print(f"\n✅ パイプライン処理が完了し、結果をファイルに保存しました。")
        print(f"出力ファイル: {config.VEHICLE_VALUE_LIST_PATH}")
    except Exception as e:
        print(f"❌ ファイルの保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()