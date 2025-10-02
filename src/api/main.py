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

def generate_report_pdf(results: list) -> str:
    """算定結果のリストから「最終版」の表形式PDFレポートを生成する"""
    pdf = PDF(orientation='L')
    pdf.add_page()
    
    # --- 1. DBから注目車種リストを取得 ---
    session = SessionLocal()
    try:
        target_models_query = session.query(TargetModel.model_code).all()
        target_model_set = {code for (code,) in target_models_query}
    finally:
        session.close()

    headers = [
        ("出品番号", 18), ("メーカー", 18), ("車名", 30), ("グレード", 30), 
        ("年式", 10), ("型式", 22), ("排気量", 15), ("車検", 18), 
        ("走行", 15), ("色", 12), ("総重量", 15), # ← 追加
        ("E/G販売", 18), ("E/G価値", 18), ("素材価値", 18), ("メモ", 28)
    ]

    pdf.set_font('ipaexg', 'B', 7)
    for header, width in headers:
        pdf.cell(width, 7, header, border=1, align='C')
    pdf.ln()

    # --- データ行を描画 ---
    pdf.set_fill_color(220, 220, 220) # グレーアウト用の色
    highlight_columns = ["損益分岐額", "入札対象"]

    for i, res in enumerate(results):
        if not res or "error" in res: continue
        
        info = res.get('vehicle_info', {})
        breakdown = res.get('breakdown', {})
        model_code = info.get('model_code', '')

        # 素材価値の合計を計算
        material_value = (
            breakdown.get('プレス材 (鉄)', 0) +
            breakdown.get('甲山 (ミックスメタル)', 0) +
            breakdown.get('ハーネス (銅)', 0)
        )
        
        # --- 2. 現在の行が注目車種かどうかを判定 ---
        is_target = model_code in target_model_set

        # --- 3. 判定結果に応じてスタイルを設定 ---
        if is_target:
            pdf.set_text_color(0, 0, 0)
            should_fill = False
        else:
            pdf.set_text_color(150, 150, 150)
            should_fill = True
        
        row_data = [
            res.get('auction_no', ''),
            info.get('maker', ''),
            info.get('car_name', ''),
            res.get('grade', ''),
            info.get('year', ''),
            info.get('model_code', ''),
            str(res.get('displacement_cc', '')),
            str(res.get('inspection_date', '')),
            str(res.get('mileage_km', '')),
            res.get('color', ''),
            str(info.get('total_weight_kg', '')),
            breakdown.get('エンジン部品販売', '×'),
            f"{breakdown.get('エンジン/ミッション', 0):,.0f}",
            f"{material_value:,.0f}",
            '' # メモ欄のデータを空にする
        ]
        
        
        for col_idx, (data, width) in enumerate(zip(row_data, [w for h, w in headers])):
            is_highlight_col = headers[col_idx][0] in highlight_columns

            if is_highlight_col and is_target: # 注目車種の、ハイライト列のみ太字にする
                pdf.set_font('ipaexg', 'B', 7)
            else:
                pdf.set_font('ipaexg', '', 6)

            pdf.cell(width, 6, str(data), border=1, fill=should_fill, align='C')
        
        pdf.ln()

    # レポート全体のスタイルをリセット
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