from typing import Optional

from pydantic import BaseModel


class CurrentFundingRate(BaseModel):
    timestamp: int
    instrument_id: str
    market_type: str
    funding_rate: float
    next_funding_time: Optional[int]
    raw_data: Optional[dict]
