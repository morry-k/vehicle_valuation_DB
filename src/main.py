# src/main.py

import config
import pipeline # pipeline.pyをインポート

def main():
    """
    パイプライン処理全体を実行するメイン関数
    """
    print("🚀 パイプライン処理を開始します...")

    # フェーズ1: 車種マスターリストの生成
    print("⚙️ フェーズ1: 車種マスターリストを生成中...")
    vehicle_master_df = pipeline.run_phase1_generate_master_list()
    
    if vehicle_master_df.empty:
        print("❌ フェーズ1でデータが生成されなかったため、処理を中断します。")
        return

    print(f"✅ フェーズ1完了: {len(vehicle_master_df)}件のユニークな車種情報を抽出しました。")

    # フェーズ2: データ収集・拡充 (Enrichment)
    print("\n🤖 フェーズ2: データを収集中...")
    enriched_df = pipeline.run_phase2_enrich_data(vehicle_master_df)
    print(f"✅ フェーズ2完了: データ拡充が完了しました。")
    print("拡充結果（最初の5件）:")
    print(enriched_df.head())


    # フェーズ3: 価値計算
    print("\n💸 フェーズ3: 価値を計算中...")
    # TODO: enriched_df を使って価値計算ロジックを実装
    final_df = enriched_df # 現時点ではフェーズ2の結果を最終結果とする


    # ▼▼▼ この部分でCSVファイルに書き出します ▼▼▼
    try:
        # final_df をCSVファイルとして保存
        # index=False: DataFrameのインデックス(0,1,2...)をCSVに含めない設定
        # encoding='utf-8-sig': Excelで開いた際の文字化けを防ぐ設定
        final_df.to_csv(config.VEHICLE_VALUE_LIST_PATH, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ パイプライン処理が完了し、結果をファイルに保存しました。")
        print(f"出力ファイル: {config.VEHICLE_VALUE_LIST_PATH}")

    except Exception as e:
        print(f"❌ ファイルの保存中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()