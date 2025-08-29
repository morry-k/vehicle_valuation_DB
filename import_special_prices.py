import pandas as pd
from pathlib import Path
from datetime import datetime
from src.db.database import engine, SessionLocal
from src.db.models import ComponentValue, SQLModel
from src.utils import normalize_text

# ★★★ インプットとなる特別価格ファイルへのパス ★★★
INPUT_CSV_PATH = Path(__file__).parent / "data" / "input" / "special_prices.csv"

def import_special_prices():
    """
    車種ごとの特別な部品価格をCSVから読み込み、データベースを更新する
    """
    print(f"'{INPUT_CSV_PATH.name}' から特別価格のインポートを開始します...")
    SQLModel.metadata.create_all(engine)
    session = SessionLocal()

    try:
        # 1. 特別価格CSVファイルを読み込む
        df = pd.read_csv(INPUT_CSV_PATH)
        df.columns = df.columns.str.strip()

        # 型式を正規化して、データベースとの整合性を保つ
        if 'model_code' in df.columns:
            df['model_code'] = df['model_code'].apply(normalize_text)

        imported_count = 0
        updated_count = 0

        # 2. CSVの各行をループして、DBを更新（Upsert）する
        for record in df.to_dict('records'):
            model_code = record.get('model_code')
            item_name = record.get('item_name')
            price = record.get('price')

            if not all([model_code, item_name, price]):
                print(f"  - スキップ: {record} -> 情報が不足しています。")
                continue

            # 車種と部品名で、既存の特別価格レコードがあるか検索
            existing_value = session.query(ComponentValue).filter_by(
                model_code=model_code,
                item_name=item_name
            ).first()

            if existing_value:
                # 存在すれば、価格を更新
                existing_value.latest_price = price
                existing_value.average_price = price
                existing_value.sample_size = 1 # 固定価格なのでサンプル数は1
                existing_value.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # 存在しなければ、新しいレコードとして作成
                existing_value = ComponentValue(
                    model_code=model_code,
                    item_name=item_name,
                    latest_price=price,
                    average_price=price,
                    sample_size=1,
                    details_tags="special" # これが特別価格であることを示すタグ
                )
                imported_count += 1
            
            session.add(existing_value)

        session.commit()
        print("\n--- 処理結果 ---")
        print(f"新規追加: {imported_count}件")
        print(f"更新: {updated_count}件")
        print("----------------")

    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {INPUT_CSV_PATH}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    import_special_prices()