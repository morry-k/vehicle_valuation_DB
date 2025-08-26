# src/pipeline.py

import pandas as pd
from pathlib import Path
import config
# "src." をつけない相対インポート
from data_processing.pdf_parser import extract_vehicles_from_pdf
from data_processing.scraper import enrich_vehicle_data # ← この行も追加

def run_phase1_generate_master_list() -> pd.DataFrame:
    """
    フェーズ1: inputフォルダ内の全PDFを解析し、ユニークな車種マスターリストを作成する
    """
    all_vehicles = []
    
    pdf_files = list(config.AUCTION_SHEETS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        print("警告: data/input/auction_sheets/ ディレクトリにPDFファイルが見つかりません。")
        return pd.DataFrame()

    print(f"{len(pdf_files)}個のPDFファイルを処理します...")

    for pdf_path in pdf_files:
        print(f"  - 解析中: {pdf_path.name}")
        extracted_data = extract_vehicles_from_pdf(pdf_path)
        all_vehicles.extend(extracted_data)

    if not all_vehicles:
        print("警告: PDFから車両データを1件も抽出できませんでした。")
        return pd.DataFrame()

    df = pd.DataFrame(all_vehicles)
    
    # 'maker'列が'メーカー'という文字列である行を除外する
    df = df[df['maker'] != 'メーカー'].copy()

    key_columns = ["maker", "car_name", "grade", "year", "model_code"]
    master_df = df.drop_duplicates(subset=key_columns).copy()

    return master_df

# ▼▼▼ この関数が不足していました ▼▼▼
def run_phase2_enrich_data(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    フェーズ2: 車種マスターリストのデータを拡充する
    """
    enriched_df = enrich_vehicle_data(master_df)
    return enriched_df