# src/config.py

from pathlib import Path

# プロジェクトのルートディレクトリ
ROOT_DIR = Path(__file__).parent.parent

# データディレクトリ
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

# ★★★ この行を追加 ▼▼▼
# データベースファイルのパスを定義
DB_PATH = DATA_DIR / "vehicle_database.db"
# ★★★ ここまで追加 ▲▲▲

# インプットファイルのパス
AUCTION_SHEETS_DIR = INPUT_DIR / "auction_sheets"
ENGINE_VALUE_PATH = INPUT_DIR / "engine_value.csv"
CATALYST_VALUE_PATH = INPUT_DIR / "catalyst_value.csv"

# アウトプットファイルのパス
VEHICLE_VALUE_LIST_PATH = OUTPUT_DIR / "vehicle_value_list.csv"

# ▼▼▼ この単価マスターをファイル末尾に追加 ▼▼▼
# 価値算定のための単価・固定価格リスト (円)
VALUATION_PRICES = {
    # 1kgあたりの単価
    "engine_per_kg": 70, # ▼▼▼ この行を追加 ▼▼▼
    "press_per_kg": 25.5,
    "kouzan_per_kg": 35.0,
    
    # 部品ごとの固定価格
    "harness_price": 8000,
    "aluminum_wheels_price": 4800,
    "catalyst_price": 20000,
    "freon_price": 1500,
    "airbag_price": 1200
}