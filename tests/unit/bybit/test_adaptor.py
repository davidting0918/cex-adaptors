import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from cex_adaptors.bybit import Bybit
from tests.unit.bybit._fixtures import load


def _exchange_info_side_effect(category: str):
    return {
        "spot": load("spot_exchange_info"),
        "linear": load("linear_exchange_info"),
        "inverse": load("inverse_exchange_info"),
    }[category]


class BybitAdaptorTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bybit = Bybit()

        # One HTTP method serves all three categories — dispatch on the category arg.
        self.bybit._get_exchange_info = AsyncMock(side_effect=_exchange_info_side_effect)

        await self.bybit.sync_exchange_info()

    async def asyncTearDown(self):
        await self.bybit.close()


class TestBybitExchangeInfo(BybitAdaptorTestCase):
    async def test_sync_exchange_info_merges_all_markets(self):
        info = self.bybit.exchange_info

        # spot
        self.assertIn("BTC/USDT:USDT", info)
        self.assertIn("ETH/USDT:USDT", info)
        # linear perp (including multiplier token)
        self.assertIn("BTC/USDT:USDT-PERP", info)
        self.assertIn("1000SHIB/USDT:USDT-PERP", info)
        # inverse perp
        self.assertIn("BTC/USD:BTC-PERP", info)
        self.assertIn("ETH/USD:ETH-PERP", info)

    async def test_get_exchange_info_full(self):
        info = await self.bybit.get_exchange_info()
        self.assertIn("BTC/USDT:USDT", info)
        self.assertIn("BTC/USDT:USDT-PERP", info)
        self.assertIn("BTC/USD:BTC-PERP", info)


class TestBybitTickers(BybitAdaptorTestCase):
    async def test_get_ticker_spot(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("spot_ticker"))

        result = await self.bybit.get_ticker("BTC/USDT:USDT")
        self.bybit._get_ticker.assert_awaited_once_with(symbol="BTCUSDT", category="spot")

        self.assertIn("BTC/USDT:USDT", result)
        self.assertEqual(result["BTC/USDT:USDT"]["last"], 20000.0)

    async def test_get_ticker_linear(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("linear_ticker"))

        result = await self.bybit.get_ticker("BTC/USDT:USDT-PERP")
        self.bybit._get_ticker.assert_awaited_once_with(symbol="BTCUSDT", category="linear")
        self.assertEqual(result["BTC/USDT:USDT-PERP"]["last"], 20000.0)

    async def test_get_ticker_inverse(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("inverse_ticker"))

        result = await self.bybit.get_ticker("BTC/USD:BTC-PERP")
        self.bybit._get_ticker.assert_awaited_once_with(symbol="BTCUSD", category="inverse")
        self.assertEqual(result["BTC/USD:BTC-PERP"]["last"], 20000.0)

    async def test_get_tickers_all(self):
        tickers_map = {
            "spot": load("spot_tickers"),
            "linear": load("linear_tickers"),
            "inverse": load("inverse_tickers"),
        }
        self.bybit._get_tickers = AsyncMock(side_effect=lambda category: tickers_map[category])

        result = await self.bybit.get_tickers()

        self.assertIn("BTC/USDT:USDT", result)
        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertIn("BTC/USD:BTC-PERP", result)
        self.assertIn("1000SHIB/USDT:USDT-PERP", result)

    async def test_get_tickers_filter_spot(self):
        tickers_map = {
            "spot": load("spot_tickers"),
            "linear": load("linear_tickers"),
            "inverse": load("inverse_tickers"),
        }
        self.bybit._get_tickers = AsyncMock(side_effect=lambda category: tickers_map[category])

        result = await self.bybit.get_tickers("spot")

        self.assertIn("BTC/USDT:USDT", result)
        self.assertNotIn("BTC/USDT:USDT-PERP", result)
        self.assertNotIn("BTC/USD:BTC-PERP", result)


class TestBybitCandlesticks(BybitAdaptorTestCase):
    async def test_history_candlesticks_num(self):
        # spot_klines has 3 entries, less than limit=1000 so the loop exits
        self.bybit._get_klines = AsyncMock(return_value=load("spot_klines"))

        result = await self.bybit.get_history_candlesticks("BTC/USDT:USDT", "1h", num=2)

        self.assertEqual(len(result), 2)
        # returned list sorted ascending by timestamp
        self.assertLess(result[0]["timestamp"], result[1]["timestamp"])
        self.bybit._get_klines.assert_awaited()

    async def test_history_candlesticks_window(self):
        self.bybit._get_klines = AsyncMock(return_value=load("linear_klines"))

        start = 1700000000000
        end = 1700003600000
        result = await self.bybit.get_history_candlesticks("BTC/USDT:USDT-PERP", "1h", start=start, end=end)

        self.assertEqual(len(result), 2)
        for kline in result:
            self.assertGreaterEqual(kline["timestamp"], start)
            self.assertLessEqual(kline["timestamp"], end)

    async def test_current_candlestick(self):
        raw = load("spot_klines")
        raw["result"]["list"] = raw["result"]["list"][:1]
        self.bybit._get_klines = AsyncMock(return_value=raw)

        result = await self.bybit.get_current_candlestick("BTC/USDT:USDT", "1h")
        self.assertIn("BTC/USDT:USDT", result)
        self.assertEqual(result["BTC/USDT:USDT"]["timestamp"], 1700007200000)

    async def test_history_candlesticks_translates_interval(self):
        self.bybit._get_klines = AsyncMock(return_value=load("spot_klines"))
        await self.bybit.get_history_candlesticks("BTC/USDT:USDT", "1h", num=1)

        # "1h" → "60" per Bybit V5 interval map
        called_kwargs = self.bybit._get_klines.await_args.kwargs
        self.assertEqual(called_kwargs["interval"], "60")
        self.assertEqual(called_kwargs["category"], "spot")
        self.assertEqual(called_kwargs["symbol"], "BTCUSDT")


