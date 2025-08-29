import pandas as pd
from pathlib import Path
from src.db.database import SessionLocal
from src.db.models import VehicleMaster

# ★★★ インプットとなる更新用CSVファイルへのパス ★★★
# ファイル名はご自身のものに合わせて変更してください
UPDATE_CSV_PATH = Path(__file__).parent / "data" / "input" / "update_weights.csv"

def update_database_from_csv():
    """
    CSVファイルの内容に基づいて、データベースを一括更新する
    """
    print(f"'{UPDATE_CSV_PATH.name}' を使ってデータベースの一括更新を開始します...")
    session = SessionLocal()
    
    try:
        # 1. 更新用CSVファイルを読み込む
        update_df = pd.read_csv(UPDATE_CSV_PATH)

        if 'id' not in update_df.columns:
            print("エラー: CSVファイルに更新対象を特定するための'id'列がありません。")
            return
            
        update_count = 0
        not_found_count = 0
        
        # 2. CSVの各行をループして、DBを更新する
        for record in update_df.to_dict('records'):
            target_id = record.get('id')
            
            # IDで更新対象のレコードを検索
            vehicle = session.query(VehicleMaster).filter_by(id=target_id).first()
            
            if vehicle:
                # レコードが見つかれば、CSVにある列の値を更新
                for column, value in record.items():
                    # id列自体は更新しない
                    if column != 'id' and hasattr(vehicle, column) and pd.notna(value):
                        setattr(vehicle, column, value)
                update_count += 1
            else:
                print(f"  - 警告: ID={target_id} のレコードがデータベースに見つかりませんでした。")
                not_found_count += 1
                
        session.commit()
        
        print("\n--- 処理結果 ---")
        print(f"更新成功: {update_count}件")
        print(f"対象不明: {not_found_count}件")
        print("----------------")

    except FileNotFoundError:
        print(f"エラー: 更新用ファイルが見つかりません: {UPDATE_CSV_PATH}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_database_from_csv()