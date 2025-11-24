import sys
from pathlib import Path

# プロジェクトルートを検索パスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from src.db.database import get_market_session
from src.db.models import AuctionMarketData

# --- 設定 ---
TARGET_URL = "https://www.aucsupport.com/soubalist.aspx?MAKER=%e3%83%88%e3%83%a8%e3%82%bf&CARNAME=%e3%83%97%e3%83%ac%e3%83%9f%e3%82%aa&SYEAR=2015&EYEAR=2025"

def parse_price_range(price_text):
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

def run_scraper():
    print("🤖 スクレイピングを開始します（デバッグ・スキャン強化版）...")
    
    session = get_market_session()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            print(f"アクセス中: {TARGET_URL}")
            page.goto(TARGET_URL)
            page.wait_for_load_state("networkidle")
            
            # 念のため少し待機（コンテンツの完全ロード待ち）
            time.sleep(3)

            # ページ全体のテキストを取得し、整形
            content_text = page.locator("body").inner_text()
            
            # タブや連続する改行を整理してリスト化
            lines = []
            for line in content_text.split('\n'):
                clean_line = line.strip()
                if clean_line:
                    lines.append(clean_line)
            
            print(f"取得したテキスト行数: {len(lines)}")

            # データの開始位置を探す
            start_index = -1
            try:
                for i, line in enumerate(lines):
                    # ヘッダーの「装備」を探す
                    if line == "装備":
                        start_index = i + 1
                        print(f"✅ ヘッダー終了位置を検出しました (Index: {i})")
                        break
                
                if start_index == -1:
                    print("⚠️ '装備' が見つかりません。テキストの先頭から探索します。")
                    start_index = 0

            except ValueError:
                pass
            
            count = 0
            current_car = []
            
            KNOWN_MAKERS = ["トヨタ", "日産", "ホンダ", "マツダ", "スバル", "三菱", "スズキ", "ダイハツ", "レクサス", "輸入車",
                            "メルセデス・ベンツ", "ＢＭＷ", "アウディ", "フォルクスワーゲン", "ポルシェ", "ボルボ", "ジープ", "ランドローバー"]

            print("データ解析を実行中...")

            for i in range(start_index, len(lines)):
                line = lines[i]
                
                # メーカー名かチェック（完全一致または「トヨタ」のみの行）
                is_new_car = line in KNOWN_MAKERS
                
                if is_new_car:
                    # データが溜まっていれば保存処理へ
                    if len(current_car) >= 10: # 14未満でも一旦チェックする
                        process_car_data(current_car, session)
                        count += 1
                    
                    # 新しい車のデータを開始
                    current_car = [line]
                else:
                    # データを追加
                    current_car.append(line)
                    
                    # ▼▼▼ デバッグ用：バッファが溜まりすぎている場合の警告 ▼▼▼
                    if len(current_car) > 25:
                        # 1台分のデータは通常15行程度。25行超えるということは区切りを見逃している
                        print(f"⚠️ 警告: 区切りを見逃した可能性があります (バッファサイズ: {len(current_car)})")
                        print(f"   内容: {current_car}")
                        # 強制的にリセットして復帰を試みる（無限増殖防止）
                        current_car = []

            # 最後の1台
            if len(current_car) >= 10:
                process_car_data(current_car, session)
                count += 1

            session.commit()
            print(f"✅ {count} 件のデータを保存しました。")

        except Exception as e:
            print(f"❌ 全体エラー: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            browser.close()
            session.close()

def process_car_data(data_list, session):
    try:
        # 最低限のデータ量チェック
        if len(data_list) < 12: return

        # リストの中身をログ出力（デバッグ用）
        # print(f"解析対象: {data_list}")

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
        for idx, val in enumerate(data_list):
            # "2025年10月" のようなパターン
            if re.match(r"^\d{4}年\d{1,2}月$", val):
                date_index = idx
                break
        
        if date_index == -1:
            # 日付が見つからない場合はスキップ
            return

        data_date = data_list[date_index]
        
        # 安全にインデックスアクセス
        def get_safe(lst, idx, default=""):
            return lst[idx] if idx < len(lst) else default

        grade = get_safe(data_list, date_index + 1)
        displacement_cc_str = get_safe(data_list, date_index + 2)
        
        # 車検と色の判別
        val1 = get_safe(data_list, date_index + 3)
        val2 = get_safe(data_list, date_index + 4)
        
        if re.search(r"\d", val1):
            inspection = val1
            color = val2
            equipment_idx = date_index + 5
        else:
            inspection = ""
            color = val1
            equipment_idx = date_index + 4 # 車検がない分ずれる
            
        equipment = get_safe(data_list, equipment_idx)

        # 数値変換
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
            source_url=TARGET_URL
        )

        session.add(record)
        print(f"  + 保存: {record.car_name} ({record.model_code}) {record.price_min}-{record.price_max}万円")

    except Exception as e:
        # print(f"    データ処理エラー: {e}")
        pass

if __name__ == "__main__":
    run_scraper()