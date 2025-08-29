import pandas as pd
from sqlalchemy import text
from src.db.database import engine
from src.config import OUTPUT_DIR # configから出力先フォルダを取得

# ★★★ 出力するExcelファイルの名前 ★★★
OUTPUT_EXCEL_PATH = OUTPUT_DIR / "database_export.xlsx"

def export_database_to_excel():
    """
    データベース内の全テーブルを単一のExcelファイルに出力する
    """
    print("データベースのエクスポート処理を開始します...")

    try:
        # データベース内の全テーブル名を取得
        with engine.connect() as connection:
            sql_query = text("SELECT name FROM sqlite_master WHERE type='table';")
            result = connection.execute(sql_query)
            table_names = [row[0] for row in result]
        
        if not table_names:
            print("データベースにテーブルが見つかりません。")
            return

        # Excelファイルへの書き込みを開始
        with pd.ExcelWriter(OUTPUT_EXCEL_PATH, engine='openpyxl') as writer:
            print(f"'{OUTPUT_EXCEL_PATH}' への書き込みを開始します...")
            
            for table_name in table_names:
                print(f"  - テーブル '{table_name}' を読み込み中...")
                # 各テーブルのデータをすべてDataFrameとして読み込む
                df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
                
                # DataFrameを、テーブル名をシート名としてExcelに書き込む
                df.to_excel(writer, sheet_name=table_name, index=False)
                print(f"    -> '{table_name}' シートに {len(df)} 件のデータを書き込みました。")

        print("\n✅ データベースのエクスポートが完了しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    export_database_to_excel()