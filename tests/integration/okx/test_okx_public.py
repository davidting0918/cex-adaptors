"""
OKX public-endpoint smoke tests. These hit the live API and are gated by
the RUN_INTEGRATION_TESTS env var so they do not run in the default CI job.

    RUN_INTEGRATION_TESTS=1 PYTHONPATH=. python3 -m unittest discover tests/integration
"""

import os
import unittest
from datetime import datetime as dt
from datetime import timedelta as td
from unittest import IsolatedAsyncioTestCase

from cex_adaptors.okx import Okx

INTEGRATION_ENABLED = os.getenv("RUN_INTEGRATION_TESTS") == "1"


@unittest.skipUnless(INTEGRATION_ENABLED, "Set RUN_INTEGRATION_TESTS=1 to run live OKX tests")
class TestOkxPublic(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.okx = Okx()
        self.spot_id = "BTC/USDT:USDT"
        self.perp_id = "BTC/USDT:USDT-PERP"
        self.inverse_perp_id = "BTC/USD:BTC-PERP"
        await self.okx.sync_exchange_info()

    async def asyncTearDown(self):
        await self.okx.close()

    async def test_exchange_info_contract(self):
        info = self.okx.exchange_info
        self.assertIn(self.spot_id, info)
        self.assertIn(self.perp_id, info)
        self.assertIn(self.inverse_perp_id, info)

    async def test_ticker_spot(self):
        result = await self.okx.get_ticker(self.spot_id)
        self.assertEqual(result["instrument_id"], self.spot_id)
        self.assertGreater(result["last"], 0)

    async def test_ticker_perp(self):
        result = await self.okx.get_ticker(self.perp_id)
        self.assertGreater(result["last"], 0)

    async def test_ticker_inverse_perp(self):
        result = await self.okx.get_ticker(self.inverse_perp_id)
        self.assertGreater(result["last"], 0)

    async def test_history_candlesticks_num(self):
        result = await self.okx.get_history_candlesticks(self.spot_id, "1d", num=30)
        self.assertEqual(len(result), 30)

    async def test_history_candlesticks_window(self):
        start = int((dt.now() - td(days=5)).timestamp() * 1000)
        end = int(dt.now().timestamp() * 1000)
        result = await self.okx.get_history_candlesticks(self.perp_id, "1d", start=start, end=end)
        self.assertTrue(result)
        for kline in result:
            self.assertGreaterEqual(kline["timestamp"], start)
            self.assertLessEqual(kline["timestamp"], end)

    async def test_current_funding_rate(self):
        result = await self.okx.get_current_funding_rate(self.perp_id)
        self.assertEqual(result["instrument_id"], self.perp_id)
        self.assertIsInstance(result["funding_rate"], float)

    async def test_history_funding_rate_num(self):
        result = await self.okx.get_history_funding_rate(self.perp_id, num=10)
        self.assertEqual(len(result), 10)

    async def test_orderbook_spot(self):
        result = await self.okx.get_orderbook(self.spot_id, depth=5)
        self.assertTrue(result["bids"])
        self.assertTrue(result["asks"])

    async def test_mark_price_perp(self):
        result = await self.okx.get_mark_price(self.perp_id)
        self.assertGreater(result["mark_price"], 0)

    async def test_index_price_perp(self):
        result = await self.okx.get_index_price(self.perp_id)
        self.assertGreater(result["index_price"], 0)

    async def test_open_interest_perp(self):
        result = await self.okx.get_open_interest(self.perp_id)
        self.assertGreater(result["oi_contract"], 0)

    async def test_last_price_spot(self):
        result = await self.okx.get_last_price(self.spot_id)
        self.assertGreater(result["last_price"], 0)


if __name__ == "__main__":
    unittest.main()
