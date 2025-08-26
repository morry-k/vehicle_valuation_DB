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
    "mileage_km": (400, 456),
}

def extract_vehicles_from_pdf(pdf_path: str) -> List[Dict]:
    """
    単一のPDFファイルから車両情報のリストを抽出する
    """
    vehicles = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # ページ上のすべての単語とその座標を取得
                words = page.extract_words(x_tolerance=2, y_tolerance=2, keep_blank_chars=True)
                
                # 単語を行ごとにグループ化
                lines = {}
                for word in words:
                    # 単語の中心のy座標をキーとして行をまとめる
                    y_center = (word['top'] + word['bottom']) / 2
                    if y_center not in lines:
                        lines[y_center] = []
                    lines[y_center].append(word)

                # 各行から列データを抽出
                for y_center in sorted(lines.keys()):
                    line_words = lines[y_center]
                    row_data = {}
                    
                    for col_name, (x0, x1) in COLUMN_BOUNDARIES.items():
                        col_words = [w['text'] for w in line_words if (w['x0'] + w['x1']) / 2 >= x0 and (w['x0'] + w['x1']) / 2 < x1]
                        row_data[col_name] = "".join(col_words)

                    # ヘッダー行や空行でないことを確認（出品番号があればデータ行とみなす）
                    if row_data.get("auction_no") and len(row_data["auction_no"]) > 2:
                        vehicles.append(row_data)

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
    
    return vehicles