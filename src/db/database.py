# src/db/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src import config

# SQLiteデータベースへの接続エンジンを作成
engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False} # SQLiteを使う場合のおまじない
)

# データベースと対話するための「セッション」を作成するクラス
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)