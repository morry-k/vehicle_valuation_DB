import sys
from pathlib import Path
import json
import tempfile
import os
import pandas as pd
from datetime import datetime
import japanize_matplotlib

# --- パスを追加 ---
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF

# --- 既存のプロジェクトから機能をインポート ---
from src.config import VALUATION_PRICES
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.utils import normalize_text
from estimate_value import estimate_scrap_value
from src.db.database import SessionLocal

# ▼▼▼ このPDFクラスの __init__ メソッドを修正 ▼▼▼
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # 標準フォントのパスを取得
            font_dir = os.path.dirname(japanize_matplotlib.__file__)
            font_path = os.path.join(font_dir, 'fonts', 'ipaexg.ttf')
            self.add_font('ipaexg', '', font_path, uni=True)
            
            # 太字フォントのパスを取得して、'B'スタイルとして登録
            font_path_bold = os.path.join(font_dir, 'fonts', 'ipaexg.ttf') # 太字がないので標準で代用
            self.add_font('ipaexg', 'B', font_path_bold, uni=True)
            
            self.set_font('ipaexg', '', 12)
        except Exception as e:
            print(f"フォントの読み込みに失敗しました: {e}")
            self.set_font('Arial', '', 12)
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

app = FastAPI()

# --- CORS設定 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_report_pdf(results: list) -> str:
    """算定結果のリストから「表形式」のPDFレポートを生成する"""
    pdf = PDF(orientation='L') # カスタムクラスを使用
    pdf.add_page()
    
    # --- 表のヘッダーを定義 ---
    # (項目名, 横幅)
    headers = [
        ("メーカー", 20), ("車名", 35), ("型式", 25),
        ("エンジン価値", 25), ("プレス材", 20), ("甲山", 18),
        ("ハーネス", 18), ("アルミ", 18), ("触媒", 15),
        ("輸送費", 18), ("合計価値", 25)
    ]
    
    pdf.set_font('ipaexg', 'B', 8) # ヘッダーは太字
    for header, width in headers:
        pdf.cell(width, 8, header, border=1, align='C')
    pdf.ln()

    # --- 表のデータ行を書き込み ---
    pdf.set_font('ipaexg', '', 7) # データは標準フォント
    for res in results:
        if not res or "error" in res:
            continue
        
        info = res['vehicle_info']
        breakdown = res['breakdown']
        
        # 表示するデータを抽出・整形
        row_data = [
            info.get('maker', ''),
            info.get('car_name', ''),
            info.get('model_code', ''),
            f"{breakdown.get('エンジン/ミッション (部品推奨)', breakdown.get('エンジン (素材価値)', 0)):,.0f}",
            f"{breakdown.get('プレス材 (鉄)', 0):,.0f}",
            f"{breakdown.get('甲山 (ミックスメタル)', 0):,.0f}",
            f"{breakdown.get('ハーネス (銅)', 0):,.0f}",
            f"{breakdown.get('アルミホイール', 0):,.0f}",
            f"{breakdown.get('Catalyst', 0):,.0f}",
            f"{breakdown.get('輸送費 (減算)', 0):,.0f}",
            f"{res.get('total_value', 0):,.0f}"
        ]
        
        # 1行書き込み
        for data, width in zip(row_data, [w for h, w in headers]):
            pdf.cell(width, 6, data, border=1)
        pdf.ln()

    output_path = os.path.join(tempfile.gettempdir(), f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(output_path)
    return output_path

# ... (@app.get と @app.post は変更なし) ...
@app.get("/api/parameters")
def get_parameters():
    """フロントエンドに渡す、価値算定の基本パラメータを返す"""
    return {
        "press_per_kg": VALUATION_PRICES.get("press_per_kg", 0),
        "kouzan_per_kg": VALUATION_PRICES.get("kouzan_per_kg", 0),
        "transport_cost": 5000,
    }

@app.post("/api/analyze-sheet")
async def analyze_sheet_endpoint(
    file: UploadFile = File(...),
    params_str: str = Form(...)
):
    """出品票PDFとパラメータを受け取り、価値算定レポートPDFを返す"""
    params = json.loads(params_str)
    temp_pdf_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(await file.read())
            temp_pdf_path = temp_pdf.name

        all_vehicles = extract_vehicles_from_pdf(temp_pdf_path)
        df = pd.DataFrame(all_vehicles)
        df = df[df['maker'] != 'メーカー'].copy()
        if 'model_code' in df.columns:
            df['model_code'] = df['model_code'].apply(normalize_text)
        
        results = []
        session = SessionLocal()
        try:
            unique_model_codes = df['model_code'].dropna().unique()
            print(f"PDFから {len(unique_model_codes)} 件のユニークな車種を検出。価値算定を開始します...")
            for model_code in unique_model_codes:
                valuation = estimate_scrap_value(model_code, session, custom_prices=params)
                results.append(valuation)
        finally:
            session.close()

        output_pdf_path = generate_report_pdf(results)
        
        return FileResponse(output_pdf_path, media_type='application/pdf', filename="valuation_report.pdf")
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)