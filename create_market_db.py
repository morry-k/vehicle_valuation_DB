from src.db.database import market_engine
from src.db.models import SQLModel, AuctionMarketData
from src import config

def create_market_database():
    """
    市場データ用の新しいデータベース(market_data.db)を作成し、
    AuctionMarketDataテーブルを初期化する
    """
    print(f"新しいデータベースを作成します: {config.MARKET_DB_PATH}")
    
    # market_engineを使って、AuctionMarketDataの定義通りにテーブルを作成
    SQLModel.metadata.create_all(market_engine)
    
    print("✅ データベースの作成が完了しました。")

if __name__ == "__main__":
    create_market_database()