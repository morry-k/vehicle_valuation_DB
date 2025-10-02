# import_targets.py
import pandas as pd
from pathlib import Path
from src.db.database import engine, SessionLocal
from src.db.models import TargetModel, SQLModel
from src.utils import normalize_text

INPUT_CSV_PATH = Path(__file__).parent / "data" / "input" / "target_models.csv"

def import_target_models():
    print(f"'{INPUT_CSV_PATH.name}' から注目車種リストのインポートを開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        df = pd.read_csv(INPUT_CSV_PATH)
        df['model_code'] = df['model_code'].apply(normalize_text)

        # 既存のリストを一度すべて削除
        session.query(TargetModel).delete()
        
        imported_count = 0
        for model_code in df['model_code'].unique():
            new_target = TargetModel(model_code=model_code)
            session.add(new_target)
            imported_count += 1
        
        session.commit()
        print(f"\n✅ {imported_count}件の注目車種をデータベースに登録しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    import_target_models()