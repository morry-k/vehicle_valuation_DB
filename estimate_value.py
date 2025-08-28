import sys
import pandas as pd
from sqlalchemy.orm import sessionmaker
from src.db.database import engine
from src.db.models import VehicleMaster, ComponentValue

# --- 価値算定のための基本設定（今後、より精緻なマスタにできます） ---
# 素材1kgあたりの単価
PRESS_PRICE_PER_KG = 25.5  # プレス材（鉄）
HARNESS_PRICE_PER_KG = 400 # ハーネス（銅）

# 平均的な部品の価値や重量
HARNESS_AVG_WEIGHT_KG = 18 # ハーネスの平均重量
ALUMINUM_WHEELS_PRICE = 4800 # アルミホイールの基本価値

def estimate_scrap_value(model_code_to_find: str):
    """
    指定された型式の車両価値を見積もる
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # --- 1. 車種辞書(VehicleMaster)から、対象車両の「設計図」を取得 ---
        vehicle = session.query(VehicleMaster).filter_by(model_code=model_code_to_find).first()
        
        if not vehicle:
            print(f"エラー: 型式 '{model_code_to_find}' が車種辞書に見つかりません。")
            return

        print(f"--- 車両価値の見積もり: {vehicle.maker} {vehicle.car_name or ''} ({vehicle.model_code}) ---")
        
        breakdown = {} # 価値の内訳を記録する辞書
        total_value = 0

        # --- 2. 部品価格表(ComponentValue)から、エンジン/ミッションの価値を取得 ---
        engine_value = 0
        if vehicle.engine_model:
            # 「標準状態(standard)」のエンジン/ミッションの価格を検索
            comp_value = session.query(ComponentValue).filter_by(
                item_name="エンジン/ミッション",
                engine_model=vehicle.engine_model,
                details_tags="standard" # 最も基本的な状態の価格を基準とする
            ).first()
            
            if comp_value:
                engine_value = comp_value.average_price
        
        breakdown["エンジン/ミッション"] = engine_value
        total_value += engine_value

        # --- 3. その他の部品価値を計算 ---
        # 重量からプレス材（鉄）とハーネス（銅）の価値を計算
        if vehicle.weight_kg:
            # 車両重量の60%がプレス材だと仮定
            press_weight = vehicle.weight_kg * 0.6
            press_value = press_weight * PRESS_PRICE_PER_KG
            breakdown["プレス材 (鉄)"] = press_value
            total_value += press_value
        
        # ハーネスは平均重量で計算
        harness_value = HARNESS_AVG_WEIGHT_KG * HARNESS_PRICE_PER_KG
        breakdown["ハーネス (銅)"] = harness_value
        total_value += harness_value
        
        # アルミホイールは固定価格と仮定
        breakdown["アルミホイール"] = ALUMINUM_WHEELS_PRICE
        total_value += ALUMINUM_WHEELS_PRICE
        
        # --- 4. 結果を表示 ---
        print("\n【価値の内訳】")
        for item, value in breakdown.items():
            # :<15 は左揃え15文字幅、,:,.0f は3桁区切りカンマ付き整数
            print(f"- {item:<18}: {value:,.0f} 円")
        
        print("------------------------------------")
        print(f"合計見積価値: {total_value:,.0f} 円")

    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python estimate_value.py [型式]")
        print("例:   python estimate_value.py ZVW30")
    else:
        target_model_code = sys.argv[1].upper() # 大文字に変換
        estimate_scrap_value(target_model_code)