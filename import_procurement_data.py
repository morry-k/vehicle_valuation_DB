import pandas as pd
from pathlib import Path
from src.db.database import engine, SessionLocal
from src.db.models import SalesHistory, SQLModel

# ★ インプットとなる「仕入れ実績」ファイルへのパス
INPUT_CSV_PATH = Path(__file__).parent / "data" / "input" / "procurement_records" / "procurement_2025_06.csv"

def import_procurement_data():
    print(f"'{INPUT_CSV_PATH.name}' を SalesHistory テーブルにインポートします...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        df = pd.read_csv(INPUT_CSV_PATH, sep=',', encoding='cp932')
        print(f"--- CSVから {len(df)} 件の行を読み込みました。 ---")
        
        df.rename(columns={
            '引渡報告日': 'sale_date', '車台番号': 'chassis_number',
            '型式': 'model_code', '車名': 'maker',
            '引渡先事業者／事業所名称': 'buyer_name', '引渡先事業所所在地': 'buyer_location'
        }, inplace=True)

        if 'chassis_number' not in df.columns:
            print("エラー: CSVに'車台番号'列が見つかりません。")
            return
            
        df['model_code'] = df['model_code'].str.split('-').str[-1].str.strip()
        df['chassis_number'] = df['chassis_number'].str.strip()
        df['sale_date'] = pd.to_datetime(df['sale_date']).dt.date
        df.dropna(subset=['chassis_number'], inplace=True)
        print(f"--- クリーニング後、 {len(df)} 件の有効なデータが残りました。 ---")

        imported_count = 0
        skipped_count = 0
        
        for record in df.to_dict('records'):
            exists = session.query(SalesHistory).filter_by(chassis_number=record['chassis_number']).first()
            if not exists:
                print(f"  -> 新規追加対象: {record['chassis_number']}") # デバッグ表示
                new_record = SalesHistory(**record)
                session.add(new_record)
                imported_count += 1
            else:
                skipped_count += 1
        
        print(f"\n--- データベースへの書き込みを開始します (新規{imported_count}件) ---")
        session.commit()
        print("--- データベースへの書き込みが完了しました ---")
        
        print("\n--- 処理結果 ---")
        print(f"SalesHistoryテーブルへのインポート成功: {imported_count}件")
        print(f"スキップ（重複）: {skipped_count}件")
        print("----------------")
    
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {INPUT_CSV_PATH}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import_procurement_data()