# debug_layout.py

import pdfplumber
from src.config import AUCTION_SHEETS_DIR

# --------------------------------------------------------------------------
# ▼▼▼ この辞書の値を、出力画像を見ながら調整していきます ▼▼▼
COLUMN_BOUNDARIES = {
    "auction_no": (15, 43),
    "maker": (43, 80),
    "car_name": (80, 200),
    "grade": (200, 300),
    "year": (300, 352),
    "model_code": (352, 400),
    "displacement_cc": (400, 453), # 「排気量」
    "inspection_date": (453, 486), # 「車検」
    "mileage_km": (486, 515),      # 「走行」
    "color": (515, 548),          # 「色」
}
# ▲▲▲ この辞書の値を、出力画像を見ながら調整していきます ▲▲▲
# --------------------------------------------------------------------------

def visualize_layout():
    """
    PDFの1ページ目に列の境界線を描画して、画像として出力する
    """
    print("レイアウトのデバッグを開始します...")
    
    try:
        # inputフォルダにある最初のPDFファイルを取得
        pdf_file = next(AUCTION_SHEETS_DIR.glob("*.pdf"))
    except StopIteration:
        print(f"エラー: '{AUCTION_SHEETS_DIR}' にPDFファイルが見つかりません。")
        return

    print(f"対象ファイル: {pdf_file.name}")

    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[0]
        im = page.to_image(resolution=150) # ページを画像に変換

        # 各列の「左端」に赤い縦線を引いて可視化
        for col_name, (x0, x1) in COLUMN_BOUNDARIES.items():
            im.draw_line([(x0, 0), (x0, page.height)], stroke="red", stroke_width=2)
        
        # 最後の列の右端にも線を引く
        last_col_x1 = list(COLUMN_BOUNDARIES.values())[-1][1]
        im.draw_line([(last_col_x1, 0), (last_col_x1, page.height)], stroke="red", stroke_width=2)

        output_path = "debug_layout_output.png"
        im.save(output_path, format="PNG")
        print(f"\n✅ 完了！ '{output_path}' という名前で画像を出力しました。")
        print("画像を開いて、赤い線が各列を正しく区切っているか確認してください。")

if __name__ == "__main__":
    visualize_layout()