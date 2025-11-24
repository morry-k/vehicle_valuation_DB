import sys
from pathlib import Path

# ▼▼▼ このブロックをファイルの「一番上」に追加してください ▼▼▼
# 現在のファイル(auction_scraper.py)から見て3階層上（プロジェクトルート）を検索パスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

import json
import time
import re
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright

# プロジェクトルートを検索パスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.db.database import get_market_session
from src.db.models import AuctionMarketData

# --- 設定 ---
BASE_URL = "https://www.aucsupport.com/soubalist.aspx"
MODEL_LIST_PATH = Path(__file__).parent / "car_models.json"

# 年式区分
YEAR_RANGES = [
    (1995, 2005), (2006, 2010),
    (2011, 2015), (2016, 2020), (2021, 2025),
]

def parse_price_range(price_text):
    """ '37 ～ 42' のような価格帯文字列を (min, max) の数値に変換 """
    if not price_text: return 0, 0
    try:
        clean = price_text.replace("万円", "").replace(",", "").strip()
        if re.search(r"[～〜\-]", clean):
            parts = re.split(r"[～〜\-]", clean)
            return int(re.sub(r"\D", "", parts[0])), int(re.sub(r"\D", "", parts[1]))
        else:
            val = int(re.sub(r"\D", "", clean))
            return val, val
    except:
        return 0, 0

def save_car_data(data_list, session, source_url):
    """ リスト化された1台分のテキストデータを解析してDBに保存（重複チェックなし） """
    try:
        # データリストが短すぎる場合は処理しない
        # ▼▼▼ 修正点: 14 から 13 に変更 ▼▼▼
        if len(data_list) < 13: return False

        # --- データの取得（固定インデックス）---
        maker = data_list[0]
        car_name = data_list[1]
        year_str = data_list[2]
        shift = data_list[3]
        mileage_str = data_list[4]
        model_code = data_list[5]
        score = data_list[6]
        price_text = data_list[7]
        
        # 日付の位置を動的に探す
        date_index = -1
        for idx in range(8, len(data_list)):
            if re.match(r"^\d{4}年\d{1,2}月$", data_list[idx]):
                date_index = idx
                break
        
        if date_index == -1: return False

        data_date = data_list[date_index]
        
        def get_data(lst, idx): return lst[idx] if idx < len(lst) else ""

        grade = get_data(data_list, date_index + 1)
        displacement_cc_str = get_data(data_list, date_index + 2)
        
        # 車検/色の柔軟な判別ロジック
        val1 = get_data(data_list, date_index + 3)
        val2 = get_data(data_list, date_index + 4)
        
        if re.search(r"^\d", val1) or re.search(r"[RSH]", val1): # RやHや数字で始まる場合は車検と判断
            inspection = val1
            color = val2
            equipment = get_data(data_list, date_index + 5)
        else:
            inspection = ""
            color = val1
            equipment = get_data(data_list, date_index + 4)

        # --- 数値変換 ---
        p_min, p_max = parse_price_range(price_text)
        try: year = int(re.sub(r"\D", "", year_str))
        except: year = 0
        try: cc = int(re.sub(r"\D", "", displacement_cc_str))
        except: cc = 0
        try: mileage = int(re.sub(r"\D", "", mileage_str))
        except: mileage = 0

        record = AuctionMarketData(
            auction_date=datetime.now().date(),
            auction_venue="AucSupport",
            maker=maker,
            car_name=car_name,
            grade=grade,
            model_code=model_code,
            year=year,
            displacement_cc=cc,
            mileage=mileage,
            color=color,
            inspection=inspection,
            equipment=equipment,
            shift=shift,
            score=score,
            price_min=p_min,
            price_max=p_max,
            data_date=data_date,
            source_url=source_url
        )

        session.add(record)
        return True

    except Exception:
        # 異常なデータはスキップ
        return False

