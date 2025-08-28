import sys
from sqlalchemy.orm import sessionmaker
from src.db.database import engine
from src.db.models import VehicleMaster, ComponentValue
from src.config import VALUATION_PRICES

def estimate_scrap_value(model_code_to_find: str):
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        vehicle = session.query(VehicleMaster).filter_by(model_code=model_code_to_find).first()
        if not vehicle:
            print(f"エラー: 型式 '{model_code_to_find}' が車種辞書に見つかりません。")
            return

        print(f"--- 車両価値の見積もり: {vehicle.maker} {vehicle.car_name or ''} ({vehicle.model_code}) ---")
        print(f"駆動方式: {vehicle.drive_type}, ボディタイプ: {vehicle.body_type}")
        
        breakdown = {}
        total_value = 0.0

        # --- 1. エンジン価値を部品価格表から取得 ---
        engine_value = 0.0
        if vehicle.engine_model:
            comp_value = session.query(ComponentValue).filter(
                ComponentValue.item_name.like('%エンジン%'),
                ComponentValue.engine_model == vehicle.engine_model
            ).order_by(ComponentValue.sample_size.desc()).first()
            if comp_value: engine_value = comp_value.average_price
        breakdown["エンジン/ミッション"] = engine_value
        total_value += engine_value

        # --- 2. 重量ベースの価値を「計算」する ---
        if vehicle.total_weight_kg:
            # 業界知識に基づく比率で計算
            press_weight = vehicle.total_weight_kg * 0.60
            kouzan_weight = vehicle.total_weight_kg * 0.15
            
            press_value = press_weight * VALUATION_PRICES["press_per_kg"]
            kouzan_value = kouzan_weight * VALUATION_PRICES["kouzan_per_kg"]
            breakdown["プレス材 (鉄)"] = press_value
            breakdown["甲山 (ミックスメタル)"] = kouzan_value
            total_value += press_value + kouzan_value

        # --- 3. 固定価格の価値を加算 ---
        # （より高度化するなら、これらの価格もComponentValue DBから引く）
        breakdown["ハーネス (銅)"] = VALUATION_PRICES["harness_price"]
        breakdown["アルミホイール"] = VALUATION_PRICES["aluminum_wheels"]
        breakdown["触媒"] = VALUATION_PRICES["catalyst_price"]
        total_value += VALUATION_PRICES["harness_price"] + VALUATION_PRICES["aluminum_wheels"] + VALUATION_PRICES["catalyst_price"]
        
        print("\n【価値の内訳】")
        for item, value in breakdown.items():
            print(f"- {item:<20}: {value:,.0f} 円")
        
        print("----------------------------------------")
        print(f"合計見積価値: {total_value:,.0f} 円")

    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python estimate_value.py [型式]")
    else:
        target_model_code = sys.argv[1].upper()
        estimate_scrap_value(target_model_code)