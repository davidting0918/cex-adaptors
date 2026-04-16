import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from cex_adaptors.binance import Binance
from tests.unit.binance._fixtures import load


class BinanceAdaptorTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.binance = Binance()

        # Mock the three stacked HTTP clients so no network call happens.
        self.binance.spot._get_exchange_info = AsyncMock(return_value=load("spot_exchange_info"))
        self.binance.linear._get_exchange_info = AsyncMock(return_value=load("linear_exchange_info"))
        self.binance.inverse._get_exchange_info = AsyncMock(return_value=load("inverse_exchange_info"))

        await self.binance.sync_exchange_info()

    async def asyncTearDown(self):
        await self.binance.close()


class TestBinanceExchangeInfo(BinanceAdaptorTestCase):
    async def test_sync_exchange_info_merges_all_markets(self):
        info = self.binance.exchange_info

        # spot + margin
        self.assertIn("BTC/USDT:USDT", info)
        self.assertIn("ETH/USDT:USDT", info)
        # linear perp + futures
        self.assertIn("BTC/USDT:USDT-PERP", info)
        self.assertIn("1000SHIB/USDT:USDT-PERP", info)
        self.assertIn("BTC/USDT:USDT-240329", info)
        # inverse perp
        self.assertIn("BTC/USD:BTC-PERP", info)

    async def test_get_exchange_info_filter_by_market_type(self):
        spot = await self.binance.get_exchange_info("spot")
        self.assertTrue(all(v["is_spot"] for v in spot.values()))

        margin = await self.binance.get_exchange_info("margin")
        self.assertTrue(all(v["is_margin"] for v in margin.values()))
        self.assertIn("BTC/USDT:USDT", margin)

        perp = await self.binance.get_exchange_info("perp")
        self.assertTrue(all(v["is_perp"] for v in perp.values()))

        futures = await self.binance.get_exchange_info("futures")
        self.assertTrue(all(v["is_futures"] for v in futures.values()))
        self.assertIn("BTC/USDT:USDT-240329", futures)


class TestBinanceTickers(BinanceAdaptorTestCase):
    async def test_get_ticker_spot(self):
        self.binance.spot._get_ticker = AsyncMock(return_value=load("spot_ticker"))

        result = await self.binance.get_ticker("BTC/USDT:USDT")
        self.binance.spot._get_ticker.assert_awaited_once_with("BTCUSDT")

        self.assertIn("BTC/USDT:USDT", result)
        self.assertEqual(result["BTC/USDT:USDT"]["last"], 20000.0)

    async def test_get_ticker_linear(self):
        self.binance.linear._get_ticker = AsyncMock(return_value=load("linear_ticker"))

        result = await self.binance.get_ticker("BTC/USDT:USDT-PERP")
        self.binance.linear._get_ticker.assert_awaited_once_with("BTCUSDT")
        self.assertEqual(result["BTC/USDT:USDT-PERP"]["last"], 20000.0)

    async def test_get_ticker_inverse(self):
        self.binance.inverse._get_ticker = AsyncMock(return_value=load("inverse_ticker"))

        result = await self.binance.get_ticker("BTC/USD:BTC-PERP")
        self.binance.inverse._get_ticker.assert_awaited_once_with("BTCUSD_PERP")
        self.assertEqual(result["BTC/USD:BTC-PERP"]["last"], 20000.0)

    async def test_get_tickers_all(self):
        self.binance.spot._get_tickers = AsyncMock(return_value=load("spot_tickers"))
        self.binance.linear._get_tickers = AsyncMock(return_value=load("linear_tickers"))
        self.binance.inverse._get_tickers = AsyncMock(return_value=load("inverse_tickers"))

        result = await self.binance.get_tickers()

        self.assertIn("BTC/USDT:USDT", result)
        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertIn("BTC/USD:BTC-PERP", result)

    async def test_get_tickers_filter_spot(self):
        self.binance.spot._get_tickers = AsyncMock(return_value=load("spot_tickers"))
        self.binance.linear._get_tickers = AsyncMock(return_value=load("linear_tickers"))
        self.binance.inverse._get_tickers = AsyncMock(return_value=load("inverse_tickers"))

        result = await self.binance.get_tickers("spot")

        self.assertIn("BTC/USDT:USDT", result)
        self.assertNotIn("BTC/USDT:USDT-PERP", result)
        self.assertNotIn("BTC/USD:BTC-PERP", result)


