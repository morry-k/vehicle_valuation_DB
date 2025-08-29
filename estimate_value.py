import sys
from sqlalchemy.orm import sessionmaker, Session
from src.db.database import engine
from src.db.models import VehicleMaster, ComponentValue
from src.config import VALUATION_PRICES, WEIGHT_BASE_RATIOS

def get_component_price(session: Session, item_name: str, vehicle: VehicleMaster) -> float:
    """
    部品の価値を検索するヘルパー関数
    優先順位： 1. 車種専用価格 -> 2. 汎用エンジン価格 -> 3. 設定ファイルの基本価格
    """
    # 1. 車種専用価格を検索 (model_codeとitem_nameが一致)
    price_record = session.query(ComponentValue).filter_by(
        item_name=item_name,
        model_code=vehicle.model_code
    ).first()
    if price_record:
        print(f"（情報: {vehicle.model_code}専用の'{item_name}'価格を適用）")
        return price_record.average_price

    # 2. 汎用エンジン価格を検索 (engine_modelとitem_nameが一致)
    if "エンジン" in item_name and vehicle.engine_model:
        price_record = session.query(ComponentValue).filter_by(
            item_name=item_name, engine_model=vehicle.engine_model, model_code=None
        ).order_by(ComponentValue.sample_size.desc()).first()
        if price_record:
            print(f"（情報: {vehicle.engine_model}搭載車の'{item_name}'価格を適用）")
            return price_record.average_price
        
    # 3. 基本価格を返す (config.pyから)
    # "Hybrid Battery" -> "hybrid_battery_price" のようにキーを生成
    default_price_key = item_name.lower().replace(" ", "_").replace("/", "_") + "_price"
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
        remarks = []

        # --- エンジン価値の判定 ---
        engine_resale_value = get_component_price(session, "エンジン/ミッション", vehicle)
        engine_material_value = 0.0
        if vehicle.total_weight_kg:
            engine_weight = vehicle.engine_weight_kg if vehicle.engine_weight_kg else (vehicle.total_weight_kg * 0.15)
            engine_material_value = engine_weight * VALUATION_PRICES["engine_per_kg"]
            if not vehicle.engine_weight_kg:
                remarks.append("エンジン重量は車両総重量からの推定値")

        if engine_resale_value > engine_material_value:
            breakdown["エンジン/ミッション (部品推奨)"] = engine_resale_value
            total_value += engine_resale_value
        else:
            breakdown["エンジン (素材価値)"] = engine_material_value
            total_value += engine_material_value

        # --- 重量ベースの価値を計算 ---
        if vehicle.total_weight_kg:
            press_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["press"]) * VALUATION_PRICES["press_per_kg"]
            kouzan_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["kouzan"]) * VALUATION_PRICES["kouzan_per_kg"]
            harness_value = (vehicle.total_weight_kg * WEIGHT_BASE_RATIOS["harness"]) * VALUATION_PRICES["harness_per_kg"]
            
            breakdown["プレス材 (鉄)"] = press_value
            breakdown["甲山 (ミックスメタル)"] = kouzan_value
            breakdown["ハーネス (銅)"] = harness_value
            total_value += press_value + kouzan_value + harness_value
        
        # --- その他の部品価値（固定価格および特別価格） ---
        breakdown["アルミホイール"] = VALUATION_PRICES["aluminum_wheels_price"]
        total_value += VALUATION_PRICES["aluminum_wheels_price"]

        # データベースに特別価格が定義されている可能性のある部品をチェック
        special_items_to_check = ["Catalyst", "Hybrid Battery", "EV Battery"]
        for item_name in special_items_to_check:
            special_value = get_component_price(session, item_name, vehicle)
            # 価値が見つかった場合（基本価格=0より大きい場合）のみ内訳に追加
            if special_value > 0:
                breakdown[item_name] = special_value
                total_value += special_value
        
        # --- 結果を表示 ---
        print("\n【価値の内訳】")
        for item, value in breakdown.items():
            print(f"- {item:<25}: {value:,.0f} 円")
        
        print("----------------------------------------")
        print(f"合計見積価値: {total_value:,.0f} 円")

        if remarks:
            print("\n【備考】")
            for remark in remarks:
                print(f"- {remark}")

    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python estimate_value.py [型式]")
        print("例:   python estimate_value.py ZVW30")
    else:
        target_model_code = sys.argv[1].upper()
        estimate_scrap_value(target_model_code)