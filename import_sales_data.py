import pandas as pd
from pathlib import Path
from src.db.database import engine, SessionLocal
from src.db.models import SalesHistory, SQLModel

# ★★★ 処理したいファイル名に合わせて変更してください ★★★
INPUT_CSV_PATH = Path(__file__).parent / "data" / "input" / "sales_records" / "sales_2025_06.csv"

def import_data():
    print(f"'{INPUT_CSV_PATH.name}' のインポート処理を開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        df = pd.read_csv(INPUT_CSV_PATH, sep=',', encoding='cp932')
        print(f"--- {len(df)}件のデータをCSVから読み込みました ---")

        # 列名を日本語から英語に変換
        df.rename(columns={
            '引渡報告日': 'sale_date',
            '車台番号': 'chassis_number',
            '型式': 'model_code',
            '車名': 'maker', # ← 'car_name' から 'maker' に変更
            '引渡先事業者／事業所名称': 'buyer_name',
            '引渡先事業所所在地': 'buyer_location'
        }, inplace=True)

        if 'model_code' not in df.columns:
            print("エラー: CSVに'型式'列が見つかりません。")
            return
            
        df['sale_date'] = pd.to_datetime(df['sale_date']).dt.date
        
        # ▼▼▼ 型式の接頭辞（例: "DBA-"）を削除する正規化処理を追加 ▼▼▼
        df['model_code'] = df['model_code'].str.split('-').str[-1]
        print("--- 型式の正規化が完了しました ---")

        imported_count = 0
        skipped_count = 0
        for record in df.to_dict('records'):
            exists = session.query(SalesHistory).filter_by(chassis_number=record['chassis_number']).first()
            if not exists:
                new_record = SalesHistory(**record)
                session.add(new_record)
                imported_count += 1
            else:
                skipped_count += 1
        
        session.commit()
        print("\n--- 処理結果 ---")
        print(f"インポート成功: {imported_count}件")
        print(f"スキップ（重複）: {skipped_count}件")
        print("----------------")
    
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {INPUT_CSV_PATH}")
    finally:
        session.close()

if __name__ == "__main__":
    import_data()