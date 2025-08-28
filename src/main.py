from src import config
from src import pipeline
import pandas as pd

def main():
    print("🚀 パイプライン処理を開始します...")

    # --- フェーズ1: PDFから全車両データを抽出し、クリーニングする ---
    print("⚙️ フェーズ1: 全車両データを抽出中...")
    all_vehicles_df = pipeline.run_phase1_extract_all_vehicles()
    if all_vehicles_df.empty:
        print("❌ PDFからデータが抽出されませんでした。")
        return
    print(f"✅ フェーズ1完了: {len(all_vehicles_df)}件の車両データを抽出しました。")
    
    # --- フェーズ2: AI処理（またはスキップ）を実行する ---
    print("\n🤖 フェーズ2: AI処理（またはスキップ）を実行します...")
    
    # ▼▼▼ 重複削除の基準を「model_code」のみにし、完全にユニークなリストを作成 ▼▼▼
    # keep='first' は、重複があった場合に最初の行を残す設定
    unique_vehicles_df = all_vehicles_df.drop_duplicates(subset=['model_code'], keep='first')
    
    # AI処理（現在はスキップする模擬関数）を呼び出す
    enriched_df = pipeline.run_phase2_enrich_data(unique_vehicles_df.copy())

    # --- フェーズ3: データベースを更新する ---
    print("\n💸 フェーズ3: データベースを更新中...")
    # 「重複を含む全データ」と「ユニークな車種の拡充済みデータ」の両方を渡す
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

# このスクリプトの実行を開始するきっかけ
if __name__ == "__main__":
    main()