import sys
from sqlalchemy.orm import sessionmaker, Session
from src.db.database import engine
from src.db.models import VehicleMaster, ComponentValue
from src.config import VALUATION_PRICES, WEIGHT_BASE_RATIOS

def get_component_price(session: Session, item_name: str, vehicle: VehicleMaster) -> float:
    """
    部品の価値を検索するヘルパー関数
    """
    # 1. 車種専用価格を検索
    price_record = session.query(ComponentValue).filter_by(
        item_name=item_name, model_code=vehicle.model_code
    ).first()
    if price_record:
        print(f"（情報: {vehicle.model_code}専用の'{item_name}'価格を適用）")
        return price_record.average_price

    # 2. 汎用エンジン価格を検索
    if "エンジン" in item_name and vehicle.engine_model:
        price_record = session.query(ComponentValue).filter_by(
            item_name=item_name, engine_model=vehicle.engine_model, model_code=None
        ).order_by(ComponentValue.sample_size.desc()).first()
        if price_record:
            print(f"（情報: {vehicle.engine_model}搭載車の'{item_name}'価格を適用）")
            return price_record.average_price
        
    # 3. 基本価格を返す
    default_price_key = item_name.lower().replace(" ", "_").replace("/", "_") + "_price"
    return VALUATION_PRICES.get(default_price_key, 0.0)


def estimate_scrap_value(model_code_to_find: str, session: Session, custom_prices: dict = None):
    """
    指定された型式の車両価値を見積もり、辞書として返す
    """
    vehicle = session.query(VehicleMaster).filter_by(model_code=model_code_to_find).first()
    if not vehicle:
        return {"error": f"型式 '{model_code_to_find}' が車種辞書に見つかりません。"}

    current_prices = VALUATION_PRICES.copy()
    if custom_prices:
        current_prices.update(custom_prices)
    
    breakdown = {}
    total_value = 0.0
    
    # --- エンジン価値の判定 ---
    engine_resale_value = get_component_price(session, "エンジン/ミッション", vehicle)
    engine_material_value = 0.0
    if vehicle.total_weight_kg:
        engine_weight = vehicle.engine_weight_kg if vehicle.engine_weight_kg else (vehicle.total_weight_kg * 0.15)
        engine_material_value = engine_weight * current_prices["engine_per_kg"]

    if engine_resale_value > engine_material_value:
        breakdown["エンジン/ミッション (部品推奨)"] = engine_resale_value
        total_value += engine_resale_value
    else:
        breakdown["エンジン (素材価値)"] = engine_material_value
        total_value += engine_material_value

    # --- 重量ベースの価値を計算 ---
    if vehicle.total_weight_kg:
        press_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["press"]) * current_prices["press_per_kg"]
        kouzan_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["kouzan"]) * current_prices["kouzan_per_kg"]
        harness_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["harness"]) * current_prices["harness_per_kg"]
        breakdown["プレス材 (鉄)"] = press_value
        breakdown["甲山 (ミックスメタル)"] = kouzan_value
        breakdown["ハーネス (銅)"] = harness_value
        total_value += press_value + kouzan_value + harness_value
    
    # --- その他の部品価値 ---
    breakdown["アルミホイール"] = current_prices["aluminum_wheels_price"]
    total_value += current_prices["aluminum_wheels_price"]

    special_items_to_check = ["Catalyst", "Hybrid Battery", "EV Battery"]
    for item_name in special_items_to_check:
        special_value = get_component_price(session, item_name, vehicle)
        if special_value > 0:
            breakdown[item_name] = special_value
            total_value += special_value

    # --- 輸送費を減算 ---
    transport_cost = custom_prices.get("transport_cost", 0)
    if transport_cost > 0:
        breakdown[f"輸送費 (減算)"] = -transport_cost
        total_value -= transport_cost
            
    vehicle_info = {
        "maker": vehicle.maker, "car_name": vehicle.car_name or "",
        "model_code": vehicle.model_code, "year": vehicle.year, "grade": vehicle.grade
    }
    
    # 最終的な結果を辞書として返す
    return {
        "vehicle_info": vehicle_info,
        "breakdown": breakdown,
        "total_value": total_value
    }

# このファイルが直接実行された場合のみ、以下の処理を行う
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python estimate_value.py [型式]")
        print("例:   python estimate_value.py ZVW30")
    else:
        target_model_code = sys.argv[1].upper()
        
        # データベースセッションを作成して関数に渡す
        session = SessionLocal()
        try:
            result = estimate_scrap_value(target_model_code, session)
            
            if "error" in result:
                print(result["error"])
            else:
                info = result['vehicle_info']
                print(f"--- 車両価値の見積もり: {info['maker']} {info['car_name']} ({info['model_code']}) ---")
                print("\n【価値の内訳】")
                for item, value in result['breakdown'].items():
                    print(f"- {item:<25}: {value:,.0f} 円")
                print("----------------------------------------")
                print(f"合計見積価値: {result['total_value']:,.0f} 円")

        finally:
            session.close()