from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Ambulance(SQLModel, table=True):
    id: str = Field(primary_key=True)
    call_sign: Optional[str] = None
    lat: float = 0.0
    lon: float = 0.0
    status: Optional[str] = 'available'
    last_update: Optional[datetime] = None

class Emergency(SQLModel, table=True):
    id: str = Field(primary_key=True)
    type: Optional[str] = None
    lat: float = 0.0
    lon: float = 0.0
    severity: Optional[int] = 1
    status: Optional[str] = 'reported'
    assigned_ambulance_id: Optional[str] = None
    created_at: Optional[datetime] = None
