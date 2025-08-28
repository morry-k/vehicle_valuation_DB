# src/db/models.py

from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date, datetime

# 車種マスターリスト用のテーブルモデル
class VehicleMaster(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    maker: str = Field(index=True)
    car_name: str = Field(index=True)
    model_code: str = Field(index=True, unique=True) # 型式はユニークキー
    
    appearance_count: int = Field(default=0)
    year: Optional[str] = None
    grade: Optional[str] = None
    weight_kg: Optional[int] = None
    engine_model: Optional[str] = None
    catalyst_model: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SalesHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sale_date: date = Field(index=True)
    chassis_number: str = Field(unique=True, index=True)
    model_code: str = Field(index=True)
    car_name: str
    buyer_name: str
    buyer_location: Optional[str] = None # ▼▼▼ この行を追加 ▼▼▼
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)