class TestBybitFundingRate(BybitAdaptorTestCase):
    async def test_current_funding_rate_linear(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("linear_ticker"))

        result = await self.bybit.get_current_funding_rate("BTC/USDT:USDT-PERP")
        self.bybit._get_ticker.assert_awaited_once_with(symbol="BTCUSDT", category="linear")
        self.assertEqual(result["BTC/USDT:USDT-PERP"]["funding_rate"], 0.0001)

    async def test_history_funding_rate_num(self):
        self.bybit._get_funding_rate_history = AsyncMock(return_value=load("linear_funding_rate_history"))

        result = await self.bybit.get_history_funding_rate("BTC/USDT:USDT-PERP", num=2)

        self.assertEqual(len(result), 2)
        # sorted ascending
        self.assertLess(result[0]["timestamp"], result[1]["timestamp"])

    async def test_history_funding_rate_window(self):
        self.bybit._get_funding_rate_history = AsyncMock(return_value=load("linear_funding_rate_history"))

        start = 1699992000000
        end = 1700020800000
        result = await self.bybit.get_history_funding_rate("BTC/USDT:USDT-PERP", start=start, end=end)

        self.assertTrue(all(start <= item["timestamp"] <= end for item in result))
        self.assertEqual(len(result), 3)


class TestBybitDerivedPrices(BybitAdaptorTestCase):
    async def test_index_price_linear(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("linear_ticker"))

        result = await self.bybit.get_index_price("BTC/USDT:USDT-PERP")
        self.assertEqual(result["index_price"], 20010.0)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    async def test_mark_price_linear(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("linear_ticker"))

        result = await self.bybit.get_mark_price("BTC/USDT:USDT-PERP")
        self.assertEqual(result["mark_price"], 20005.0)

    async def test_open_interest_linear(self):
        self.bybit._get_open_interest = AsyncMock(return_value=load("linear_open_interest"))

        result = await self.bybit.get_open_interest("BTC/USDT:USDT-PERP")
        self.assertEqual(result["open_interest"], 12345.678)

    async def test_last_price_spot(self):
        self.bybit._get_ticker = AsyncMock(return_value=load("spot_ticker"))

        result = await self.bybit.get_last_price("BTC/USDT:USDT")
        self.assertEqual(result["last_price"], 20000.0)
        self.assertEqual(result["market_type"], "spot")


class TestBybitOrderbook(BybitAdaptorTestCase):
    async def test_orderbook_spot(self):
        self.bybit._get_orderbook = AsyncMock(return_value=load("spot_orderbook"))

        result = await self.bybit.get_orderbook("BTC/USDT:USDT", depth=50)
        self.bybit._get_orderbook.assert_awaited_once_with(category="spot", symbol="BTCUSDT", limit=50)
        self.assertEqual(len(result["bids"]), 3)
        self.assertEqual(len(result["asks"]), 3)

    async def test_orderbook_linear_caps_depth(self):
        self.bybit._get_orderbook = AsyncMock(return_value=load("linear_orderbook"))

        # depth=1000 requested but linear cap is 500
        result = await self.bybit.get_orderbook("BTC/USDT:USDT-PERP", depth=1000)
        self.bybit._get_orderbook.assert_awaited_once_with(category="linear", symbol="BTCUSDT", limit=500)
        self.assertEqual(len(result["bids"]), 2)


class TestBybitRejectsUnknownInstrument(BybitAdaptorTestCase):
    async def test_unknown_instrument_ticker(self):
        with self.assertRaises(ValueError):
            await self.bybit.get_ticker("UNKNOWN/XYZ:XYZ")

    async def test_unknown_instrument_current_candlestick(self):
        with self.assertRaises(ValueError):
            await self.bybit.get_current_candlestick("UNKNOWN/XYZ:XYZ", "1h")

    async def test_unknown_instrument_orderbook(self):
        with self.assertRaises(ValueError):
            await self.bybit.get_orderbook("UNKNOWN/XYZ:XYZ")

    async def test_unknown_instrument_funding_rate(self):
        with self.assertRaises(ValueError):
            await self.bybit.get_current_funding_rate("UNKNOWN/XYZ:XYZ-PERP")

    async def test_unknown_instrument_open_interest(self):
        with self.assertRaises(ValueError):
            await self.bybit.get_open_interest("UNKNOWN/XYZ:XYZ-PERP")


if __name__ == "__main__":
    unittest.main()
