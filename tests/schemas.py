from typing import Optional

from pydantic import BaseModel, model_validator


class CurrentFundingRate(BaseModel):
    timestamp: int
    instrument_id: str
    market_type: str
    funding_rate: float
    next_funding_time: Optional[int]
    raw_data: Optional[dict]


class HistoryFundingRate(BaseModel):
    timestamp: int
    instrument_id: str
    market_type: str
    funding_rate: float
    realized_rate: Optional[float]
    raw_data: Optional[dict]


class Kline(BaseModel):
    timestamp: int
    instrument_id: str
    market_type: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    base_volume: float
    quote_volume: float
    contract_volume: float
    raw_data: Optional[dict | list]

    @model_validator(mode="after")
    def validate_ohlc(self, values):
        if (
            self.high < self.low
            or self.high < self.open
            or self.high < self.close
            or self.low > self.open
            or self.low > self.close
        ):
            raise ValueError(f"OHLC values are invalid. {self.open}, {self.high}, {self.low}, {self.close}")
        return self


class ExchangeInfo(BaseModel):
    active: bool
    base: str
    quote: str
    settle: str
    symbol: str
    contract_size: int | float
    expiration_time: Optional[int]
    is_futures: bool
    is_margin: bool
    is_perp: bool
    is_spot: bool
    is_linear: bool
    is_inverse: bool
    leverage: int
    listing_time: int
    max_order_size: float
    min_order_size: float
    multiplier: int
    tick_size: float
    raw_data: Optional[dict | list]

    @model_validator(mode="after")
    def validate_type(self):
        return self


class Ticker(BaseModel):
    timestamp: int
    instrument_id: str
    market_type: str
    open_time: int
    close_time: int
    open: float
    high: float
    low: float
    last: float
    base_volume: float
    quote_volume: float
    price_change: float
    price_change_percent: float
    raw_data: Optional[dict | list]

    @model_validator(mode="after")
    def validate_volume(self):

        implied_price = self.quote_volume / self.base_volume
        dif_ratio = 0.05  # 5%

        if abs(implied_price - self.last) / self.last > dif_ratio:
            raise ValueError(f"Implied price is too far from last price. {implied_price}, {self.last}")

        return self
