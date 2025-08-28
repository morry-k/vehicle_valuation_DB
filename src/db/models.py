# src/db/models.py

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date, datetime

class VehicleMaster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    maker: Optional[str] = Field(default=None, index=True)
    car_name: Optional[str] = Field(default=None, index=True)
    model_code: str = Field(index=True, unique=True)
    
    appearance_count: int = Field(default=0)
    year: Optional[str] = None
    grade: Optional[str] = None
    
    # --- AIによる拡充データ ---
    engine_model: Optional[str] = Field(default=None, index=True)
    drive_type: Optional[str] = Field(default=None, index=True)
    body_type: Optional[str] = Field(default=None, index=True)
    total_weight_kg: Optional[int] = None
    engine_weight_kg: Optional[int] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ▼▼▼ このモデル定義をファイル末尾に追加 ▼▼▼
class ComponentValue(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_name: str = Field(index=True)      # 品名 (例: "エンジン/ミッション")
    engine_model: Optional[str] = Field(default=None, index=True) # E/G型式
    
    # 「詳細」をタグ化したもの (例: "no_catalyst,with_suspension")
    details_tags: str = Field(index=True, default="standard") 
    
    latest_price: float # 最新の取引単価
    average_price: float # 平均取引単価
    sample_size: int    # 価格計算の基になった取引件数
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SalesHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sale_date: date = Field(index=True)
    chassis_number: str = Field(unique=True, index=True)
    model_code: str = Field(index=True)
    maker: str = Field(index=True)
    car_name: Optional[str] = None
    buyer_name: str
    buyer_location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

