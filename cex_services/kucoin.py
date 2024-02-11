import asyncio

from .exchanges.kucoin import KucoinFutures, KucoinSpot
from .parsers.kucoin import KucoinParser
from .utils import query_dict


class Kucoin(object):
    name = "kucoin"

    def __init__(self):
        self.spot = KucoinSpot()
        self.futures = KucoinFutures()
        self.parser = KucoinParser()

        self.exchange_info = {}

    @classmethod
    async def create(cls):
        instance = cls()
        instance.exchange_info = await instance.get_exchange_info()
        return instance

    async def close(self):
        await self.spot.close()
        await self.futures.close()

    async def get_exchange_info(self) -> dict:
        spot = self.parser.parse_exchange_info(
            await self.spot._get_symbol_list(), self.parser.spot_exchange_info_parser
        )
        futures = self.parser.parse_exchange_info(
            await self.futures._get_symbol_list(), self.parser.futures_exchange_info_parser
        )

        return {**spot, **futures}

    async def get_tickers(self, market_type: str = None) -> dict:
        if market_type == "spot":
            return self.parser.parse_spot_tickers(await self.spot._get_tickers(), self.exchange_info)
        elif market_type == "futures":
            ids = list(query_dict(self.exchange_info, "is_futures == True or is_perp == True").keys())
            num_batch = 20
            results = {}
            for i in range(0, len(ids), num_batch):
                tasks = []
                for instrument_id in ids[i : i + num_batch]:
                    _symbol = self.exchange_info[instrument_id]["raw_data"]["symbol"]
                    tasks.append(self.futures._get_ticker(_symbol))
                raw_tickers = await asyncio.gather(*tasks)
                parsed_tickers = self.parser.parse_derivative_tickers(raw_tickers, self.exchange_info)
                results.update(parsed_tickers)
            return results
        else:
            pass

    async def get_klines(
        self, instrument_id: str, interval: str, start: int = None, end: int = None, limit: int = None
    ):
        pass
