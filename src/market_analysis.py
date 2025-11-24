from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.db.models import AuctionMarketData
import re

# ▼▼▼ インポート文を、プロジェクトのルートから見た正しい形式に修正 ▼▼▼
from src.db.models import AuctionMarketData
from src.db.database import get_market_session # 必要なセッションを取得する関数

def analyze_market_trends(model_code: str, target_year: int, target_mileage: int, session: Session):
    """
    重み付き近接分析に基づき、予想相場とトレンドを算出する
    """
    # ★デバッグ用: 検索条件を出力
    print(f"\n--- Market Analysis for Code: {model_code}, Year: {target_year}, Mileage: {target_mileage} ---")
    
    # 1. この型式の市場データを取得
    history = session.query(AuctionMarketData).filter(
        AuctionMarketData.model_code == model_code
    ).all()

    if not history:
        print(f"Market Analysis: No history records found for model_code '{model_code}'.")
        return {"market_price": 0, "trend_icon": "→", "sample_count": 0}

    print(f"Market Analysis: Found {len(history)} total records.")

    # --- 2. 重みと価格を計算 ---
    weighted_sum = 0
    total_weight = 0
    valid_count = 0
    
    for h in history:
        # 価格が有効（0より大きい）で、年式が0でないレコードのみを使用
        # ★デデバッグ用: フィルタリングされた理由を出力
        if h.price_max <= 0:
            print(f"    - Filtered: Price is 0. Model: {h.model_code}, Max Price: {h.price_max}")
            continue
        if h.year == 0:
            print(f"    - Filtered: Year is 0. Model: {h.model_code}")
            continue
            
        # 走行距離を km 単位（またはデータソースの単位）で比較
        mileage_diff = abs(target_mileage - h.mileage) 
        year_diff = abs(target_year - h.year)
        
        # 重み計算 (分母が小さいほど重い)
        denominator = (year_diff + 1)**2 + (mileage_diff / 50)**2 + 1
        weight = 1 / denominator

        mid_price = (h.price_min + h.price_max) / 2
        
        weighted_sum += mid_price * weight
        total_weight += weight
        valid_count += 1

    # 3. 最終価格を算出
    if total_weight == 0:
        # ★デバッグ用: 有効なサンプルがない場合
        print("Market Analysis: Total weight is 0. No valid samples for calculation.")
        return {"market_price": 0, "trend_icon": "→", "sample_count": 0}
        
    avg_price = (weighted_sum / total_weight)
    
    # トレンド判定は簡略化
    trend_icon = "→"
    
    final_price_yen = int(avg_price * 10000)
    
    # ★デバッグ用: 最終結果を出力
    print(f"Market Analysis: Calculated final price: {final_price_yen:,} JPY (Samples: {valid_count}).")
    
    # 万円単位を円に変換して返す
    return {
        "market_price": final_price_yen, 
        "trend_icon": trend_icon,
        "sample_count": valid_count
    }