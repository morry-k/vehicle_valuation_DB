import sys
from sqlalchemy.orm import sessionmaker
from src.db.database import engine
from src.db.models import VehicleMaster
from src.config import VALUATION_PRICES # 作成した単価マスターをインポート

def estimate_scrap_value(model_code_to_find: str):
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # --- 1. 車種辞書から、対象車両の「設計図（重量など）」を取得 ---
        vehicle = session.query(VehicleMaster).filter_by(model_code=model_code_to_find).first()
        
        if not vehicle:
            print(f"エラー: 型式 '{model_code_to_find}' が車種辞書に見つかりません。")
            return

        print(f"--- 車両価値の見積もり: {vehicle.maker} {vehicle.car_name or ''} ({vehicle.model_code}) ---")
        
        breakdown = {}
        total_value = 0.0

        # --- 2. 重量ベースの価値を計算 ---
        # 各重量データが存在するかチェックしながら計算
        if vehicle.engine_weight_kg:
            value = vehicle.engine_weight_kg * VALUATION_PRICES["engine_per_kg"]
            breakdown["エンジン計"] = value
            total_value += value
        
        if vehicle.kouzan_weight_kg:
            value = vehicle.kouzan_weight_kg * VALUATION_PRICES["kouzan_per_kg"]
            breakdown["甲山計"] = value
            total_value += value
            
        if vehicle.wiring_weight_kg:
            value = vehicle.wiring_weight_kg * VALUATION_PRICES["wiring_per_kg"]
            breakdown["配線計"] = value
            total_value += value
            
        if vehicle.press_weight_kg:
            value = vehicle.press_weight_kg * VALUATION_PRICES["press_per_kg"]
            breakdown["プレス計"] = value
            total_value += value

        # --- 3. 固定価格の部品価値を加算 ---
        breakdown["アルミホイール"] = VALUATION_PRICES["aluminum_wheels"]
        total_value += VALUATION_PRICES["aluminum_wheels"]
        
        breakdown["触媒"] = VALUATION_PRICES["catalyst"]
        total_value += VALUATION_PRICES["catalyst"]
        
        breakdown["フロン"] = VALUATION_PRICES["freon"]
        total_value += VALUATION_PRICES["freon"]
        
        breakdown["エアバッグ"] = VALUATION_PRICES["airbag"]
        total_value += VALUATION_PRICES["airbag"]

        # --- 4. 結果を表示 ---
        print("\n【価値の内訳】")
        for item, value in breakdown.items():
            print(f"- {item:<15}: {value:,.0f} 円")
        
        print("---------------------------------")
        print(f"合計見積価値: {total_value:,.0f} 円")

    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python estimate_value.py [型式]")
        print("例:   python estimate_value.py UCF11")
    else:
        target_model_code = sys.argv[1].upper()
        estimate_scrap_value(target_model_code)