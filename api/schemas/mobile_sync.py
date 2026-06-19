# api/schemas/mobile_sync.py

from pydantic import BaseModel
from typing import List


class MobileSignal(BaseModel):

    source: str

    sender: str

    message: str

    timestamp: int


class SyncRequest(BaseModel):

    device_id: str

    signals: List[MobileSignal]