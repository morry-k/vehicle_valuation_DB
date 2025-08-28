# src/pipeline.py

import pandas as pd
from pathlib import Path
# 変更後
from src import config
from src.data_processing.pdf_parser import extract_vehicles_from_pdf
from src.data_processing.scraper import enrich_vehicle_data

def run_phase1_extract_all_vehicles() -> pd.DataFrame:
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
    df = df[df['maker'] != 'メーカー'].copy()
    
    # drop_duplicates を削除し、全データをそのまま返す
    return df

# ▼▼▼ この関数が不足していました ▼▼▼
def run_phase2_enrich_data(master_df: pd.DataFrame) -> pd.DataFrame:
    """
    フェーズ2: 車種マスターリストのデータを拡充する
    """
    enriched_df = enrich_vehicle_data(master_df)
    return enriched_df

def run_phase3_calculate_value(all_vehicles_df: pd.DataFrame) -> pd.DataFrame:
    """
    フェーズ3: PDFから抽出した全車両データを集計し、既存DBを更新する
    """
    print("  - 既存データベースの読み込みと更新を開始します...")
    
    # --- 1. 既存DBを読み込む ---
    try:
        existing_db = pd.read_csv(config.VEHICLE_VALUE_LIST_PATH)
        print(f"  - 既存のデータベース（{len(existing_db)}件）を読み込みました。")
    except FileNotFoundError:
        required_cols = ['maker', 'car_name', 'model_code', 'appearance_count', 'year', 'grade']
        existing_db = pd.DataFrame(columns=required_cols)
        print("  - 既存のデータベースが見つからないため、新規に作成します。")

    # --- 2. 今回抽出した全車両リストから、出現回数を計算 ---
    key_cols = ['maker', 'car_name', 'model_code']
    if not all(col in all_vehicles_df.columns for col in key_cols):
        print(f"エラー: 必要なキー列 {key_cols} が抽出データにありません。")
        return existing_db # エラーの場合は既存DBをそのまま返す

    appearance_counts = all_vehicles_df.groupby(key_cols).size().reset_index(name='new_appearance_count')

    # --- 3. 今回抽出したユニークな車種情報と出現回数を結合 ---
    unique_new_vehicles = all_vehicles_df.drop_duplicates(subset=key_cols)
    merged_new_data = pd.merge(unique_new_vehicles, appearance_counts, on=key_cols)

    # --- 4. 既存DBと新しいデータをマージ ---
    final_db = pd.merge(existing_db, merged_new_data, on=key_cols, how='outer', suffixes=('_old', '_new'))

    # --- 5. 出現回数を更新し、列を整理 ---
    final_db['appearance_count'] = final_db['appearance_count'].fillna(0) + final_db['new_appearance_count'].fillna(0)
    final_db['appearance_count'] = final_db['appearance_count'].astype(int)
    
    # 新しいデータにしかなかった行のために、他の列の値を更新
    for col in ['year', 'grade', 'auction_no', 'mileage_km']: # PDFから取得する他の列
        if f'{col}_new' in final_db.columns and f'{col}_old' in final_db.columns:
            final_db[col] = final_db[f'{col}_new'].fillna(final_db[f'{col}_old'])

    # 最終的に必要な列だけを選択して整理
    final_columns = [col for col in required_cols if col in final_db.columns]
    final_db = final_db[final_columns]

    print("  - データベースの更新が完了しました。")
    return final_db