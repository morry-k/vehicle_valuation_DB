# src/main.py (テスト実行用)

from src import config
from src import pipeline
import pandas as pd

def main():
    """
    パイプライン処理のテスト実行用メイン関数 (10件のみ処理)
    """
    print("🚀 [テストモード] パイプライン処理を開始します...")

    # フェーズ1: 車種マスターリストの生成
    print("⚙️ フェーズ1: 車種マスターリストを生成中...")
    vehicle_master_df = pipeline.run_phase1_generate_master_list()
    
    if vehicle_master_df.empty:
        print("❌ フェーズ1でデータが生成されなかったため、処理を中断します。")
        return

    # DataFrameのヘッダー行（「メーカー」など）を除外する
    # この処理は pipeline.py に移動済みですが、念のためここでも確認
    if not vehicle_master_df.empty and vehicle_master_df.iloc[0]['maker'] == 'メーカー':
         vehicle_master_df = vehicle_master_df.iloc[1:].copy()

    print(f"✅ フェーズ1完了: {len(vehicle_master_df)}件のユニークな車種情報を抽出しました。")
    print("--- 抽出結果（最初の5件）---")
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print(vehicle_master_df.head(5))
    print("--------------------")

    # テスト用に先頭10件のみを処理対象とする
    test_df = vehicle_master_df.head(10)
    print(f"\n[テストモード] 先頭{len(test_df)}件のデータのみを処理します。")

    # フェーズ2: データ収集・拡充
    print("\n🤖 フェーズ2: データを収集中...")
    enriched_df = pipeline.run_phase2_enrich_data(test_df)
    
    # フェーズ3: 価値計算 (現在は何もしない)
    final_df = enriched_df

    # CSVファイルに保存
    try:
        final_df.to_csv(config.VEHICLE_VALUE_LIST_PATH, index=False, encoding='utf-8-sig')
        print(f"\n✅ テスト処理が完了し、結果をファイルに保存しました。")
        print(f"出力ファイル: {config.VEHICLE_VALUE_LIST_PATH}")
    except Exception as e:
        print(f"❌ ファイルの保存中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()