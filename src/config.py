# src/config.py

from pathlib import Path

# プロジェクトのルートディレクトリを取得
# このファイル (config.py) の親 (src) の親 (vehicle_value_pipeline)
ROOT_DIR = Path(__file__).parent.parent

# データディレクトリのパスを定義
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

# インプットファイルのパス
AUCTION_SHEETS_DIR = INPUT_DIR / "auction_sheets"
ENGINE_VALUE_PATH = INPUT_DIR / "engine_value.csv"
CATALYST_VALUE_PATH = INPUT_DIR / "catalyst_value.csv"

# アウトプットファイルのパス
VEHICLE_VALUE_LIST_PATH = OUTPUT_DIR / "vehicle_value_list.csv"