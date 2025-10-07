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
from src.db.models import TargetModel # ★ TargetModelをインポート

class PDF(FPDF):
    def __init__(self, header_info=None, *args, **kwargs): # ← ★ 1. header_info を受け取る
        super().__init__(*args, **kwargs)
        self.header_info = header_info or {} # ← ★ 2. 受け取った情報をselfに保存
        try:
            # フォント設定は変更なし
            font_dir = os.path.dirname(japanize_matplotlib.__file__)
            font_path = os.path.join(font_dir, 'fonts', 'ipaexg.ttf')
            self.add_font('ipaexg', '', font_path, uni=True)
            self.add_font('ipaexg', 'B', font_path, uni=True)
            self.set_font('ipaexg', '', 12)
        except Exception as e:
            print(f"フォントの読み込みに失敗しました: {e}")
            self.set_font('Arial', '', 12)

    def header(self):
        # --- 受け取ったヘッダー情報を使って動的なタイトルを生成 ---
        title = self.header_info.get("auction_venue", "車両価値算定レポート")
        date = self.header_info.get("auction_date", "")
        corner = self.header_info.get("auction_corner", "") # コーナー名を取得
        
        self.set_font('ipaexg', 'B', 15)
        self.cell(0, 10, title, 0, 1, 'C')

        # 日付とコーナー名をサブタイトルとして表示
        subtitle = f"({date}開催分 / {corner}コーナー)" if date and corner else f"({date}開催分)" if date else ""
        if subtitle:
            self.set_font('ipaexg', '', 10)
            self.cell(0, 7, subtitle, 0, 1, 'C')
        
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('ipaexg', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


app = FastAPI()
# --- ▼▼▼ このCORS設定ブロックを修正 ▼▼▼ ---
origins = [
    "http://localhost:3000", # ローカル開発環境用
    "https://vehicle-valuation-db.vercel.app", # Vercelの本番環境用
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_report_pdf(results: list, header_info: dict) -> str: # ← ★引数に header_info を追加
    """算定結果のリストから「最終版」の表形式PDFレポートを生成する"""
    pdf = PDF(header_info=header_info, orientation='L') # PDFクラスにヘッダー情報を渡す
    pdf.add_page()

    session = SessionLocal()
    try:
        target_models_query = session.query(TargetModel.model_code).all()
        target_model_set = {code for (code,) in target_models_query}
    finally:
        session.close()

    # ▼▼▼ headersリストの定義を修正 ▼▼▼
    # 「色」を削除し、「総重量」「シフト」「評価点」を追加
    headers = [
        ("出品番号", 18), ("メーカー", 18), ("車名", 30), ("グレード", 30), 
        ("年式", 10), ("型式", 22), ("排気量", 15), ("車検", 18), 
        ("走行", 12), ("シフト", 12), ("評価点", 12), ("総重量", 12),
        ("E/G販売", 12), ("E/G価値", 12), ("素材価値", 12), ("メモ", 28)
    ]
    
    pdf.set_font('ipaexg', 'B', 7)
    for header, width in headers:
        pdf.cell(width, 7, header, border=1, align='C')
    pdf.ln()

    pdf.set_fill_color(220, 220, 220)
    highlight_columns = ["損益分岐額", "入札対象"]

    for i, res in enumerate(results):
        if not res or "error" in res: continue
        
        info = res.get('vehicle_info', {})
        breakdown = res.get('breakdown', {})
        model_code = res.get('model_code', '')

        material_value = (
            breakdown.get('プレス材 (鉄)', 0) +
            breakdown.get('甲山 (ミックスメタル)', 0) +
            breakdown.get('ハーネス (銅)', 0)
        )
        
        is_target = model_code in target_model_set

        if is_target:
            pdf.set_text_color(0, 0, 0)
            should_fill = False
        else:
            pdf.set_text_color(150, 150, 150)
            should_fill = True
        
        # ▼▼▼ 2つの評価点を結合するロジックを追加 ▼▼▼
        score = res.get('evaluation_score', '')
        interior = res.get('evaluation_interior', '')
        evaluation_text = f"{score} / {interior}" if score and interior else score or interior
        
        # ▼▼▼ row_dataリストの定義を修正 ▼▼▼
        row_data = [
            res.get('auction_no', ''),
            res.get('maker', ''),
            res.get('car_name', ''),
            res.get('grade', ''),
            res.get('year', ''),
            res.get('model_code', ''),
            str(res.get('displacement_cc', '')),
            str(res.get('inspection_date', '')),
            str(res.get('mileage_km', '')),
            res.get('shift', ''),
            evaluation_text,
            str(res.get('total_weight_kg', '')),
            breakdown.get('エンジン部品販売', '×'),
            f"{breakdown.get('エンジン/ミッション', 0):,.0f}",
            f"{material_value:,.0f}",
            '' # メモ欄
        ]
        
        for col_idx, (data, width) in enumerate(zip(row_data, [w for h, w in headers])):
            pdf.cell(width, 6, str(data), border=1, fill=should_fill, align='C')
        
        pdf.ln()

    pdf.set_text_color(0, 0, 0)
    
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

        header_info, all_vehicles = extract_vehicles_from_pdf(temp_pdf_path)
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
                
                # まず、PDFの生データを final_record のベースとする
                final_record = row.to_dict()

                if model_code:
                    valuation = estimate_scrap_value(model_code, session, custom_prices=params)
                    
                    # 価値算定が成功した場合のみ、結果をマージする
                    if "error" not in valuation:
                        final_record.update(valuation)
                        if 'vehicle_info' in valuation:
                            final_record.update(valuation.get('vehicle_info', {}))
                
                # 過去相場と入札度のロジック
                past_auction_price = random.randint(30000, 110000)
                final_record['past_auction_price'] = past_auction_price
                
                total_value = final_record.get('total_value', 0)
                diff = total_value - past_auction_price
                
                if total_value == 0:
                    bidding_recommendation = "?"
                elif diff >= 10000:
                    bidding_recommendation = "〇"
                elif diff > -10000:
                    bidding_recommendation = "△"
                else:
                    bidding_recommendation = "×"
                final_record['bidding_recommendation'] = bidding_recommendation
                
                results.append(final_record)
        finally:
            session.close()

        output_pdf_path = generate_report_pdf(results, header_info)
        return FileResponse(output_pdf_path, media_type='application/pdf', filename="valuation_report.pdf")
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.unlink(temp_pdf_path)