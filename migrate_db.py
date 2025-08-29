from sqlalchemy import inspect, text
from src.db.database import engine

def run_migration():
    """
    データベースのテーブル構造をチェックし、不足している列を安全に追加する
    """
    print("データベースのマイグレーションを開始します...")
    
    inspector = inspect(engine)
    
    try:
        with engine.connect() as connection:
            trans = connection.begin()
            
            # --- vehiclemaster テーブルの列をチェック ---
            vm_columns = [c["name"] for c in inspector.get_columns("vehiclemaster")]
            # models.py で定義した新しい列
            vm_cols_to_add = {
                "drive_type": "VARCHAR", "body_type": "VARCHAR",
                "total_weight_kg": "INTEGER", "engine_weight_kg": "INTEGER",
                "kouzan_weight_kg": "INTEGER", "wiring_weight_kg": "INTEGER",
                "press_weight_kg": "INTEGER"
            }
            for col, col_type in vm_cols_to_add.items():
                if col not in vm_columns:
                    print(f"  - 'vehiclemaster' テーブルに '{col}' 列を追加します...")
                    connection.execute(text(f'ALTER TABLE vehiclemaster ADD COLUMN {col} {col_type}'))
            
            # --- componentvalue テーブルの列をチェック ---
            cv_columns = [c["name"] for c in inspector.get_columns("componentvalue")]
            if "model_code" not in cv_columns:
                print("  - 'componentvalue' テーブルに 'model_code' 列を追加します...")
                connection.execute(text('ALTER TABLE componentvalue ADD COLUMN model_code VARCHAR'))

            # --- saleshistory テーブルの列をチェック ---
            sh_columns = [c["name"] for c in inspector.get_columns("saleshistory")]
            if "buyer_location" not in sh_columns:
                print("  - 'saleshistory' テーブルに 'buyer_location' 列を追加します...")
                connection.execute(text('ALTER TABLE saleshistory ADD COLUMN buyer_location VARCHAR'))

            trans.commit()
        
        print("✅ マイグレーションが完了しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    run_migration()