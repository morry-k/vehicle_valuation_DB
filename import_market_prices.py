import pandas as pd
from pathlib import Path
from datetime import datetime
from src.db.database import engine, SessionLocal
from src.db.models import ComponentValue, SQLModel

# ▼▼▼ ファイル名を実際のExcelファイル名に修正 ▼▼▼
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

# import_market_prices.py の run_import 関数

def run_import():
    print(f"'{INPUT_XLSX_PATH.name}' から市場価格のインポートを開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        # ▼▼▼ header=3 を追加 ▼▼▼
        # header=3 は「4行目をヘッダーとして読み込む」という意味 (0から数えるため)
        df = pd.read_excel(INPUT_XLSX_PATH, header=3)
        
        # すべての列名の前後に存在する可能性のある空白を自動で削除する
        df.columns = df.columns.str.strip()
        
        # 「E/G型式」が空の行は除外
        df.dropna(subset=['E/G型式'], inplace=True)
        
        
        df['details_tags'] = df['詳細'].apply(parse_details_to_tags)
        
        key_cols = ['品名', 'E/G型式', 'details_tags']
        grouped = df.groupby(key_cols)

        print(f"{len(grouped)}種類の部品グループが見つかりました。データベースを更新します...")

        for name, group in grouped:
            item_name, engine_model, tags = name
            
            avg_price = group['単価'].mean()
            latest_price = group.sort_values(by='日付').iloc[-1]['単価']
            sample_size = len(group)

            existing_value = session.query(ComponentValue).filter_by(
                item_name=item_name, engine_model=engine_model, details_tags=tags
            ).first()

            if existing_value:
                existing_value.latest_price, existing_value.average_price, existing_value.sample_size = latest_price, avg_price, sample_size
                existing_value.updated_at = datetime.utcnow()
            else:
                existing_value = ComponentValue(
                    item_name=item_name, engine_model=engine_model, details_tags=tags,
                    latest_price=latest_price, average_price=avg_price, sample_size=sample_size
                )
            session.add(existing_value)
        
        session.commit()
        print("\n✅ 市場価格データベースの更新が完了しました。")

    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {INPUT_XLSX_PATH}")
    except KeyError as e:
        print(f"エラー: Excelファイルに必要な列が見つかりません: {e}")
        print("Excelファイルのヘッダー行（1行目）に、必要な列名（特に E/G型式）が存在するか確認してください。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_import()