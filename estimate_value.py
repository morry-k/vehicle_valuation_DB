import sys
from sqlalchemy.orm import sessionmaker, Session
from src.db.database import engine
from src.db.models import VehicleMaster, ComponentValue
from src.config import VALUATION_PRICES

def get_component_price(session: Session, item_name: str, vehicle: VehicleMaster) -> float:
    """
    部品の価値を検索するヘルパー関数
    優先順位： 1. 車種専用価格 -> 2. 汎用部品価格 -> 3. 設定ファイルの基本価格
    """
    # 1. まず、車種指定の「特別価格」を検索
    price_record = session.query(ComponentValue).filter_by(
        item_name=item_name,
        model_code=vehicle.model_code
    ).first()
    if price_record:
        print(f"（情報: {vehicle.model_code}専用の'{item_name}'価格を適用）")
        return price_record.average_price

    # 2. なければ、エンジン型式ベースの「汎用価格」を検索
    if vehicle.engine_model:
        price_record = session.query(ComponentValue).filter_by(
            item_name=item_name,
            engine_model=vehicle.engine_model
        ).order_by(ComponentValue.sample_size.desc()).first()
        if price_record:
            print(f"（情報: {vehicle.engine_model}搭載車の'{item_name}'価格を適用）")
            return price_record.average_price

    # 3. それでもなければ、config.pyの基本価格を返す
    default_price_key = item_name.lower().replace("/", "_") + "_price"
    return VALUATION_PRICES.get(default_price_key, 0.0)


def estimate_scrap_value(model_code_to_find: str):
    """
    指定された型式の車両価値を見積もる
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        vehicle = session.query(VehicleMaster).filter_by(model_code=model_code_to_find).first()
        if not vehicle:
            print(f"エラー: 型式 '{model_code_to_find}' が車種辞書に見つかりません。")
            return

        print(f"--- 車両価値の見積もり: {vehicle.maker} {vehicle.car_name or ''} ({vehicle.model_code}) ---")
        if vehicle.drive_type or vehicle.body_type:
             print(f"駆動方式: {vehicle.drive_type or '不明'}, ボディタイプ: {vehicle.body_type or '不明'}")
        
        breakdown = {}
        total_value = 0.0

        # --- 1. エンジン価値を判定 ---
        engine_resale_value = get_component_price(session, "エンジン/ミッション", vehicle)
        engine_material_value = 0.0
        if vehicle.engine_weight_kg:
            engine_material_value = vehicle.engine_weight_kg * VALUATION_PRICES["engine_per_kg"]
        elif vehicle.total_weight_kg:
            engine_material_value = (vehicle.total_weight_kg * 0.15) * VALUATION_PRICES["engine_per_kg"]

        if engine_resale_value > engine_material_value:
            breakdown["エンジン/ミッション (部品推奨)"] = engine_resale_value
            total_value += engine_resale_value
        else:
            breakdown["エンジン (素材価値)"] = engine_material_value
            total_value += engine_material_value

        # --- 2. 重量ベースの価値を計算 ---
        if vehicle.total_weight_kg:
            press_weight = vehicle.total_weight_kg * 0.60
            kouzan_weight = vehicle.total_weight_kg * 0.15
            press_value = press_weight * VALUATION_PRICES["press_per_kg"]
            kouzan_value = kouzan_weight * VALUATION_PRICES["kouzan_per_kg"]
            breakdown["プレス材 (鉄)"] = press_value
            breakdown["甲山 (ミックスメタル)"] = kouzan_value
            total_value += press_value + kouzan_value
        
        # --- 3. その他の部品価値を加算 ---
        # ハイブリッドバッテリーや触媒など、車種によって価値が大きく異なる部品
        battery_value = get_component_price(session, "Hybrid Battery", vehicle)
        if battery_value > 0:
            breakdown["ハイブリッドバッテリー"] = battery_value
            total_value += battery_value

        catalyst_value = get_component_price(session, "Catalyst", vehicle)
        breakdown["触媒"] = catalyst_value
        total_value += catalyst_value
        
        # 固定価格の部品
        breakdown["ハーネス (銅)"] = VALUATION_PRICES["harness_price"]
        breakdown["アルミホイール"] = VALUATION_PRICES["aluminum_wheels_price"]
        total_value += VALUATION_PRICES["harness_price"] + VALUATION_PRICES["aluminum_wheels_price"]

        # --- 4. 結果を表示 ---
        print("\n【価値の内訳】")
        for item, value in breakdown.items():
            print(f"- {item:<25}: {value:,.0f} 円")
        
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