import sys
from pathlib import Path
import json
import tempfile
import os
import pandas as pd
from datetime import datetime
import japanize_matplotlib
import random
import traceback
import re 

# プロジェクトのルートディレクトリをPythonの検索パスに追加
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fpdf import FPDF

# --- インポートのパスをすべて src からに統一 ---
from src.config import VALUATION_PRICES
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.utils import normalize_text
from src.estimate_value import estimate_scrap_value
from src.db.database import SessionLocal, get_market_session # ★市場DBセッション用
from src.db.models import TargetModel
from src.market_analysis import analyze_market_trends # ★相場分析ロジック

class PDF(FPDF):
    def __init__(self, header_info=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header_info = header_info or {}
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
        title = self.header_info.get("auction_venue", "車両価値算定レポート")
        date = self.header_info.get("auction_date", "")
        corner = self.header_info.get("auction_corner", "")
        
        self.set_font('ipaexg', 'B', 15)
        self.cell(0, 10, title, 0, 1, 'C')

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
origins = [
    "http://localhost:3000",
    "https://vehicle-valuation-db.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_report_pdf(results: list, header_info: dict) -> str:
    """算定結果のリストから「最終版」の表形式PDFレポートを生成する"""
    pdf = PDF(header_info=header_info, orientation='L')
    pdf.add_page()

    session = SessionLocal()
    try:
        target_models_query = session.query(TargetModel.model_code).all()
        target_model_set = {code for (code,) in target_models_query}
    finally:
        session.close()

    # headersリスト
    headers = [
        ("出品番号", 18), ("メーカー", 18), ("車名", 37), ("グレード", 45), 
        ("年式", 10), ("型式", 25), ("排気量", 15), ("車検", 23), 
        ("走行", 12), ("シフト", 12), ("評価点", 12), ("総重量", 12),
        ("E/G販売", 12), ("E/G価値", 12), ("素材価値", 12),("過去相場", 18)
    ]
    
    pdf.set_draw_color(160, 160, 160)

    pdf.set_font('ipaexg', 'B', 7)
    for header, width in headers:
        pdf.cell(width, 7, header, border=1, align='L')
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
        
        is_target = res.get('is_target', False)

        if is_target:
            pdf.set_text_color(0, 0, 0)
            should_fill = False
        else:
            pdf.set_text_color(100, 100, 100)
            should_fill = True
        
        score = res.get('evaluation_score', '')
        interior = res.get('evaluation_interior', '')
        evaluation_text = f"{score} / {interior}" if score and interior else score or interior
        
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
            f"{res.get('past_auction_price', 0):,.0f}", # ★過去相場
            '' # メモ欄
        ]
        
        for col_idx, (data, width) in enumerate(zip(row_data, [w for h, w in headers])):
            pdf.cell(width, 6, str(data), border=1, fill=should_fill, align='L')
        
        pdf.ln()

    pdf.set_text_color(0, 0, 0)
    
    output_path = os.path.join(tempfile.gettempdir(), f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
    pdf.output(output_path)
    return output_path


@app.get("/api/parameters")
def get_parameters():
    """フロントエンドに渡す、価値算定の基本パラメータを返す"""
    return {
        "engine_per_kg": VALUATION_PRICES.get("engine_per_kg", 0),
        "press_per_kg": VALUATION_PRICES.get("press_per_kg", 0),
        "kouzan_per_kg": VALUATION_PRICES.get("kouzan_per_kg", 0),
        "harness_per_kg": VALUATION_PRICES.get("harness_per_kg", 0),
        "aluminum_wheels_price": VALUATION_PRICES.get("aluminum_wheels_price", 0),
        "catalyst_price": VALUATION_PRICES.get("catalyst_price", 0),
        "transport_cost": 5000,
    }

@app.post("/api/analyze-sheet")
async def analyze_sheet_endpoint(file: UploadFile = File(...), params_str: str = Form(...)):
    try:
        params = json.loads(params_str)
        temp_pdf_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(await file.read())
                temp_pdf_path = temp_pdf.name

            header_info, all_vehicles = extract_vehicles_from_pdf(temp_pdf_path)
            df = pd.DataFrame(all_vehicles)
            df = df[df['maker'] != 'メーカー'].copy()
            
            results = []
            session = SessionLocal()
            market_session = get_market_session() # ★市場データDBセッション作成
            try:
                target_models_query = session.query(TargetModel.model_code).all()
                target_model_set = {code for (code,) in target_models_query}
                
                print(f"PDFから {len(df)} 件の車両を検出。価値算定を開始します...")
                for index, row in df.iterrows():
                    
                    pdf_row_data = row.to_dict()
                    original_model_code = pdf_row_data.get('model_code')

                    lookup_model_code = None
                    if original_model_code:
                        temp_code = original_model_code.replace("カイ", "").replace("ｶｲ", "").strip()
                        lookup_model_code = normalize_text(temp_code)
                    
                    valuation = {}
                    if lookup_model_code:
                        valuation = estimate_scrap_value(lookup_model_code, session, custom_prices=params)
                    else:
                        valuation = {"error": "型式不明"}
                    
                    db_info = valuation.get('vehicle_info', {})
                    calculated_values = valuation.copy()
                    calculated_values.pop('vehicle_info', None) 
                    
                    # データを正しい順序でマージ
                    final_record = pdf_row_data.copy()
                    final_record.update(db_info)
                    final_record.update(pdf_row_data)
                    final_record.update(calculated_values)

                    # ▼▼▼ 相場分析に必要な情報を抽出して変換 ▼▼▼
                    target_year_str = final_record.get('year', '0')
                    target_mileage_str = final_record.get('mileage_km', '0')
                    target_score_str = final_record.get('evaluation_score', '0') # 評価点

                    try:
                        # 年式: "H27" -> 2015 などの変換が必要だが、簡易的に数字のみ抽出
                        target_year = int(re.sub(r"[^\d]", "", target_year_str))
                        if target_year < 100 and target_year != 0:
                            target_year += 2000 # 暫定補正 (本来は和暦変換が必要)
                    except:
                        target_year = 0
                    
                    try:
                        target_mileage = int(re.sub(r"[^\d]", "", target_mileage_str))
                    except:
                        target_mileage = 0

                    # ▼▼▼ 市場相場の分析実行 ▼▼▼
                    market_info = {"market_price": 0, "trend_icon": "→", "sample_count": 0}
                    if lookup_model_code and target_year > 0:
                        market_info = analyze_market_trends(
                            lookup_model_code, 
                            target_year, 
                            target_mileage, 
                            target_score_str, # 評価点も渡す
                            market_session    # 市場DBセッション
                        )
                    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

                    final_record['past_auction_price'] = market_info["market_price"]
                    final_record['market_trend'] = market_info["trend_icon"] 

                    # 注目車種判定
                    is_target = (original_model_code in target_model_set) or \
                                (lookup_model_code in target_model_set)
                    final_record['is_target'] = is_target

                    # 入札度ロジック
                    total_value = final_record.get('total_value', 0)
                    market_price = final_record.get('past_auction_price', 0)

                    if total_value == 0 or market_price == 0:
                        bidding_recommendation = "?"
                    else:
                        diff = total_value - market_price
                        if diff >= 10000:
                            bidding_recommendation = "〇"
                        elif diff > -10000:
                            bidding_recommendation = "△"
                        else:
                            bidding_recommendation = "×"
                    final_record['bidding_recommendation'] = bidding_recommendation
                    
                    results.append(final_record)
            finally:
                session.close()
                market_session.close() # ★忘れずにクローズ

            output_pdf_path = generate_report_pdf(results, header_info)
            return FileResponse(output_pdf_path, media_type='application/pdf', filename="valuation_report.pdf")
        
        finally:
            if temp_pdf_path and os.path.exists(temp_pdf_path):
                os.unlink(temp_pdf_path)
    
    except Exception as e:
        print("\n" + "="*50)
        print("バックエンドで予期せぬエラーが発生しました。")
        traceback.print_exc()
        print("="*50 + "\n")
        return {"error": "Internal Server Error"}, 500