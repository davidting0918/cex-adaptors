import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from cex_adaptors.okx import Okx
from tests.unit.okx._fixtures import load

_EXCHANGE_INFO_BY_INST_TYPE = {
    "SPOT": "spot_exchange_info",
    "MARGIN": "margin_exchange_info",
    "FUTURES": "futures_exchange_info",
    "SWAP": "perp_exchange_info",
}

_TICKERS_BY_INST_TYPE = {
    "SPOT": "spot_tickers",
    "FUTURES": "futures_tickers",
    "SWAP": "perp_tickers",
}


class OkxAdaptorTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.okx = Okx()

        # Mock the HTTP exchange-info call so sync_exchange_info runs offline.
        self.okx._get_exchange_info = AsyncMock(
            side_effect=lambda instType: load(_EXCHANGE_INFO_BY_INST_TYPE[instType])
        )
        await self.okx.sync_exchange_info()

    async def asyncTearDown(self):
        await self.okx.close()


class TestOkxExchangeInfo(OkxAdaptorTestCase):
    async def test_sync_exchange_info_merges_all_markets(self):
        info = self.okx.exchange_info

        # spot + margin merged into spot keys
        self.assertIn("BTC/USDT:USDT", info)
        self.assertIn("ETH/USDT:USDT", info)
        # perp (linear + inverse)
        self.assertIn("BTC/USDT:USDT-PERP", info)
        self.assertIn("ETH/USDT:USDT-PERP", info)
        self.assertIn("BTC/USD:BTC-PERP", info)
        # futures (linear + inverse)
        self.assertIn("BTC/USDT:USDT-240329", info)
        self.assertIn("BTC/USD:BTC-240329", info)

        # BTC/USDT:USDT should be flagged as margin after combine
        self.assertTrue(info["BTC/USDT:USDT"]["is_margin"])
        self.assertFalse(info["ETH/USDT:USDT"]["is_margin"])

    async def test_get_exchange_info_spot_only(self):
        spot = await self.okx.get_exchange_info("spot")
        self.assertIn("BTC/USDT:USDT", spot)
        self.assertTrue(all(v["is_spot"] for v in spot.values()))

    async def test_get_exchange_info_perp_only(self):
        perp = await self.okx.get_exchange_info("perp")
        self.assertTrue(all(v["is_perp"] for v in perp.values()))
        self.assertIn("BTC/USDT:USDT-PERP", perp)

    async def test_get_exchange_info_futures_only(self):
        futures = await self.okx.get_exchange_info("futures")
        self.assertTrue(all(v["is_futures"] for v in futures.values()))
        self.assertIn("BTC/USDT:USDT-240329", futures)


