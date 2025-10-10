import sys
from pathlib import Path
import pandas as pd

# プロジェクトのsrcフォルダをPythonの検索パスに追加
sys.path.append(str(Path(__file__).resolve().parent / "src"))

from config import AUCTION_SHEETS_DIR
from data_processing.pdf_parser import extract_vehicles_from_pdf
from utils import normalize_text

def list_unique_models():
    """
    inputフォルダ内の全PDFを解析し、ユニークな型式のリストを出力する
    """
    print("PDF内の全車種の型式リストを作成します...")
    
    all_model_codes = set() # 重複を自動で省くためにセットを使用

    pdf_files = list(AUCTION_SHEETS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"エラー: '{AUCTION_SHEETS_DIR}' にPDFファイルが見つかりません。")
        return

    print(f"{len(pdf_files)}個のPDFファイルを処理します...")

    # 既存のPDF解析機能を再利用
    for pdf_path in pdf_files:
        print(f"  - 解析中: {pdf_path.name}")
        # パーサーからはヘッダー情報と車両リストが返ってくる
        header_info, vehicles = extract_vehicles_from_pdf(pdf_path)
        
        for vehicle in vehicles:
            model_code = vehicle.get("model_code")
            if model_code:
                # 正規化してセットに追加
                all_model_codes.add(normalize_text(model_code))

    if not all_model_codes:
        print("型式を一つも抽出できませんでした。")
        return

    # --- 結果を出力 ---
    print("\n" + "="*50)
    print(f"検出されたユニークな型式の総数: {len(all_model_codes)} 件")
    print("="*50)
    
    # アルファベット順にソートして表示
    for model_code in sorted(list(all_model_codes)):
        print(model_code)

if __name__ == "__main__":
    list_unique_models()