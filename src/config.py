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