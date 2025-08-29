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
        if vehicle.drive_type or vehicle.body_type:
             print(f"駆動方式: {vehicle.drive_type or '不明'}, ボディタイプ: {vehicle.body_type or '不明'}")
        
        breakdown = {}
        total_value = 0.0
        remarks = [] # 備考を記録するリスト

        # --- 1. エンジン価値を部品価格表から取得 ---
        engine_value = 0.0
        if vehicle.engine_model:
            comp_value = session.query(ComponentValue).filter(
                ComponentValue.item_name.like('%エンジン%'),
                ComponentValue.engine_model == vehicle.engine_model
            ).order_by(ComponentValue.sample_size.desc()).first()
            if comp_value: 
                engine_value = comp_value.average_price
                remarks.append(f"エンジン価値は {comp_value.sample_size}件 の取引データに基づく")
        breakdown["エンジン/ミッション"] = engine_value
        total_value += engine_value

        # --- 2. 重量ベースの価値を「計算」または「推定」する ---
        if vehicle.total_weight_kg:
            engine_weight = 0
            if vehicle.engine_weight_kg:
                # DBに正確なエンジン重量があれば、それを使う
                engine_weight = vehicle.engine_weight_kg
                remarks.append("エンジン重量はAIによる調査値")
            else:
                # なければ、車両総重量の15%として推定する
                engine_weight = vehicle.total_weight_kg * 0.15
                remarks.append("エンジン重量は車両総重量からの推定値")

            # 業界知識に基づく比率で他の重量も計算
            press_weight = vehicle.total_weight_kg * 0.60
            kouzan_weight = vehicle.total_weight_kg * 0.15
            
            # エンジン素材価値（エンジン価値とは別）
            engine_material_value = engine_weight * VALUATION_PRICES["engine_per_kg"]
            breakdown["エンジン(素材価値)"] = engine_material_value
            # total_value += engine_material_value # 通常はエンジン/ミッション価値に含意されるため、ここでは加算しない

            press_value = press_weight * VALUATION_PRICES["press_per_kg"]
            kouzan_value = kouzan_weight * VALUATION_PRICES["kouzan_per_kg"]
            breakdown["プレス材 (鉄)"] = press_value
            breakdown["甲山 (ミックスメタル)"] = kouzan_value
            total_value += press_value + kouzan_value

        # --- 3. 固定価格の価値を加算 ---
        # ... (この部分は変更なし) ...
        fixed_value_items = ["harness_price", "aluminum_wheels_price", "catalyst_price", "freon_price", "airbag_price"]
        item_names = {"harness_price": "ハーネス (銅)", "aluminum_wheels_price": "アルミホイール", "catalyst_price": "触媒", "freon_price": "フロン", "airbag_price": "エアバッグ"}
        for item_key in fixed_value_items:
            value = VALUATION_PRICES[item_key]
            breakdown[item_names[item_key]] = value
            total_value += value
        
        # --- 4. 結果を表示 ---
        print("\n【価値の内訳】")
        for item, value in breakdown.items():
            print(f"- {item:<20}: {value:,.0f} 円")
        
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
    else:
        target_model_code = sys.argv[1].upper()
        estimate_scrap_value(target_model_code)