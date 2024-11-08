from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class Device(BaseModel):
    id: str
    type: str  # franklin, sierra, huawei, android, voip
    phone_number: str
    sim_iccid: Optional[str]
    signal_strength: Optional[int]
    status: str  # online, offline, error
    first_seen: datetime
    last_seen: datetime

class SMS(BaseModel):
    id: int
    device_id: str
    from_number: str
    to_number: str
    text: str
    received_at: datetime
    delivered: bool 