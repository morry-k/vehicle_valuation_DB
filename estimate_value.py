import sys
from sqlalchemy.orm import sessionmaker
from src.db.database import engine
from src.db.models import VehicleMaster, ComponentValue
from src.config import VALUATION_PRICES

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

        # --- ▼▼▼ ここからエンジン価値の判定ロジック ▼▼▼ ---
        
        # 1. 部品としての市場価値を取得
        resale_value = 0.0
        if vehicle.engine_model:
            comp_value = session.query(ComponentValue).filter(
                ComponentValue.item_name.like('%エンジン%'),
                ComponentValue.engine_model == vehicle.engine_model
            ).order_by(ComponentValue.sample_size.desc()).first()
            if comp_value:
                resale_value = comp_value.average_price
                remarks.append(f"エンジン価値は {comp_value.sample_size}件 の取引データに基づく")

        # 2. 素材としての金属価値を計算
        material_value = 0.0
        if vehicle.engine_weight_kg:
            material_value = vehicle.engine_weight_kg * VALUATION_PRICES["engine_per_kg"]
            remarks.append("エンジン重量はAIによる調査値")
        elif vehicle.total_weight_kg:
            estimated_weight = vehicle.total_weight_kg * 0.15 # 総重量から推定
            material_value = estimated_weight * VALUATION_PRICES["engine_per_kg"]
            remarks.append("エンジン重量は車両総重量からの推定値")

        # 3. 価値が高い方を採用
        if resale_value > material_value:
            # 部品価値の方が高い場合
            breakdown["エンジン/ミッション (部品推奨)"] = resale_value
            total_value += resale_value
        else:
            # 素材価値の方が高い、または部品価値がない場合
            breakdown["エンジン (素材価値)"] = material_value
            total_value += material_value

        # --- ▲▲▲ エンジン価値の判定ロジックここまで ▲▲▲ ---

        # --- 重量ベースの価値を「計算」する ---
        if vehicle.total_weight_kg:
            press_weight = vehicle.total_weight_kg * 0.60
            kouzan_weight = vehicle.total_weight_kg * 0.15
            press_value = press_weight * VALUATION_PRICES["press_per_kg"]
            kouzan_value = kouzan_weight * VALUATION_PRICES["kouzan_per_kg"]
            breakdown["プレス材 (鉄)"] = press_value
            breakdown["甲山 (ミックスメタル)"] = kouzan_value
            total_value += press_value + kouzan_value

        # --- 固定価格の価値を加算 ---
        fixed_value_items = ["harness_price", "aluminum_wheels_price", "catalyst_price", "freon_price", "airbag_price"]
        item_names = {"harness_price": "ハーネス (銅)", "aluminum_wheels_price": "アルミホイール", "catalyst_price": "触媒", "freon_price": "フロン", "airbag_price": "エアバッグ"}
        for item_key in fixed_value_items:
            value = VALUATION_PRICES[item_key]
            breakdown[item_names[item_key]] = value
            total_value += value
        
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
    else:
        target_model_code = sys.argv[1].upper()
        estimate_scrap_value(target_model_code)