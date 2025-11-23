from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src import config

# --- 1. メインデータベース (vehicle_database.db) ---
# 役割: 車種辞書、部品価格、自社の仕入れ実績など
engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False}
)

# 既存のコードとの互換性のため、名前は SessionLocal のままにする
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- 2. 市場データ用データベース (market_data.db) ---
# 役割: スクレイピングで収集した大量の相場データ
market_engine = create_engine(
    f"sqlite:///{config.MARKET_DB_PATH}",
    connect_args={"check_same_thread": False}
)

# 市場データ専用のセッション作成クラス
MarketSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=market_engine)


# --- ヘルパー関数 ---

def get_session() -> Session:
    """メインDBのセッションを取得する"""
    return SessionLocal()

def get_market_session() -> Session:
    """市場データDBのセッションを取得する"""
    return MarketSessionLocal()