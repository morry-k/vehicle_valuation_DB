import sys
from pathlib import Path
import json
import time

# パス設定
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from playwright.sync_api import sync_playwright

# ターゲットURL (検索条件入力ページ)
# ※実際の検索フォームがあるURLを指定してください。
# もし soubalist.aspx が検索結果専用なら、その前の「検索条件入力ページ」のURLが必要です。
# ここでは仮にトップページまたは検索ページとします。
SEARCH_PAGE_URL = "https://www.aucsupport.com/searchsoubahand.aspx" 

TARGET_MAKERS = ["トヨタ", "日産", "ホンダ"]

def fetch_model_list():
    print("🚙 車種リストの自動取得を開始します...")
    
    car_models = {} # 結果を保存する辞書

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            page.goto(SEARCH_PAGE_URL)
            page.wait_for_load_state("networkidle")
            
            # ページ構造によっては、メーカーを選ぶと車種リストが動的に読み込まれる場合があります
            # ここでは一般的なドロップダウンの操作を想定しています
            
            # メーカーのセレクトボックスを探す (name属性が MAKER だと仮定)
            # 実際のサイトのHTMLを見て name="MAKER" かどうか確認してください
            maker_select_name = "MAKER"
            car_select_name = "CARNAME"

            for maker in TARGET_MAKERS:
                print(f"\n--- {maker} の車種を取得中 ---")
                
                # メーカーを選択する
                # (select_optionはvalueが必要な場合が多いですが、labelでもいける場合があります)
                # うまくいかない場合は、一度HTMLを出力してvalueを確認する必要があります
                try:
                    page.select_option(f"select[name='{maker_select_name}']", label=maker)
                    # 読み込み待ち
                    time.sleep(3) 
                except:
                    # URLパラメータでメーカー指定して移動する方が確実かもしれません
                    print(f"  -> ページ遷移でメーカー指定を試みます...")
                    page.goto(f"{SEARCH_PAGE_URL}?MAKER={maker}")
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)

                # 車種のセレクトボックスから全てのオプションを取得
                car_options = page.locator(f"select[name='{car_select_name}'] option").all()
                
                models = []
                for option in car_options:
                    text = option.inner_text().strip()
                    value = option.get_attribute("value")
                    
                    # "選択してください" や 空の選択肢を除外
                    if text and "選択" not in text and value:
                        models.append(text)
                
                print(f"  -> {len(models)} 車種を発見")
                car_models[maker] = models

            # 結果をJSONファイルに保存
            output_path = Path(__file__).parent / "car_models.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(car_models, f, ensure_ascii=False, indent=2)
            
            print(f"\n✅ 車種リストを保存しました: {output_path}")

        except Exception as e:
            print(f"❌ エラー: {e}")
            
        finally:
            browser.close()

if __name__ == "__main__":
    fetch_model_list()