import pandas as pd
from pathlib import Path
from src.db.database import SessionLocal
from src.db.models import VehicleMaster

# ★★★ インプットとなる更新用CSVファイルへのパス ★★★
UPDATE_CSV_PATH = Path(__file__).parent / "data" / "input" / "update_weights.csv"

def update_database_from_csv():
    """
    CSVファイルの内容に基づいて、データベースを一括更新する
    """
    print(f"'{UPDATE_CSV_PATH.name}' を使ってデータベースの一括更新を開始します...")
    session = SessionLocal()
    
    try:
        update_df = pd.read_csv(UPDATE_CSV_PATH)

        if 'id' not in update_df.columns:
            print("エラー: CSVファイルに更新対象を特定するための'id'列がありません。")
            return
            
        update_count = 0
        not_found_count = 0
        skipped_count = 0
        
        for record in update_df.to_dict('records'):
            target_id = record.get('id')
            if not target_id: continue

            vehicle = session.query(VehicleMaster).filter_by(id=target_id).first()
            
            if vehicle:
                # --- ▼▼▼ ここからが新しい安全装置付きの更新ロジック ▼▼▼ ---
                
                # もしCSVにmodel_codeの更新指示があれば、重複チェックを行う
                if 'model_code' in record and pd.notna(record['model_code']):
                    new_model_code = record['model_code']
                    # 変更先のmodel_codeが、自分以外のレコードで既に使われていないか確認
                    exists = session.query(VehicleMaster).filter(
                        VehicleMaster.model_code == new_model_code,
                        VehicleMaster.id != target_id
                    ).first()
                    
                    if exists:
                        print(f"  - スキップ: ID={target_id} の型式を '{new_model_code}' に変更できません。(ID={exists.id} で既に使用中)")
                        skipped_count += 1
                        continue # この行の処理を中断して次に進む

                # 安全チェックをパスしたら、CSVにある列の値を更新
                for column, value in record.items():
                    if column != 'id' and hasattr(vehicle, column) and pd.notna(value):
                        setattr(vehicle, column, value)
                update_count += 1
                # --- ▲▲▲ ここまでが新しいロジック ▲▲▲ ---
            else:
                print(f"  - 警告: ID={target_id} のレコードがデータベースに見つかりませんでした。")
                not_found_count += 1
                
        session.commit()
        
        print("\n--- 処理結果 ---")
        print(f"更新成功: {update_count}件")
        print(f"スキップ（重複エラー）: {skipped_count}件")
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