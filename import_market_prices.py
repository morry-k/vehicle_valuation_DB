import pandas as pd
from pathlib import Path
from datetime import datetime
from src.db.database import engine, SessionLocal
from src.db.models import ComponentValue, SQLModel
from src.data_processing.llm_client import get_full_engine_model_from_llm # 新しい関数をインポート
import time

INPUT_XLSX_PATH = Path(__file__).parent / "data" / "input" / "sales_records" / "sales_2025_06.xlsx"

def parse_details_to_tags(detail_string: str) -> str:
    # ... (この関数は変更なし) ...
    if not isinstance(detail_string, str): return "standard"
    tags, detail_lower = set(), detail_string.lower()
    if "触媒外し" in detail_lower: tags.add("no_catalyst")
    elif "触媒" in detail_lower: tags.add("with_catalyst")
    if "足セット" in detail_lower: tags.add("with_suspension")
    if "4wd" in detail_lower: tags.add("4wd")
    return ",".join(sorted(list(tags))) if tags else "standard"

def run_import():
    print(f"'{INPUT_XLSX_PATH.name}' から市場価格のインポートを開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        df = pd.read_excel(INPUT_XLSX_PATH, header=3)
        df.columns = df.columns.str.strip()
        df.dropna(subset=['E/G型式', '単価'], inplace=True)

        # --- ▼▼▼ AIによるエンジン型式の正規化処理を追加 ▼▼▼ ---
        print("\n--- AIを使ってエンジン型式の正規化を開始します ---")
        normalized_engines = []
        for index, row in df.iterrows():
            print(f"  - 処理中 ({index + 1}/{len(df)}): {row.get('メ－カ－')} {row.get('車輌型式')} ({row.get('E/G型式')})")
            full_engine_model = get_full_engine_model_from_llm(
                row.get('メ－カ－'), row.get('車輌型式'), row.get('E/G型式')
            )
            normalized_engines.append(full_engine_model)
            time.sleep(0.1) # レートリミット対策

        df['engine_model_normalized'] = normalized_engines
        print("--- エンジン型式の正規化が完了しました ---\n")
        # --- ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ ---

        df['details_tags'] = df['詳細'].apply(parse_details_to_tags)
        
        # グループ化のキーを正規化後のエンジン型式に変更
        key_cols = ['品名', 'engine_model_normalized', 'details_tags']
        grouped = df.groupby(key_cols)

        print(f"{len(grouped)}種類の部品グループが見つかりました。データベースを更新します...")

        for name, group in grouped:
            item_name, engine_model, tags = name
            
            latest_row = group.sort_values(by='日付', ascending=False).iloc[0]
            avg_price = group['単価'].mean()
            latest_price = latest_row['単価']
            sample_size = len(group)

            existing_value = session.query(ComponentValue).filter_by(
                item_name=str(item_name), engine_model=str(engine_model), details_tags=tags
            ).first()

            if existing_value:
                existing_value.latest_price = latest_price
                existing_value.average_price = avg_price
                existing_value.sample_size = sample_size
                existing_value.updated_at = datetime.utcnow()
            else:
                existing_value = ComponentValue(
                    item_name=str(item_name), engine_model=str(engine_model), details_tags=tags,
                    latest_price=latest_price, average_price=avg_price, sample_size=sample_size
                )
            session.add(existing_value)
        
        session.commit()
        print("\n✅ 市場価格データベースの更新が完了しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    run_import()