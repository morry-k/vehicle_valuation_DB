import pandas as pd
from src.db.database import engine
from sqlalchemy import text # ▼▼▼ この行を追加 ▼▼▼

# データベース内の全テーブル名を取得
try:
    with engine.connect() as connection:
        # ▼▼▼ text()でSQL文を囲むように修正 ▼▼▼
        sql_query = text("SELECT name FROM sqlite_master WHERE type='table';")
        result = connection.execute(sql_query)
        table_names = [row[0] for row in result]
    
    if not table_names:
        print("データベースにテーブルが見つかりません。")
    else:
        print("--- データベース内のテーブル一覧 ---")
        for name in table_names:
            print(f"- {name}")
        print("-------------------------------------\n")

        # 各テーブルの先頭5件を表示
        pd.set_option('display.max_columns', None) # 全ての列を表示
        pd.set_option('display.width', 200)       # 表示幅を広げる

        for table_name in table_names:
            try:
                print(f"--- テーブル名: {table_name} (先頭5件) ---")
                df = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 5", engine)
                print(df)
                print("\n")
            except Exception as e:
                print(f"テーブル '{table_name}' の読み込み中にエラーが発生しました: {e}")

except Exception as e:
    print(f"データベースへの接続中にエラーが発生しました: {e}")