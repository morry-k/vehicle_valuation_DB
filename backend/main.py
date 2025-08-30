import sys
from pathlib import Path
import json
import tempfile
import os
import pandas as pd
from datetime import datetime
import japanize_matplotlib

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF

from src.config import VALUATION_PRICES
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.utils import normalize_text
from estimate_value import estimate_scrap_value
from src.db.database import SessionLocal

class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # 標準フォントと太字フォントのみを登録
            font_dir = os.path.dirname(japanize_matplotlib.__file__)
            font_path = os.path.join(font_dir, 'fonts', 'ipaexg.ttf')
            self.add_font('ipaexg', '', font_path, uni=True)
            self.add_font('ipaexg', 'B', font_path, uni=True)
            # self.add_font('ipaexg', 'I', font_path, uni=True) # ← イタリックの登録を削除
            self.set_font('ipaexg', '', 12)
        except Exception as e:
            print(f"フォントの読み込みに失敗しました: {e}")
            self.set_font('Arial', '', 12)

    def header(self):
        self.set_font('ipaexg', 'B', 15)
        self.cell(0, 10, '車両価値算定レポート', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        # イタリック('I')ではなく、標準フォント('')を使用するように変更
        self.set_font('ipaexg', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def generate_report_pdf(results: list) -> str:
    """算定結果のリストから「最終版」の表形式PDFレポートを生成する"""
    pdf = PDF(orientation='L') # 用紙を横向きに設定
    pdf.add_page()
    
    # --- ▼▼▼ 表示したい列に合わせてヘッダーを定義 ▼▼▼ ---
    headers = [
        ("出品番号", 20), ("メーカー", 20), ("車名", 35), ("型式", 25),
        ("E/G型式", 20), ("総重量", 15),
        ("E/G価値", 20), ("プレス材", 20), ("甲山", 20),
        ("ハーネス", 20), ("アルミ", 18), ("触媒", 15),
        ("輸送費", 15), ("合計価値", 22)
    ]
    
    pdf.set_font('ipaexg', 'B', 7)
    for header, width in headers:
        pdf.cell(width, 7, header, border=1, align='C')
    pdf.ln()

    # --- ▼▼▼ 表示したいデータを正しく抽出して行を作成 ▼▼▼ ---
    pdf.set_font('ipaexg', '', 6)
    for res in results:
        if not res or "error" in res: continue
        
        # res辞書には、PDFの生データとDBからの補足情報がすべてマージされている
        breakdown = res.get('breakdown', {})
        
        # データを抽出（getの第二引数で、値がない場合は空文字''にする）
        row_data = [
            res.get('auction_no', ''),
            res.get('maker', ''),
            res.get('car_name', ''),
            res.get('model_code', ''),
            res.get('engine_model', ''),
            str(res.get('total_weight_kg', '')), # 数値の可能性があるのでstrに変換
            f"{breakdown.get('エンジン/ミッション (部品推奨)', breakdown.get('エンジン (素材価値)', 0)):,.0f}",
            f"{breakdown.get('プレス材 (鉄)', 0):,.0f}",
            f"{breakdown.get('甲山 (ミックスメタル)', 0):,.0f}",
            f"{breakdown.get('ハーネス (銅)', 0):,.0f}",
            f"{breakdown.get('アルミホイール', 0):,.0f}",
            f"{breakdown.get('Catalyst', 0):,.0f}",
            f"{breakdown.get('輸送費 (減算)', 0):,.0f}",
            f"{res.get('total_value', 0):,.0f}"
        ]
        
        for data, width in zip(row_data, [w for h, w in headers]):
            pdf.cell(width, 6, str(data), border=1)
        pdf.ln()

    output_path = os.path.join(tempfile.gettempdir(), f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(output_path)
    return output_path

@app.get("/api/parameters")
def get_parameters():
    return {"press_per_kg": VALUATION_PRICES.get("press_per_kg", 0), "kouzan_per_kg": VALUATION_PRICES.get("kouzan_per_kg", 0), "transport_cost": 5000}

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
                results.append(final_record)
        finally:
            session.close()

        # ▼▼▼ ここからがデバッグ表示 ▼▼▼
        print("\n" + "="*50)
        print("デバッグ情報：PDF生成に渡されるデータ（最初の1件）")
        if results:
            import pprint
            pprint.pprint(results[0])
        print("="*50 + "\n")
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        output_pdf_path = generate_report_pdf(results)
        return FileResponse(output_pdf_path, media_type='application/pdf', filename="valuation_report.pdf")
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)