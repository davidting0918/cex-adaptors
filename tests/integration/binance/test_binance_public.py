"""
Binance public-endpoint smoke tests. These hit the live API and are gated by
the RUN_INTEGRATION_TESTS env var so they do not run in the default CI job.

    RUN_INTEGRATION_TESTS=1 PYTHONPATH=. python3 -m unittest discover tests/integration
"""

import os
import unittest
from datetime import datetime as dt
from datetime import timedelta as td
from unittest import IsolatedAsyncioTestCase

from cex_adaptors.binance import Binance

INTEGRATION_ENABLED = os.getenv("RUN_INTEGRATION_TESTS") == "1"


@unittest.skipUnless(INTEGRATION_ENABLED, "Set RUN_INTEGRATION_TESTS=1 to run live Binance tests")
class TestBinancePublic(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.binance = Binance()
        self.spot_id = "BTC/USDT:USDT"
        self.linear_id = "BTC/USDT:USDT-PERP"
        self.inverse_id = "BTC/USD:BTC-PERP"
        await self.binance.sync_exchange_info()

    async def asyncTearDown(self):
        await self.binance.close()

    async def test_exchange_info_contract(self):
        info = self.binance.exchange_info
        self.assertIn(self.spot_id, info)
        self.assertIn(self.linear_id, info)
        self.assertIn(self.inverse_id, info)

    async def test_ticker_spot(self):
        result = await self.binance.get_ticker(self.spot_id)
        self.assertIn(self.spot_id, result)
        self.assertGreater(result[self.spot_id]["last"], 0)

    async def test_ticker_linear(self):
        result = await self.binance.get_ticker(self.linear_id)
        self.assertGreater(result[self.linear_id]["last"], 0)

    async def test_ticker_inverse(self):
        result = await self.binance.get_ticker(self.inverse_id)
        self.assertGreater(result[self.inverse_id]["last"], 0)

    async def test_history_candlesticks_num(self):
        result = await self.binance.get_history_candlesticks(self.spot_id, "1d", num=30)
        self.assertEqual(len(result), 30)

    async def test_history_candlesticks_window(self):
        start = int((dt.now() - td(days=5)).timestamp() * 1000)
        end = int(dt.now().timestamp() * 1000)
        result = await self.binance.get_history_candlesticks(self.linear_id, "1d", start=start, end=end)
        self.assertTrue(result)
        for kline in result:
            self.assertGreaterEqual(kline["timestamp"], start)
            self.assertLessEqual(kline["timestamp"], end)

    async def test_current_funding_rate(self):
        result = await self.binance.get_current_funding_rate(self.linear_id)
        self.assertIn(self.linear_id, result)
        self.assertIsInstance(result[self.linear_id]["funding_rate"], float)

    async def test_history_funding_rate_num(self):
        result = await self.binance.get_history_funding_rate(self.linear_id, num=10)
        self.assertEqual(len(result), 10)

    async def test_orderbook_spot(self):
        result = await self.binance.get_orderbook(self.spot_id, depth=5)
        self.assertEqual(len(result["bids"]), 5)
        self.assertEqual(len(result["asks"]), 5)

    async def test_open_interest_linear(self):
        result = await self.binance.get_open_interest(self.linear_id)
        self.assertGreater(result["oi_contract"], 0)


if __name__ == "__main__":
    unittest.main()