class TestOkxTickers(OkxAdaptorTestCase):
    async def test_get_ticker_spot(self):
        self.okx._get_ticker = AsyncMock(return_value=load("spot_ticker"))

        result = await self.okx.get_ticker("BTC/USDT:USDT")
        self.okx._get_ticker.assert_awaited_once_with("BTC-USDT")

        self.assertEqual(result["instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(result["last"], 20000.0)
        self.assertEqual(result["market_type"], "spot")

    async def test_get_ticker_perp(self):
        self.okx._get_ticker = AsyncMock(return_value=load("perp_ticker"))

        result = await self.okx.get_ticker("BTC/USDT:USDT-PERP")
        self.okx._get_ticker.assert_awaited_once_with("BTC-USDT-SWAP")
        self.assertEqual(result["instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(result["last"], 20000.0)
        self.assertEqual(result["market_type"], "perp")

    async def test_get_tickers_all(self):
        self.okx._get_tickers = AsyncMock(side_effect=lambda instType: load(_TICKERS_BY_INST_TYPE[instType]))

        result = await self.okx.get_tickers()

        self.assertIn("BTC/USDT:USDT", result)
        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertIn("BTC/USD:BTC-PERP", result)
        self.assertIn("BTC/USDT:USDT-240329", result)

    async def test_get_tickers_filter_spot(self):
        self.okx._get_tickers = AsyncMock(return_value=load("spot_tickers"))

        result = await self.okx.get_tickers("spot")
        self.okx._get_tickers.assert_awaited_once_with("SPOT")

        self.assertIn("BTC/USDT:USDT", result)
        self.assertNotIn("BTC/USDT:USDT-PERP", result)

    async def test_get_tickers_filter_perp(self):
        self.okx._get_tickers = AsyncMock(return_value=load("perp_tickers"))

        result = await self.okx.get_tickers("perp")
        self.okx._get_tickers.assert_awaited_once_with("SWAP")

        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertNotIn("BTC/USDT:USDT", result)


class TestOkxCandlesticks(OkxAdaptorTestCase):
    async def test_history_candlesticks_num(self):
        self.okx._get_klines = AsyncMock(return_value=load("perp_candles"))

        result = await self.okx.get_history_candlesticks("BTC/USDT:USDT-PERP", "1h", num=2)

        self.assertEqual(len(result), 2)
        # sorted ascending by timestamp, last `num` retained
        self.assertLess(result[0]["timestamp"], result[1]["timestamp"])
        self.okx._get_klines.assert_awaited()

    async def test_history_candlesticks_window(self):
        self.okx._get_klines = AsyncMock(return_value=load("perp_candles"))

        start = 1700000000000
        end = 1700003600000
        result = await self.okx.get_history_candlesticks("BTC/USDT:USDT-PERP", "1h", start=start, end=end)

        # fixture has ts 1700000000000, 1700003600000, 1700007200000 → first two are in window
        self.assertEqual(len(result), 2)
        for kline in result:
            self.assertGreaterEqual(kline["timestamp"], start)
            self.assertLessEqual(kline["timestamp"], end)

    async def test_current_candlestick(self):
        self.okx._get_klines = AsyncMock(return_value=load("spot_candles_single"))

        result = await self.okx.get_current_candlestick("BTC/USDT:USDT", "1h")

        self.assertIn("BTC/USDT:USDT", result)
        self.assertEqual(result["BTC/USDT:USDT"]["timestamp"], 1700000000000)


class TestOkxFundingRate(OkxAdaptorTestCase):
    async def test_current_funding_rate(self):
        self.okx._get_current_funding_rate = AsyncMock(return_value=load("current_funding_rate"))

        result = await self.okx.get_current_funding_rate("BTC/USDT:USDT-PERP")
        self.okx._get_current_funding_rate.assert_awaited_once_with("BTC-USDT-SWAP")
        self.assertEqual(result["funding_rate"], 0.0001)
        self.assertEqual(result["instrument_id"], "BTC/USDT:USDT-PERP")

    async def test_history_funding_rate_num(self):
        self.okx._get_history_funding_rate = AsyncMock(return_value=load("history_funding_rate"))

        result = await self.okx.get_history_funding_rate("BTC/USDT:USDT-PERP", num=2)

        self.assertEqual(len(result), 2)
        # sorted ascending
        self.assertLess(result[0]["timestamp"], result[1]["timestamp"])

    async def test_history_funding_rate_window(self):
        self.okx._get_history_funding_rate = AsyncMock(return_value=load("history_funding_rate"))

        start = 1699992000000
        end = 1700020800000
        result = await self.okx.get_history_funding_rate("BTC/USDT:USDT-PERP", start=start, end=end)

        self.assertTrue(all(start <= item["timestamp"] <= end for item in result))
        self.assertEqual(len(result), 3)


class TestOkxDerivedPrices(OkxAdaptorTestCase):
    async def test_index_price(self):
        self.okx._get_index_ticker = AsyncMock(return_value=load("index_ticker"))

        result = await self.okx.get_index_price("BTC/USDT:USDT-PERP")
        # perp instId BTC-USDT-SWAP -> trimmed to BTC-USDT for index lookup; quote USDT passed
        self.okx._get_index_ticker.assert_awaited_once_with("BTC-USDT", "USDT")
        self.assertEqual(result["index_price"], 20010.0)

    async def test_mark_price(self):
        self.okx._get_mark_price = AsyncMock(return_value=load("mark_price"))

        result = await self.okx.get_mark_price("BTC/USDT:USDT-PERP")
        self.okx._get_mark_price.assert_awaited_once_with("BTC-USDT-SWAP", "SWAP")
        self.assertEqual(result["mark_price"], 20005.0)

    async def test_mark_price_spot_rewrites_market(self):
        # SPOT is not a valid instType for mark-price → adaptor substitutes MARGIN
        self.okx._get_mark_price = AsyncMock(return_value=load("mark_price"))

        await self.okx.get_mark_price("BTC/USDT:USDT")
        self.okx._get_mark_price.assert_awaited_once_with("BTC-USDT", "MARGIN")

    async def test_open_interest_single(self):
        self.okx._get_open_interest = AsyncMock(return_value=load("open_interest_single"))

        result = await self.okx.get_open_interest("BTC/USDT:USDT-PERP")
        self.okx._get_open_interest.assert_awaited_once_with(instId="BTC-USDT-SWAP")
        self.assertEqual(result["oi_contract"], 123456.0)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    async def test_open_interest_by_market_type(self):
        self.okx._get_open_interest = AsyncMock(return_value=load("open_interest_market"))

        result = await self.okx.get_open_interest(market_type="perp")
        self.okx._get_open_interest.assert_awaited_once_with(instType="SWAP")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    async def test_open_interest_requires_argument(self):
        with self.assertRaises(Exception):
            await self.okx.get_open_interest()

    async def test_last_price(self):
        self.okx._get_ticker = AsyncMock(return_value=load("spot_ticker"))

        result = await self.okx.get_last_price("BTC/USDT:USDT")
        self.assertEqual(result["last_price"], 20000.0)
        self.assertEqual(result["market_type"], "spot")


class TestOkxOrderbook(OkxAdaptorTestCase):
    async def test_orderbook(self):
        self.okx._get_orderbook = AsyncMock(return_value=load("orderbook"))

        result = await self.okx.get_orderbook("BTC/USDT:USDT", depth=20)
        self.okx._get_orderbook.assert_awaited_once_with("BTC-USDT", "20")
        # parser returns all levels the API returned; 3 in fixture
        self.assertEqual(len(result["asks"]), 3)
        self.assertEqual(len(result["bids"]), 3)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT")


class TestOkxRejectsUnknownInstrument(OkxAdaptorTestCase):
    async def test_unknown_ticker(self):
        with self.assertRaises(Exception):
            await self.okx.get_ticker("UNKNOWN/XYZ:XYZ")

    async def test_unknown_current_candlestick(self):
        with self.assertRaises(Exception):
            await self.okx.get_current_candlestick("UNKNOWN/XYZ:XYZ", "1h")

    async def test_unknown_orderbook(self):
        with self.assertRaises(Exception):
            await self.okx.get_orderbook("UNKNOWN/XYZ:XYZ")

    async def test_unknown_current_funding_rate(self):
        with self.assertRaises(Exception):
            await self.okx.get_current_funding_rate("UNKNOWN/XYZ:XYZ-PERP")

    async def test_unknown_last_price(self):
        with self.assertRaises(Exception):
            await self.okx.get_last_price("UNKNOWN/XYZ:XYZ")

    async def test_unknown_index_price(self):
        with self.assertRaises(Exception):
            await self.okx.get_index_price("UNKNOWN/XYZ:XYZ-PERP")


if __name__ == "__main__":
    unittest.main()
