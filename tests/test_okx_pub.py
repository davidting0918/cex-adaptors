import tracemalloc
import unittest
from datetime import datetime as dt
from datetime import timedelta as td
from unittest import IsolatedAsyncioTestCase

from cex_adaptors.okx import Okx
from tests.schemas import CurrentFundingRate
from tests.utils import validate_dict_response

tracemalloc.start()


class TestOkx(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.okx = Okx()
        self.spot_instrument_id = "BTC/USDT:USDT"
        self.perp_instrument_id = "BTC/USDT:USDT-PERP"
        await self.okx.sync_exchange_info()

    async def asyncTearDown(self):
        await self.okx.close()

    async def test_get_exchange_info(self):
        response = await self.okx.get_exchange_info()
        self.assertTrue(response)
        return

    async def test_get_tickers(self):
        spot = await self.okx.get_tickers("spot")
        self.assertTrue(spot)

        futures = await self.okx.get_tickers("futures")
        self.assertTrue(futures)

        perp = await self.okx.get_tickers("perp")
        self.assertTrue(perp)

        tickers = await self.okx.get_tickers()
        self.assertTrue(tickers)
        return

    async def test_get_ticker(self):
        spot = await self.okx.get_ticker(self.spot_instrument_id)
        self.assertTrue(spot)

        perp = await self.okx.get_ticker(self.perp_instrument_id)
        self.assertTrue(perp)

        return

    async def test_get_klines(self):
        spot = await self.okx.get_history_candlesticks(self.spot_instrument_id, "1d", num=120)
        self.assertEqual(len(spot), 120)

        perp = await self.okx.get_history_candlesticks(self.perp_instrument_id, "1d", num=77)
        self.assertEqual(len(perp), 77)

        return

    async def test_get_klines_with_timestamp(self):
        start = int((dt.today() - td(days=30)).timestamp() * 1000)
        end = int(dt.today().timestamp() * 1000)

        spot = await self.okx.get_history_candlesticks(self.spot_instrument_id, "1d", start=start, end=end)
        self.assertEqual(len(spot), 30)

        perp = await self.okx.get_history_candlesticks(self.perp_instrument_id, "1d", start=start, end=end)
        self.assertEqual(len(perp), 30)

        return

    async def test_get_current_funding_rate(self):
        funding_rate = await self.okx.get_current_funding_rate(self.perp_instrument_id)
        self.assertTrue(funding_rate)

        self.assertTrue(validate_dict_response(funding_rate, CurrentFundingRate))
        return

    async def test_get_history_funding_rate(self):
        history_funding_rate = await self.okx.get_history_funding_rate(self.perp_instrument_id, num=30)
        self.assertEqual(len(history_funding_rate), 30)

        start = int((dt.today() - td(days=2)).timestamp() * 1000)
        end = int(dt.today().timestamp() * 1000)
        history_funding_rate = await self.okx.get_history_funding_rate(self.perp_instrument_id, start=start, end=end)
        self.assertEqual(len(history_funding_rate), 6)
        return


if __name__ == "__main__":
    unittest.main()
