from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from src.db.models import AuctionMarketData
from typing import List, Tuple, Optional
import re
import math

def _parse_score_value(score_str: str) -> float:
    """ 評価点文字列を数値(-1.0, 3.0, 3.5, 4.0など)に変換するヘルパー関数 """
    if not score_str:
        return 0.0
        
    score = str(score_str).strip().upper()
    
    # 1. R点 (-1.0)
    if "R" in score or "修復" in score or score == "-1":
        return -1.0
    
    # 2. 数値点
    try:
        # "4 - きれい" や "4.5" から数字部分を抽出
        match = re.match(r"^\d(\.\d)?", score)
        if match:
            return float(match.group(0))
        return 0.0
    except:
        return 0.0

def _get_score_targets(target_score: float) -> Optional[Tuple[float, Optional[float]]]:
    """ ターゲット評価点に基づき、過去データで検索すべき上下の評価点範囲を決定する """
    
    if target_score == -1.0:
        return (-1.0, None) # R点の場合はR点データのみ
    
    if target_score == 0.0:
        return None # 評価点不明な場合は計算しない

    # 整数点 (例: 3.0, 4.0, 5.0) の場合
    if target_score == math.floor(target_score):
        return (target_score, None) # 一致する点数のみをターゲットとする
    
    # 小数点 (例: 3.5, 4.5) の場合
    # 4.5 -> (4.0, 5.0), 3.5 -> (3.0, 4.0)
    if target_score % 1.0 == 0.5:
        lower = math.floor(target_score)
        upper = math.ceil(target_score)
        return (lower, upper)
        
    return None # その他の不正な点数の場合

def _calculate_weighted_price(history: List[AuctionMarketData], target_year: int, target_mileage: int) -> float:
    """ 選別されたデータ群に対して重み付き平均を計算するコア関数 """
    weighted_sum = 0
    total_weight = 0
    valid_count = 0
    
    for h in history:
        # データ品質チェック
        if h.price_max <= 0 or h.year == 0:
            continue
            
        mileage_diff = abs(target_mileage - h.mileage) 
        year_diff = abs(target_year - h.year)
        
        # 重み計算 (距離が近いほど重い)
        # 年式差の2乗 + (走行距離差/50)の2乗 + 1
        denominator = (year_diff + 1)**2 + (mileage_diff / 50)**2 + 1
        weight = 1 / denominator

        mid_price = (h.price_min + h.price_max) / 2
        
        weighted_sum += mid_price * weight
        total_weight += weight
        valid_count += 1
        
    if total_weight == 0:
        return 0.0
        
    return (weighted_sum / total_weight)

def analyze_market_trends(model_code: str, target_year: int, target_mileage: int, target_score_str: str, session: Session):
    """
    質的フィルタリングに基づき、予想相場とトレンドを算出する
    """
    # print(f"\n--- Market Analysis: {model_code} (Year:{target_year}, Km:{target_mileage}, Score:{target_score_str}) ---")
    
    target_score_value = _parse_score_value(target_score_str)
    score_targets = _get_score_targets(target_score_value)
    
    # 評価点が不明、または計算対象外の場合は0を返す
    if not score_targets:
        # print("  -> Score target not determined. Skipping.")
        return {"market_price": 0, "trend_icon": "→", "sample_count": 0}

    lower_score, upper_score = score_targets
    final_prices = []
    total_samples = 0

    # 評価点でフィルタリングする内部関数
    def filter_by_score(query, score_value):
        if score_value == -1.0:
            # R点: 'R', '修復', '-1' を含むもの
            return query.filter(or_(
                AuctionMarketData.score.like('%R%'), 
                AuctionMarketData.score.like('%修復%'),
                AuctionMarketData.score.like('%-1%')
            ))
        else:
            # 整数点: '4' で始まるもの ('4', '4.5' もヒットするが、4.5は除外したい)
            # 単純化のため、'4%' で検索
            return query.filter(AuctionMarketData.score.like(f"{int(score_value)}%"))

    # ベースクエリ
    base_query = session.query(AuctionMarketData).filter(AuctionMarketData.model_code == model_code)

    # --- 1. 下限スコア (必須) の処理 ---
    # print(f"  -> Analyzing lower score group: {lower_score}")
    query_lower = filter_by_score(base_query, lower_score)
    history_lower = query_lower.all()
    
    if not history_lower:
        # print("  -> No history for lower score group.")
        # 片方しかデータがない場合は、計算を諦める (要件通り)
        return {"market_price": 0, "trend_icon": "?", "sample_count": 0}
    
    price_A = _calculate_weighted_price(history_lower, target_year, target_mileage)
    if price_A > 0:
        final_prices.append(price_A)
        total_samples += len(history_lower)
    else:
        return {"market_price": 0, "trend_icon": "?", "sample_count": 0}


    # --- 2. 上限スコア (小数点の場合のみ) の処理 ---
    if upper_score is not None:
        # print(f"  -> Analyzing upper score group: {upper_score}")
        query_upper = filter_by_score(base_query, upper_score)
        history_upper = query_upper.all()
        
        if not history_upper:
            # print("  -> No history for upper score group.")
            # 片方しかデータがない場合は、相場情報を出さない
            return {"market_price": 0, "trend_icon": "?", "sample_count": 0}
        
        price_B = _calculate_weighted_price(history_upper, target_year, target_mileage)
        if price_B > 0:
            final_prices.append(price_B)
            total_samples += len(history_upper)
        else:
            return {"market_price": 0, "trend_icon": "?", "sample_count": 0}


    # --- 最終結果の統合 ---
    if not final_prices:
        return {"market_price": 0, "trend_icon": "-", "sample_count": 0}
    
    final_avg_price = sum(final_prices) / len(final_prices)
    final_price_yen = int(final_avg_price * 10000)
    
    # print(f"  => Final Market Price: {final_price_yen:,} JPY (Samples: {total_samples})")

    return {
        "market_price": final_price_yen, 
        "trend_icon": "→",
        "sample_count": total_samples
    }