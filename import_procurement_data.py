import pandas as pd
from pathlib import Path
from src.db.database import engine, SessionLocal
from src.db.models import SalesHistory, SQLModel # ★ SalesHistoryモデルを正しく使う

# ★ インプットとなる「仕入れ実績」ファイルへのパス
INPUT_CSV_PATH = Path(__file__).parent / "data" / "input" / "procurement_records" / "procurement_2025_06.csv"

def import_procurement_data():
    print(f"'{INPUT_CSV_PATH.name}' のインポート処理を開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        df = pd.read_csv(INPUT_CSV_PATH, sep=',', encoding='cp932')
        
        df.rename(columns={
            '引渡報告日': 'sale_date',
            '車台番号': 'chassis_number',
            '型式': 'model_code',
            '車名': 'maker',
            '引渡先事業者／事業所名称': 'buyer_name',
            '引渡先事業所所在地': 'buyer_location'
        }, inplace=True)

        if 'chassis_number' not in df.columns:
            print("エラー: CSVに'車台番号'列が見つかりません。")
            return
            
        # データをクリーニング
        df['model_code'] = df['model_code'].str.split('-').str[-1].str.strip()
        df['chassis_number'] = df['chassis_number'].str.strip()
        df['sale_date'] = pd.to_datetime(df['sale_date']).dt.date
        df.dropna(subset=['chassis_number'], inplace=True) # 車台番号がない行は除外

        imported_count = 0
        skipped_count = 0
        
        # ★ SalesHistoryテーブルにデータを登録するループ
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
        print(f"SalesHistoryテーブルへのインポート成功: {imported_count}件")
        print(f"スキップ（重複）: {skipped_count}件")
        print("----------------")
    
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {INPUT_CSV_PATH}")
    finally:
        session.close()

if __name__ == "__main__":
    import_procurement_data()