import pdfplumber
from pathlib import Path

# --- 設定 ---
INPUT_DIR = Path(__file__).parent / "data" / "input" / "auction_sheets"
OUTPUT_LOG_PATH = Path(__file__).parent / "debug_word_analysis.txt" # 出力ログファイル

def analyze_pdf_structure():
    """PDF内の全単語の構造を分析し、テキストログに出力する"""
    print("PDFの内部構造の分析を開始します...")
    
    try:
        pdf_file = next(INPUT_DIR.glob("*.pdf"))
    except StopIteration:
        print(f"エラー: '{INPUT_DIR}' にPDFファイルが見つかりません。")
        return

    print(f"対象ファイル: {pdf_file.name}")

    with pdfplumber.open(pdf_file) as pdf, open(OUTPUT_LOG_PATH, "w", encoding="utf-8") as f:
        f.write(f"--- {pdf_file.name} の単語構造分析 ---\n\n")
        
        for page_num, page in enumerate(pdf.pages):
            f.write(f"\n--- ページ {page_num + 1} ---\n")
            
            words = page.extract_words(x_tolerance=2, y_tolerance=3)
            if not words: continue

            # y座標（top）で単語をソート
            sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))

            current_top = -1
            for word in sorted_words:
                # y座標が大きく変わったら、改行を入れて見やすくする
                if round(word['top']) > current_top + 5:
                    f.write("\n")
                    current_top = round(word['top'])
                
                # 単語の情報をファイルに書き込む
                f.write(f"'{word['text']}' (top:{word['top']:.1f}, x0:{word['x0']:.1f})  ")

    print(f"\n✅ 完了！ '{OUTPUT_LOG_PATH.name}' という名前で分析ログを出力しました。")

if __name__ == "__main__":
    analyze_pdf_structure()