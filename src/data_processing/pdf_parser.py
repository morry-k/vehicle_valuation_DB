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
}

def extract_vehicles_from_pdf(pdf_path: str) -> list:
    """
    単語を行にグループ化するロジックを改善した最終版パーサー
    """
    all_vehicles = []
    with pdfplumber.open(pdf_path) as pdf:
        
        # 集計表である最後の3ページを除外
        pages_to_process = pdf.pages[:-3] 
        
        for page_num, page in enumerate(pages_to_process):
            print(f"  - ページ {page_num + 1} を解析中...")
            
            # 1. ページ上のすべての単語とその座標を取得
            words = page.extract_words(x_tolerance=2, y_tolerance=3)
            if not words:
                continue

            # 2. 単語をy座標（top）を基準に行ごとにグループ化する
            lines = {}
            for word in words:
                # y座標を5ピクセルの範囲で丸めて、同じ行の単語をグループ化
                line_key = round(word['top'] / 5) * 5
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append(word)

            # 3. 各行の単語を、COLUMN_BOUNDARIESに基づいて列に割り当てる
            for line_key in sorted(lines.keys()):
                line_words = sorted(lines[line_key], key=lambda w: w['x0'])
                row_data = {key: [] for key in COLUMN_BOUNDARIES.keys()}
                
                for word in line_words:
                    for col_name, (x0, x1) in COLUMN_BOUNDARIES.items():
                        if word['x0'] >= x0 and word['x1'] <= x1:
                            row_data[col_name].append(word['text'])
                            break
                
                final_row = {key: " ".join(value) for key, value in row_data.items()}

                if final_row.get("auction_no") and final_row["auction_no"].strip().isdigit():
                    all_vehicles.append(final_row)
                else:
                    if any(val.strip() for val in final_row.values()):
                        print(f"  -> [除外] {final_row}")
                    
    return all_vehicles