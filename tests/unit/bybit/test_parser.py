import unittest

from cex_adaptors.parsers.bybit import BybitParser
from tests.unit.bybit._fixtures import load


class TestBybitExchangeInfo(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()

    def test_parse_spot_exchange_info(self):
        raw = load("spot_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.spot_exchange_info_parser)

        self.assertIn("BTC/USDT:USDT", result)
        self.assertIn("ETH/USDT:USDT", result)

        btc = result["BTC/USDT:USDT"]
        self.assertTrue(btc["active"])
        self.assertTrue(btc["is_spot"])
        # marginTrading = "utaOnly" → is_margin True
        self.assertTrue(btc["is_margin"])
        self.assertFalse(btc["is_perp"])
        self.assertFalse(btc["is_futures"])
        self.assertTrue(btc["is_linear"])
        self.assertFalse(btc["is_inverse"])
        self.assertEqual(btc["base"], "BTC")
        self.assertEqual(btc["quote"], "USDT")
        self.assertEqual(btc["settle"], "USDT")
        self.assertEqual(btc["contract_size"], 1)
        self.assertEqual(btc["tick_size"], 0.01)
        self.assertEqual(btc["raw_data"]["symbol"], "BTCUSDT")

        eth = result["ETH/USDT:USDT"]
        # marginTrading = "none" → is_margin False
        self.assertFalse(eth["is_margin"])

        # Closed status → active is False but record still present
        self.assertFalse(result["SOL/USDC:USDC"]["active"])

    def test_parse_linear_exchange_info(self):
        raw = load("linear_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.perp_futures_exchange_info_parser)

        perp = result["BTC/USDT:USDT-PERP"]
        self.assertTrue(perp["is_perp"])
        self.assertFalse(perp["is_futures"])
        self.assertTrue(perp["is_linear"])
        self.assertFalse(perp["is_inverse"])
        self.assertEqual(perp["base"], "BTC")
        self.assertEqual(perp["quote"], "USDT")
        self.assertEqual(perp["settle"], "USDT")
        self.assertEqual(perp["multiplier"], 1)
        self.assertEqual(perp["contract_size"], 0.001)
        self.assertEqual(perp["listing_time"], 1585526400000)
        self.assertEqual(perp["leverage"], 100.0)

        multiplier_perp = result["1000SHIB/USDT:USDT-PERP"]
        self.assertEqual(multiplier_perp["base"], "SHIB")
        self.assertEqual(multiplier_perp["multiplier"], 1000)

    def test_parse_inverse_exchange_info(self):
        raw = load("inverse_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.perp_futures_exchange_info_parser)

        btc = result["BTC/USD:BTC-PERP"]
        self.assertTrue(btc["is_perp"])
        self.assertTrue(btc["is_inverse"])
        self.assertFalse(btc["is_linear"])
        self.assertEqual(btc["base"], "BTC")
        self.assertEqual(btc["quote"], "USD")
        self.assertEqual(btc["settle"], "BTC")

        eth = result["ETH/USD:ETH-PERP"]
        self.assertTrue(eth["is_inverse"])
        self.assertEqual(eth["settle"], "ETH")


class TestBybitTicker(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()
        self.spot_info = self.parser.parse_exchange_info(
            load("spot_exchange_info"), self.parser.spot_exchange_info_parser
        )
        self.linear_info = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )
        self.inverse_info = self.parser.parse_exchange_info(
            load("inverse_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )

    def test_parse_raw_ticker_spot(self):
        info = self.spot_info["BTC/USDT:USDT"]
        ticker = self.parser.parse_raw_ticker(load("spot_ticker"), "spot", info)

        self.assertEqual(ticker["timestamp"], 1700086400000)
        self.assertEqual(ticker["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(ticker["open"], 19900.0)
        self.assertEqual(ticker["high"], 20100.0)
        self.assertEqual(ticker["low"], 19800.0)
        self.assertEqual(ticker["last"], 20000.0)
        self.assertEqual(ticker["base_volume"], 1000.0)
        self.assertEqual(ticker["quote_volume"], 20000000.0)
        # Bybit parser computes prevPrice24h - lastPrice (negative when price rose)
        self.assertEqual(ticker["price_change"], -100.0)
        self.assertAlmostEqual(ticker["price_change_percent"], 0.005)

    def test_parse_raw_ticker_linear(self):
        info = self.linear_info["BTC/USDT:USDT-PERP"]
        ticker = self.parser.parse_raw_ticker(load("linear_ticker"), "linear", info)

        self.assertEqual(ticker["perp_instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(ticker["last"], 20000.0)
        # For linear: base_volume ← volume24h, quote_volume ← turnover24h
        self.assertEqual(ticker["base_volume"], 1000.0)
        self.assertEqual(ticker["quote_volume"], 20000000.0)

    def test_parse_raw_ticker_inverse_swaps_volume_fields(self):
        info = self.inverse_info["BTC/USD:BTC-PERP"]
        ticker = self.parser.parse_raw_ticker(load("inverse_ticker"), "inverse", info)

        self.assertEqual(ticker["perp_instrument_id"], "BTC/USD:BTC-PERP")
        # For inverse: base_volume ← turnover24h, quote_volume ← volume24h
        self.assertEqual(ticker["base_volume"], 50.0)
        self.assertEqual(ticker["quote_volume"], 1000000.0)

    def test_parse_tickers_spot_skips_unknown(self):
        result = self.parser.parse_tickers(load("spot_tickers"), "spot", self.spot_info)

        self.assertEqual(set(result.keys()), {"BTC/USDT:USDT", "ETH/USDT:USDT"})
        self.assertEqual(result["BTC/USDT:USDT"]["last"], 20000.0)
        self.assertEqual(result["ETH/USDT:USDT"]["last"], 1500.0)

    def test_parse_tickers_linear_filters_by_market_type(self):
        infos = {**self.spot_info, **self.linear_info, **self.inverse_info}
        result = self.parser.parse_tickers(load("linear_tickers"), "linear", infos)

        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertIn("1000SHIB/USDT:USDT-PERP", result)

    def test_parse_tickers_inverse(self):
        infos = {**self.spot_info, **self.linear_info, **self.inverse_info}
        result = self.parser.parse_tickers(load("inverse_tickers"), "inverse", infos)

        self.assertIn("BTC/USD:BTC-PERP", result)
        self.assertIn("ETH/USD:ETH-PERP", result)


class TestBybitCandlesticks(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()
        spot_infos = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_exchange_info_parser)
        linear_infos = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )
        inverse_infos = self.parser.parse_exchange_info(
            load("inverse_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )
        self.spot_info = spot_infos["BTC/USDT:USDT"]
        self.linear_info = linear_infos["BTC/USDT:USDT-PERP"]
        self.inverse_info = inverse_infos["BTC/USD:BTC-PERP"]

    def test_parse_candlesticks_spot_list(self):
        raw = load("spot_klines")
        result = self.parser.parse_candlesticks(raw, self.spot_info, "spot", "1h")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        # find the 1700000000000 kline regardless of order
        first = next(r for r in result if r["timestamp"] == 1700000000000)
        self.assertEqual(first["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(first["market_type"], "spot")
        self.assertEqual(first["interval"], "1h")
        self.assertEqual(first["open"], 19900.0)
        self.assertEqual(first["high"], 20050.0)
        self.assertEqual(first["low"], 19850.0)
        self.assertEqual(first["close"], 20000.0)
        self.assertEqual(first["base_volume"], 10.0)
        self.assertEqual(first["quote_volume"], 200000.0)
        # spot market_type → contract_volume divides by 1
        self.assertEqual(first["contract_volume"], 10.0)

    def test_parse_candlesticks_single_returns_dict(self):
        raw = load("spot_klines")
        raw["result"]["list"] = raw["result"]["list"][:1]
        result = self.parser.parse_candlesticks(raw, self.spot_info, "spot", "1h")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["timestamp"], 1700007200000)

    def test_parse_candlesticks_linear_contract_size(self):
        raw = load("linear_klines")
        result = self.parser.parse_candlesticks(raw, self.linear_info, "linear", "1h")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        # contract_size = 0.001 → contract_volume = base_volume / 0.001
        first = next(r for r in result if r["timestamp"] == 1700000000000)
        self.assertEqual(first["base_volume"], 10.0)
        self.assertAlmostEqual(first["contract_volume"], 10.0 / 0.001)


class TestBybitFundingRate(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()
        info = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )
        self.linear_info = info["BTC/USDT:USDT-PERP"]

    def test_parse_current_funding_rate(self):
        # The parse_current_funding_rate reads from a ticker response (which
        # contains fundingRate and nextFundingTime), not from funding history.
        raw = load("linear_ticker")
        result = self.parser.parse_current_funding_rate(raw, self.linear_info)

        self.assertEqual(result["timestamp"], 1700086400000)
        self.assertEqual(result["next_funding_time"], 1700028800000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(result["market_type"], "perp")
        self.assertEqual(result["funding_rate"], 0.0001)

    def test_parse_history_funding_rate(self):
        raw = load("linear_funding_rate_history")
        result = self.parser.parse_funding_rate(raw, self.linear_info)

        self.assertEqual(len(result), 3)
        for item in result:
            self.assertEqual(item["perp_instrument_id"], "BTC/USDT:USDT-PERP")
            self.assertEqual(item["market_type"], "perp")
            self.assertEqual(item["realized_rate"], item["funding_rate"])
        # first entry is most recent per Bybit API
        self.assertEqual(result[0]["timestamp"], 1700020800000)
        self.assertEqual(result[0]["funding_rate"], 0.00015)


class TestBybitDerivedPrices(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()
        linear = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )
        self.linear_info = linear["BTC/USDT:USDT-PERP"]

    def test_parse_index_price(self):
        result = self.parser.parse_index_price(load("linear_ticker"), self.linear_info)
        self.assertEqual(result["index_price"], 20010.0)
        self.assertEqual(result["timestamp"], 1700086400000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(result["market_type"], "perp")

    def test_parse_mark_price(self):
        result = self.parser.parse_mark_price(load("linear_ticker"), self.linear_info)
        self.assertEqual(result["mark_price"], 20005.0)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    def test_parse_last_price(self):
        result = self.parser.parse_last_price(load("linear_ticker"), self.linear_info)
        self.assertEqual(result["last_price"], 20000.0)
        self.assertEqual(result["market_type"], "perp")

    def test_parse_open_interest(self):
        result = self.parser.parse_open_interest(load("linear_open_interest"), self.linear_info)
        self.assertEqual(result["open_interest"], 12345.678)
        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")


class TestBybitOrderbook(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_exchange_info_parser)
        linear = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.perp_futures_exchange_info_parser
        )
        self.spot_info = spot["BTC/USDT:USDT"]
        self.linear_info = linear["BTC/USDT:USDT-PERP"]

    def test_parse_orderbook_spot(self):
        result = self.parser.parse_orderbook(load("spot_orderbook"), self.spot_info)

        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(result["timestamp"], 1700000000123)
        self.assertEqual(len(result["bids"]), 3)
        self.assertEqual(len(result["asks"]), 3)
        self.assertEqual(result["bids"][0]["price"], 19999.0)
        self.assertEqual(result["bids"][0]["volume"], 1.5)
        self.assertEqual(result["asks"][0]["price"], 20001.0)
        self.assertIsNone(result["bids"][0]["order_number"])

    def test_parse_orderbook_linear(self):
        result = self.parser.parse_orderbook(load("linear_orderbook"), self.linear_info)

        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(len(result["bids"]), 2)
        self.assertEqual(len(result["asks"]), 2)


class TestBybitCheckResponse(unittest.TestCase):
    def setUp(self):
        self.parser = BybitParser()

    def test_non_zero_retcode_raises(self):
        with self.assertRaises(ValueError):
            self.parser.check_response({"retCode": 10001, "retMsg": "bad", "result": {}, "time": 1700000000000})

    def test_get_interval_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.parser.get_interval("not-a-real-interval")

    def test_open_interest_interval_unknown_raises(self):
        with self.assertRaises(ValueError):
            self.parser.get_open_interest_interval("not-a-real-interval")


if __name__ == "__main__":
    unittest.main()
