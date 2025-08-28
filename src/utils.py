# src/utils.py
import unicodedata

def normalize_text(text: str) -> str:
    """
    文字列を正規化する（半角化、大文字化、空白除去）
    """
    if not isinstance(text, str):
        return text
    # NFKC正規化により、全角英数字・記号などを半角に変換
    normalized_text = unicodedata.normalize('NFKC', text)
    return normalized_text.upper().strip()