def process_current_page(page, session, source_url):
    """ 
    ページ解析・保存
    戻り値: (saved_count, total_maker_found)
    """
    count = 0
    maker_found_count = 0

    try:
        content_text = page.locator("body").inner_text()
        lines = [line.strip() for line in content_text.split('\n') if line.strip()]
        
        # ヘッダーを探してデータの開始位置を特定
        start_index = -1
        for i, line in enumerate(lines):
            if line == "装備":
                start_index = i + 1
                break
        
        if start_index == -1: return 0, 0

        current_car = []
        KNOWN_MAKERS = ["トヨタ", "日産", "ホンダ", "マツダ", "スバル", "三菱", "スズキ", "ダイハツ", "レクサス", "輸入車",
                        "メルセデス・ベンツ", "ＢＭＷ", "アウディ", "フォルクスワーゲン", "ポルシェ", "ボルボ", "ジープ", "ランドローバー"]

        for i in range(start_index, len(lines)):
            line = lines[i]
            
            if line in KNOWN_MAKERS:
                maker_found_count += 1
                # 前の車を処理
                # ▼▼▼ 修正点: 14 から 13 に変更 ▼▼▼
                if len(current_car) >= 13:
                    if save_car_data(current_car, session, source_url):
                        count += 1
                current_car = [line] # 新しい車をスタート
            else:
                current_car.append(line)

        # 最後の1台
        if len(current_car) >= 13: # ▼▼▼ 修正点: 14 から 13 に変更 ▼▼▼
            if save_car_data(current_car, session, source_url):
                count += 1
            
        session.commit()
        return count, maker_found_count

    except Exception as e:
        return 0, 0

def run_bulk_scraper():
    print("🤖 大規模スクレイピング（最終修正版）を開始します...")
    
    if not MODEL_LIST_PATH.exists():
        print(f"❌ エラー: 車種リストが見つかりません: {MODEL_LIST_PATH}")
        return

    with open(MODEL_LIST_PATH, "r", encoding="utf-8") as f:
        target_dict = json.load(f)

    session = get_market_session()
    total_saved_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            for maker, car_list in target_dict.items():
                print(f"\n{'='*40}")
                print(f"🏭 メーカー: {maker} (全{len(car_list)}車種)")
                print(f"{'='*40}")
                
                for car_name in car_list:
                    print(f"\n🚗 車種: {car_name}")
                    
                    for start_year, end_year in YEAR_RANGES:
                        range_label = f"{start_year}-{end_year}"
                        
                        try:
                            target_url = f"{BASE_URL}?MAKER={maker}&CARNAME={car_name}&SYEAR={start_year}&EYEAR={end_year}"
                            
                            page.goto(target_url)
                            
                            try:
                                page.wait_for_load_state("networkidle", timeout=10000)
                            except: pass
                            time.sleep(2) 

                            # 100件表示ボタン処理
                            try:
                                limit_btn = page.get_by_text("100", exact=True)
                                if limit_btn.count() > 0 and limit_btn.first.is_visible():
                                    limit_btn.first.click()
                                    try:
                                        page.wait_for_load_state("networkidle", timeout=10000)
                                    except: pass
                                    time.sleep(4) 
                            except Exception:
                                pass

                            # 解析と保存
                            saved_count, total_found = process_current_page(page, session, target_url)
                            
                            if saved_count > 0:
                                print(f"   ✅ {range_label}: {saved_count} 件保存 (検出: {total_found})")
                                total_saved_count += saved_count
                            else:
                                msg = f"検出 {total_found} 件" if total_found > 0 else "データなし"
                                print(f"   . {range_label}: {msg}")

                            time.sleep(1)

                        except Exception as e:
                            print(f"   ❌ エラー ({range_label}): {e}")
                            continue

        except Exception as e:
            print(f"\n❌ 全体エラー発生: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print(f"\n🎉 全処理完了！ 合計保存件数: {total_saved_count} 件")
            browser.close()
            session.close()

if __name__ == "__main__":
    run_bulk_scraper()