class TestBinanceCandlesticks(BinanceAdaptorTestCase):
    async def test_history_candlesticks_num(self):
        self.binance.spot._get_klines = AsyncMock(return_value=load("spot_klines"))

        result = await self.binance.get_history_candlesticks("BTC/USDT:USDT", "1h", num=2)

        self.assertEqual(len(result), 2)
        # returned list is sorted ascending by timestamp
        self.assertLess(result[0]["timestamp"], result[1]["timestamp"])
        self.binance.spot._get_klines.assert_awaited()

    async def test_history_candlesticks_window(self):
        self.binance.linear._get_klines = AsyncMock(return_value=load("linear_klines"))

        start = 1700000000000
        end = 1700003600000
        result = await self.binance.get_history_candlesticks("BTC/USDT:USDT-PERP", "1h", start=start, end=end)

        # fixture has timestamps 1700000000000 and 1700003600000 → both in window
        self.assertEqual(len(result), 2)
        for kline in result:
            self.assertGreaterEqual(kline["timestamp"], start)
            self.assertLessEqual(kline["timestamp"], end)

    async def test_current_candlestick(self):
        # parser returns a single dict when only one kline is supplied
        self.binance.spot._get_klines = AsyncMock(return_value=load("spot_klines")[:1])

        result = await self.binance.get_current_candlestick("BTC/USDT:USDT", "1h")
        self.assertIn("BTC/USDT:USDT", result)
        self.assertEqual(result["BTC/USDT:USDT"]["timestamp"], 1700000000000)


class TestBinanceFundingRate(BinanceAdaptorTestCase):
    async def test_current_funding_rate_linear(self):
        self.binance.linear._get_index_and_mark_price = AsyncMock(return_value=load("linear_premium_index"))

        result = await self.binance.get_current_funding_rate("BTC/USDT:USDT-PERP")
        self.binance.linear._get_index_and_mark_price.assert_awaited_once_with(symbol="BTCUSDT")
        self.assertEqual(result["BTC/USDT:USDT-PERP"]["funding_rate"], 0.0001)

    async def test_history_funding_rate_num(self):
        self.binance.linear._get_funding_rate_history = AsyncMock(return_value=load("linear_funding_rate_history"))

        result = await self.binance.get_history_funding_rate("BTC/USDT:USDT-PERP", num=2)

        self.assertEqual(len(result), 2)
        # sorted ascending
        self.assertLess(result[0]["timestamp"], result[1]["timestamp"])

    async def test_history_funding_rate_window(self):
        self.binance.linear._get_funding_rate_history = AsyncMock(return_value=load("linear_funding_rate_history"))

        start = 1699992000000
        end = 1700020800000
        result = await self.binance.get_history_funding_rate("BTC/USDT:USDT-PERP", start=start, end=end)

        self.assertTrue(all(start <= item["timestamp"] <= end for item in result))
        self.assertEqual(len(result), 2)


class TestBinanceDerivedPrices(BinanceAdaptorTestCase):
    async def test_index_price_linear(self):
        self.binance.linear._get_index_and_mark_price = AsyncMock(return_value=load("linear_premium_index"))

        result = await self.binance.get_index_price("BTC/USDT:USDT-PERP")
        self.assertEqual(result["index_price"], 20010.0)

    async def test_mark_price_linear(self):
        self.binance.linear._get_index_and_mark_price = AsyncMock(return_value=load("linear_premium_index"))

        result = await self.binance.get_mark_price("BTC/USDT:USDT-PERP")
        self.assertEqual(result["mark_price"], 20000.0)

    async def test_open_interest_linear(self):
        self.binance.linear._get_open_interest = AsyncMock(return_value=load("linear_open_interest"))

        result = await self.binance.get_open_interest("BTC/USDT:USDT-PERP")
        self.assertEqual(result["oi_contract"], 12345.678)

    async def test_open_interest_rejects_spot(self):
        with self.assertRaises(ValueError):
            await self.binance.get_open_interest("BTC/USDT:USDT")

    async def test_last_price(self):
        self.binance.spot._get_ticker = AsyncMock(return_value=load("spot_ticker"))

        result = await self.binance.get_last_price("BTC/USDT:USDT")
        self.assertEqual(result["last_price"], 20000.0)
        self.assertEqual(result["market_type"], "spot")


class TestBinanceOrderbook(BinanceAdaptorTestCase):
    async def test_orderbook_spot(self):
        self.binance.spot._get_order_book = AsyncMock(return_value=load("spot_orderbook"))

        result = await self.binance.get_orderbook("BTC/USDT:USDT", depth=2)
        self.binance.spot._get_order_book.assert_awaited_once_with(symbol="BTCUSDT", limit=5000)
        self.assertEqual(len(result["bids"]), 2)
        self.assertEqual(len(result["asks"]), 2)

    async def test_orderbook_linear(self):
        self.binance.linear._get_order_book = AsyncMock(return_value=load("linear_orderbook"))

        result = await self.binance.get_orderbook("BTC/USDT:USDT-PERP")
        self.binance.linear._get_order_book.assert_awaited_once_with(symbol="BTCUSDT", limit=1000)
        self.assertEqual(len(result["bids"]), 2)


class TestBinanceRejectsUnknownInstrument(BinanceAdaptorTestCase):
    async def test_unknown_instrument_current_candlestick(self):
        with self.assertRaises(ValueError):
            await self.binance.get_current_candlestick("UNKNOWN/XYZ:XYZ", "1h")

    async def test_unknown_instrument_orderbook(self):
        with self.assertRaises(ValueError):
            await self.binance.get_orderbook("UNKNOWN/XYZ:XYZ")

    async def test_unknown_instrument_funding_rate(self):
        with self.assertRaises(ValueError):
            await self.binance.get_current_funding_rate("UNKNOWN/XYZ:XYZ-PERP")


if __name__ == "__main__":
    unittest.main()
