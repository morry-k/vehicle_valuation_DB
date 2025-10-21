# src/data_processing/pdf_parser.py

import pdfplumber
import pandas as pd
from typing import List, Dict

# PDFのテーブルの列の境界線 (左端と右端のx座標)
# ※この座標は実際のPDFに合わせて調整する必要があります
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
    "shift": (548, 578),      # ▲ 「シフト」を追加
    #"space": (578, 720),      # ▲ 「シフト」を追加
    "evaluation_score": (720, 750),   # 数字部分 (3.5 など)
    "evaluation_interior": (720, 750), # 内装評価 (B, C など)
}

def extract_header_info(page: pdfplumber.page.Page) -> dict:
    """PDFのページ上部からヘッダー情報（会場名、日付、コーナー名など）を抽出する"""
    header_area = page.crop((0, 0, page.width, 50))
    header_text = header_area.extract_text(x_tolerance=2, y_tolerance=2)
    
    if not header_text:
        return {}
        
    parts = header_text.split()
    corner_name = ""
    # "【コーナー別出品車リスト】" という文字列の次にある単語をコーナー名として取得
    try:
        marker_index = parts.index("【コーナー別出品車リスト】")
        if len(parts) > marker_index + 1:
            corner_name = parts[marker_index + 1]
    except ValueError:
        corner_name = "" # マーカーが見つからない場合は空にする

    header_info = {
        "auction_round": parts[0] if len(parts) > 0 else '',
        "auction_date": parts[2] if len(parts) > 2 else '',
        "auction_venue": parts[3] if len(parts) > 3 else '',
        "auction_corner": corner_name, # 抽出したコーナー名を追加
    }
    return header_info


def extract_vehicles_from_pdf(pdf_path: str) -> (dict, list):
    """
    「1行 = 1車種」のシンプルなロジックでPDFを解析する
    """
    all_vehicles = []
    header_info = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            return {}, []

        # --- ステップ1: ヘッダー情報を取得 ---
        header_info = extract_header_info(pdf.pages[0])
        
        pages_to_process = pdf.pages[:-3] if len(pdf.pages) > 3 else pdf.pages
        
        for page_num, page in enumerate(pages_to_process):
            print(f"  - ページ {page_num + 1} を解析中...")
            
            # --- ステップ2: ページ上のすべての単語を取得 ---
            words = page.extract_words(x_tolerance=2, y_tolerance=2) # y_toleranceは小さくても良い
            if not words: continue

            # --- ステップ3: 単語を行ごとにグループ化（近接行の結合ロジックは削除） ---
            lines = {}
            for word in words:
                # y座標を厳密に（1ピクセル単位で）丸めて、行をグループ化
                line_key = round(word['top'])
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append(word)

            # --- ステップ4: 各行を列に割り当て ---
            for line_key in sorted(lines.keys()):
                line_words = sorted(lines[line_key], key=lambda w: w['x0']) # x座標でソート
                
                row_data = {key: [] for key in COLUMN_BOUNDARIES.keys()}
                for word in line_words:
                    for col_name, (x0, x1) in COLUMN_BOUNDARIES.items():
                        word_center = (word['x0'] + word['x1']) / 2
                        if x0 <= word_center < x1:
                            row_data[col_name].append(word['text'])
                            break
                
                final_row = {key: " ".join(value) for key, value in row_data.items()}

                auction_no_val = final_row.get("auction_no", "").strip()
                if auction_no_val and auction_no_val.isdigit():
                    all_vehicles.append(final_row)
                else:
                    if any(val.strip() for val in final_row.values()):
                        print(f"  -> [除外/フィルタ] {final_row}")
                    
    return header_info, all_vehicles