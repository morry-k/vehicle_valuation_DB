import sys
from sqlalchemy.orm import sessionmaker, Session
# --- インポート文をすべて src からの絶対パスに統一 ---
from src.db.database import engine, SessionLocal
from src.db.models import VehicleMaster, ComponentValue
from src.config import VALUATION_PRICES, WEIGHT_BASE_RATIOS
from src.db.database import SessionLocal # SessionLocalを直接インポート



def get_component_price(session: Session, item_name: str, vehicle: VehicleMaster) -> float:
    # ... (このヘルパー関数は変更の必要はありません) ...
    price_record = session.query(ComponentValue).filter_by(item_name=item_name, model_code=vehicle.model_code).first()
    if price_record:
        return price_record.average_price
    if "エンジン" in item_name and vehicle.engine_model:
        price_record = session.query(ComponentValue).filter_by(item_name=item_name, engine_model=vehicle.engine_model, model_code=None).order_by(ComponentValue.sample_size.desc()).first()
        if price_record:
            return price_record.average_price
    default_price_key = item_name.lower().replace(" ", "_").replace("/", "_") + "_price"
    return VALUATION_PRICES.get(default_price_key, 0.0)

def calculate_material_value(vehicle: VehicleMaster, current_prices: dict) -> float:
    """
    車両の素材価値（プレス材、甲山、ハーネスなど）の合計を計算する
    """
    if not vehicle.total_weight_kg:
        return 0.0

    press_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["press"]) * current_prices.get("press_per_kg", 0)
    kouzan_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["kouzan"]) * current_prices.get("kouzan_per_kg", 0)
    harness_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["harness"]) * current_prices.get("harness_per_kg", 0)
    
    return press_value + kouzan_value + harness_value

def estimate_scrap_value(model_code_to_find: str, session: Session, custom_prices: dict = None):
    """
    指定された型式の車両価値を見積もり、辞書として返す
    DBに存在しない場合でも、空の情報を返す
    """
    vehicle = session.query(VehicleMaster).filter_by(model_code=model_code_to_find).first()
    
    # ▼▼▼ ここからが修正箇所 ▼▼▼
    if not vehicle:
        # DBに車種が見つからない場合、"error"を返すのではなく、
        # 空のvehicle_infoと、価値0の結果を返す
        return {
            "vehicle_info": {"model_code": model_code_to_find}, # 型式だけは返す
            "breakdown": {"エンジン部品販売": "×"},
            "total_value": 0,
            "remarks": ["DBに車種未登録"]
        }
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    current_prices = VALUATION_PRICES.copy()
    if custom_prices:
        current_prices.update(custom_prices)
    
    breakdown = {}
    total_value = 0.0
    remarks = []
    
    # --- エンジン価値の判定 ---
    engine_resale_value = get_component_price(session, "エンジン/ミッション", vehicle)
    engine_material_value = 0.0
    if vehicle.total_weight_kg:
        engine_weight = vehicle.engine_weight_kg if vehicle.engine_weight_kg else (vehicle.total_weight_kg * 0.15)
        engine_material_value = engine_weight * current_prices["engine_per_kg"]
        if not vehicle.engine_weight_kg:
            remarks.append("エンジン重量は車両総重量からの推定値")

    # ▼▼▼ 「エンジン部品販売」のロジック ▼▼▼
    if engine_resale_value > 0:
        breakdown["エンジン部品販売"] = "〇"
    else:
        breakdown["エンジン部品販売"] = "×"

    # 価値の高い方を合計に加算
    if engine_resale_value > engine_material_value:
        breakdown["エンジン/ミッション"] = engine_resale_value
        total_value += engine_resale_value
    else:
        breakdown["エンジン/ミッション"] = engine_material_value
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
    special_items_to_check = ["Catalyst", "Hybrid Battery"]
    for item_name in special_items_to_check:
        special_value = get_component_price(session, item_name, vehicle)
        if special_value > 0:
            breakdown[item_name] = special_value
            total_value += special_value

    # --- 輸送費を減算 ---
    transport_cost = custom_prices.get("transport_cost", 0)
    if transport_cost > 0:
        breakdown["輸送費 (減算)"] = -transport_cost
        total_value -= transport_cost
            
    # ▼▼▼ vehicle.dict()を使い、DBの全情報を返すように修正 ▼▼▼
    vehicle_info = vehicle.dict()
    
    return {
        "vehicle_info": vehicle_info,
        "breakdown": breakdown,
        "total_value": total_value,
        "remarks": remarks
    }

# このファイルが直接実行された場合の処理
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python estimate_value.py [型式]")
    else:
        target_model_code = sys.argv[1].upper()
        session = SessionLocal()
        try:
            result = estimate_scrap_value(target_model_code, session)
            if "error" in result:
                print(result["error"])
            else:
                info = result['vehicle_info']
                print(f"--- 車両価値の見積もり: {info.get('maker')} {info.get('car_name')} ({info.get('model_code')}) ---")
                if info.get('drive_type') or info.get('body_type'):
                    print(f"駆動方式: {info.get('drive_type', '不明')}, ボディタイプ: {info.get('body_type', '不明')}")

                print("\n【価値の内訳】")
                for item, value in result['breakdown'].items():
                    print(f"- {item:<25}: {value:,.0f} 円")
                
                print("----------------------------------------")
                print(f"合計見積価値: {result['total_value']:,.0f} 円")

                if result.get("remarks"):
                    print("\n【備考】")
                    for remark in result["remarks"]:
                        print(f"- {remark}")
        finally:
            session.close()