import sys
from pathlib import Path

# パス設定
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from playwright.sync_api import sync_playwright

# ターゲットURL
TARGET_URL = "https://www.aucsupport.com/searchsoubahand.aspx"

def dump_table_html():
    print("🔍 HTML構造を解析するためにソースを保存します...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.goto(TARGET_URL)
            page.wait_for_load_state("networkidle")

            # ターゲットテーブルの特定
            target_table = None
            all_tables = page.locator("table").all()
            for table in all_tables:
                text = table.inner_text()
                if "メーカー" in text and "車種" in text and "価格" in text:
                    target_table = table
                    break
            
            if not target_table:
                print("❌ テーブルが見つかりません")
                return

            # ▼▼▼ ここが重要：テーブルのHTMLをそのまま取得する ▼▼▼
            html_content = target_table.inner_html()

            # ファイルに保存 (output.html)
            output_file = "debug_table_structure.html"
            with open(output_file, "w", encoding="utf-8") as f:
                # 見やすくするために簡単なHTML枠で囲む
                f.write("<html><body><table border='1'>")
                f.write(html_content)
                f.write("</table></body></html>")

            print(f"✅ HTMLを保存しました: {output_file}")
            print("このファイルをブラウザやエディタで開いて、'tr' タグの構造を確認してください。")

        except Exception as e:
            print(f"エラー: {e}")
        
        finally:
            browser.close()

if __name__ == "__main__":
    dump_table_html()