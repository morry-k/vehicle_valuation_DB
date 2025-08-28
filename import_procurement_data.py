import pandas as pd
from pathlib import Path
from src.db.database import engine, SessionLocal
from src.db.models import VehicleMaster, SQLModel
from src.utils import normalize_text # ▼▼▼ 1. ユーティリティから正規化関数をインポート ▼▼▼

# ★★★ インプットとなる仕入れ実績ファイルへのパス ★★★
INPUT_CSV_PATH = Path(__file__).parent / "data" / "input" / "procurement_records" / "procurement_2025_06.csv"

def import_procurement_data():
    print(f"'{INPUT_CSV_PATH.name}' のインポート処理を開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        df = pd.read_csv(INPUT_CSV_PATH, sep=',', encoding='cp932')
        df.rename(columns={'型式': 'model_code', '車名': 'maker'}, inplace=True)

        if 'model_code' not in df.columns:
            print("エラー: CSVに'型式'列が見つかりません。")
            return
            
        # 型式のクリーニング
        df['model_code'] = df['model_code'].str.split('-').str[-1].str.strip()
        
        # ▼▼▼ 2. 正規化関数を適用する行を追加 ▼▼▼
        df['model_code'] = df['model_code'].apply(normalize_text)

        df.dropna(subset=['model_code'], inplace=True)
        df.drop_duplicates(subset=['model_code'], inplace=True)

        existing_codes_query = session.query(VehicleMaster.model_code).all()
        existing_codes = {code for (code,) in existing_codes_query}
        print(f"データベースに既に存在するユニークな型式: {len(existing_codes)}件")

        new_vehicles_df = df[~df['model_code'].isin(existing_codes)]
        
        imported_count = 0
        if not new_vehicles_df.empty:
            print(f"車種辞書への新規追加対象: {len(new_vehicles_df)}件")
            
            for record in new_vehicles_df.to_dict('records'):
                new_record = VehicleMaster(
                    model_code=record['model_code'],
                    maker=record.get('maker'),
                    appearance_count=0
                )
                session.add(new_record)
            
            session.commit()
            imported_count = len(new_vehicles_df)

        skipped_count = len(df) - imported_count
        
        print("\n--- 処理結果 ---")
        print(f"車種辞書への新規追加: {imported_count}件")
        print(f"スキップ（既存）: {skipped_count}件")
        print("----------------")
    
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {INPUT_CSV_PATH}")
    finally:
        session.close()

if __name__ == "__main__":
    import_procurement_data()