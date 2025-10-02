import sys
from pathlib import Path
import json
import tempfile
import os
import pandas as pd
from datetime import datetime
import japanize_matplotlib
import random

# プロジェクトのルートディレクトリをPythonの検索パスに追加
# これにより、'src'フォルダをトップレベルとして認識できるようになる
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF

# --- ▼▼▼ インポートのパスをすべて src からに統一 ▼▼▼ ---
from src.config import VALUATION_PRICES
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.utils import normalize_text
from src.estimate_value import estimate_scrap_value
from src.db.database import SessionLocal

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            font_dir = os.path.dirname(japanize_matplotlib.__file__)
            font_path = os.path.join(font_dir, 'fonts', 'ipaexg.ttf')
            self.add_font('ipaexg', '', font_path, uni=True)
            self.add_font('ipaexg', 'B', font_path, uni=True)
            self.set_font('ipaexg', '', 12)
        except Exception as e:
            print(f"フォントの読み込みに失敗しました: {e}")
            self.set_font('Arial', '', 12)
    def header(self):
        self.set_font('ipaexg', 'B', 15)
        self.cell(0, 10, 'オークション仕入れ参考表', 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('ipaexg', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def generate_report_pdf(results: list) -> str:
    """算定結果のリストから「最終版」の表形式PDFレポートを生成する"""
    pdf = PDF(orientation='L')
    pdf.add_page()
    
    headers = [
        ("出品番号", 16), ("メーカー", 18), ("車名", 28), ("型式", 16),
        ("E/G型式", 16), ("総重量", 12), ("E/G部品販売", 16), 
        ("E/G価値", 14), ("プレス材", 14), ("甲山", 14), ("ハーネス", 14), 
        ("アルミ", 14), ("触媒", 12),("その他", 12),  ("輸送費等", 12), 
        ("損益分岐額", 18), ("過去相場(仮)", 18), ("入札対象", 10)
    ]
    
    # --- ヘッダー行を描画 ---
    pdf.set_font('ipaexg', 'B', 7)
    for header, width in headers:
        pdf.cell(width, 7, header, border=1, align='C')
    pdf.ln()

    # --- データ行を描画 ---
    pdf.set_fill_color(240, 240, 240)
    
    # ハイライトしたい列名をリストで定義
    highlight_columns = ["損益分岐額", "入札対象"]

    for i, res in enumerate(results):
        if not res or "error" in res: continue
        
        info = res.get('vehicle_info', {})
        breakdown = res.get('breakdown', {})
        
        row_data = [
            res.get('auction_no', ''), info.get('maker', ''), info.get('car_name', ''),
            info.get('model_code', ''), info.get('engine_model', ''), str(info.get('total_weight_kg', '')),
            breakdown.get('エンジン部品販売', '×'),
            f"{breakdown.get('エンジン/ミッション', 0):,.0f}",
            f"{breakdown.get('プレス材 (鉄)', 0):,.0f}", f"{breakdown.get('甲山 (ミックスメタル)', 0):,.0f}",
            f"{breakdown.get('ハーネス (銅)', 0):,.0f}", f"{breakdown.get('アルミホイール', 0):,.0f}",
            f"{breakdown.get('Catalyst', 0):,.0f}",  "0", # ← 「その他」の列に一旦0を入れる
            f"{breakdown.get('輸送費 (減算)', 0):,.0f}",
            f"{res.get('total_value', 0):,.0f}", f"{res.get('past_auction_price', 0):,.0f}",
            res.get('bidding_recommendation', '')
        ]
        
        should_fill = i % 2 == 0
        
        for col_idx, (data, width) in enumerate(zip(row_data, [w for h, w in headers])):
            
            is_highlight_col = headers[col_idx][0] in highlight_columns

            # ▼▼▼ 線の太さを変更するコードを削除し、フォント設定のみに変更 ▼▼▼
            if is_highlight_col:
                pdf.set_font('ipaexg', 'B', 7) # フォントを太字・少し大きく
            else:
                pdf.set_font('ipaexg', '', 6)  # 標準フォント

            pdf.cell(width, 6, str(data), border=1, fill=should_fill, align='C')
        
        # 1行描画が終わったら、次の行のためにフォントを標準に戻し、改行する
        pdf.set_font('ipaexg', '', 6)
        pdf.ln()
    
    output_path = os.path.join(tempfile.gettempdir(), f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(output_path)
    return output_path

@app.get("/api/parameters")
def get_parameters():
    """フロントエンドに渡す、価値算定の基本パラメータを返す"""
    # ▼▼▼ config.pyから返す値を、フロントエンドの表示項目と完全に一致させる ▼▼▼
    return {
        "engine_per_kg": VALUATION_PRICES.get("engine_per_kg", 0),
        "press_per_kg": VALUATION_PRICES.get("press_per_kg", 0),
        "kouzan_per_kg": VALUATION_PRICES.get("kouzan_per_kg", 0),
        "harness_per_kg": VALUATION_PRICES.get("harness_per_kg", 0),
        "aluminum_wheels_price": VALUATION_PRICES.get("aluminum_wheels_price", 0),
        "catalyst_price": VALUATION_PRICES.get("catalyst_price", 0),
        "transport_cost": 5000, # 輸送費は固定値として追加
    }

@app.post("/api/analyze-sheet")
async def analyze_sheet_endpoint(file: UploadFile = File(...), params_str: str = Form(...)):
    params = json.loads(params_str)
    temp_pdf_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(await file.read())
            temp_pdf_path = temp_pdf.name

        all_vehicles = extract_vehicles_from_pdf(temp_pdf_path)
        df = pd.DataFrame(all_vehicles)
        df = df[df['maker'] != 'メーカー'].copy()
        for col in ['maker', 'car_name', 'model_code']:
            if col in df.columns:
                df[col] = df[col].apply(normalize_text)
        
        results = []
        session = SessionLocal()
        try:
            print(f"PDFから {len(df)} 件の車両を検出。価値算定を開始します...")
            for index, row in df.iterrows():
                model_code = row.get('model_code')
                if not model_code: continue
                
                valuation = estimate_scrap_value(model_code, session, custom_prices=params)
                
                final_record = row.to_dict()
                final_record.update(valuation)
                if valuation and 'vehicle_info' in valuation:
                    final_record.update(valuation.get('vehicle_info', {}))


                # ▼▼▼ 新しいロジックを追加 ▼▼▼
                past_auction_price = random.randint(30000, 110000)
                final_record['past_auction_price'] = past_auction_price

                total_value = valuation.get('total_value', 0)
                diff = total_value - past_auction_price
                
                if diff >= 10000:
                    bidding_recommendation = "〇"
                elif diff > -10000:
                    bidding_recommendation = "△"
                else:
                    bidding_recommendation = "×"
                final_record['bidding_recommendation'] = bidding_recommendation
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                results.append(final_record)
        finally:
            session.close()

        # ▼▼▼ ここの行を修正 ▼▼▼
        # generate_report_pdfの戻り値（PDFのパス）を output_path 変数に格納する
        output_path = generate_report_pdf(results)
        
        return FileResponse(output_path, media_type='application/pdf', filename="valuation_report.pdf")
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)