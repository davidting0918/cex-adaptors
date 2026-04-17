import unittest

from cex_adaptors.parsers.binance import BinanceParser
from tests.unit.binance._fixtures import load


class TestBinanceExchangeInfo(unittest.TestCase):
    def setUp(self):
        self.parser = BinanceParser()

    def test_parse_spot_exchange_info(self):
        raw = load("spot_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.spot_exchange_info_parser)

        self.assertIn("BTC/USDT:USDT", result)
        self.assertIn("ETH/USDT:USDT", result)

        btc = result["BTC/USDT:USDT"]
        self.assertTrue(btc["active"])
        self.assertTrue(btc["is_spot"])
        self.assertTrue(btc["is_margin"])
        self.assertFalse(btc["is_perp"])
        self.assertFalse(btc["is_futures"])
        self.assertTrue(btc["is_linear"])
        self.assertFalse(btc["is_inverse"])
        self.assertEqual(btc["base"], "BTC")
        self.assertEqual(btc["quote"], "USDT")
        self.assertEqual(btc["settle"], "USDT")
        self.assertEqual(btc["contract_size"], 1)
        self.assertEqual(btc["raw_data"]["symbol"], "BTCUSDT")

        eth = result["ETH/USDT:USDT"]
        self.assertFalse(eth["is_margin"])

        # BREAK status → active is False but record still present
        self.assertFalse(result["SOL/BUSD:BUSD"]["active"])

    def test_parse_linear_exchange_info(self):
        raw = load("linear_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.futures_exchange_info_parser("linear"))

        perp = result["BTC/USDT:USDT-PERP"]
        self.assertTrue(perp["is_perp"])
        self.assertFalse(perp["is_futures"])
        self.assertTrue(perp["is_linear"])
        self.assertFalse(perp["is_inverse"])
        self.assertEqual(perp["base"], "BTC")
        self.assertEqual(perp["quote"], "USDT")
        self.assertEqual(perp["settle"], "USDT")
        self.assertEqual(perp["multiplier"], 1)
        self.assertEqual(perp["contract_size"], 1)
        self.assertEqual(perp["listing_time"], 1569398400000)

        multiplier_perp = result["1000SHIB/USDT:USDT-PERP"]
        self.assertEqual(multiplier_perp["base"], "SHIB")
        self.assertEqual(multiplier_perp["multiplier"], 1000)

        futures_id = "BTC/USDT:USDT-240329"
        self.assertIn(futures_id, result)
        futures = result[futures_id]
        self.assertTrue(futures["is_futures"])
        self.assertFalse(futures["is_perp"])
        self.assertEqual(futures["expiration_time"], 1711699200000)

    def test_parse_inverse_exchange_info(self):
        raw = load("inverse_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.futures_exchange_info_parser("inverse"))

        btc = result["BTC/USD:BTC-PERP"]
        self.assertTrue(btc["is_perp"])
        self.assertTrue(btc["is_inverse"])
        self.assertFalse(btc["is_linear"])
        self.assertEqual(btc["settle"], "BTC")
        self.assertEqual(btc["contract_size"], 100.0)


class TestBinanceTicker(unittest.TestCase):
    def setUp(self):
        self.parser = BinanceParser()
        self.spot_info = self.parser.parse_exchange_info(
            load("spot_exchange_info"), self.parser.spot_exchange_info_parser
        )
        self.linear_info = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.futures_exchange_info_parser("linear")
        )
        self.inverse_info = self.parser.parse_exchange_info(
            load("inverse_exchange_info"), self.parser.futures_exchange_info_parser("inverse")
        )

    def test_parse_ticker_spot(self):
        info = self.spot_info["BTC/USDT:USDT"]
        ticker = self.parser.parse_ticker(load("spot_ticker"), info)

        self.assertEqual(ticker["timestamp"], 1700086400000)
        self.assertEqual(ticker["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(ticker["open"], 19900.0)
        self.assertEqual(ticker["high"], 20100.0)
        self.assertEqual(ticker["low"], 19800.0)
        self.assertEqual(ticker["last"], 20000.0)
        self.assertEqual(ticker["base_volume"], 1000.0)
        self.assertEqual(ticker["quote_volume"], 20000000.0)
        self.assertEqual(ticker["price_change"], 100.0)
        self.assertAlmostEqual(ticker["price_change_percent"], 0.005)

    def test_parse_ticker_linear(self):
        info = self.linear_info["BTC/USDT:USDT-PERP"]
        ticker = self.parser.parse_ticker(load("linear_ticker"), info)

        self.assertEqual(ticker["perp_instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(ticker["base_volume"], 1000.0)
        # linear perp contract_size defaults to 1, so quote_volume unchanged
        self.assertEqual(ticker["quote_volume"], 20000000.0)

    def test_parse_ticker_inverse_multiplies_by_contract_size(self):
        info = self.inverse_info["BTC/USD:BTC-PERP"]
        # API returns array for inverse — parser unwraps first element
        ticker = self.parser.parse_ticker(load("inverse_ticker"), info)

        self.assertEqual(ticker["perp_instrument_id"], "BTC/USD:BTC-PERP")
        self.assertEqual(ticker["base_volume"], 50.0)
        # volume (10000 contracts) * contract_size (100) = 1,000,000 USD
        self.assertEqual(ticker["quote_volume"], 1_000_000.0)

    def test_parse_tickers_spot_skips_unknown(self):
        infos = {**self.spot_info, **self.linear_info, **self.inverse_info}
        result = self.parser.parse_tickers(load("spot_tickers"), "spot", infos)

        self.assertEqual(set(result.keys()), {"BTC/USDT:USDT", "ETH/USDT:USDT"})

    def test_parse_tickers_linear_filters_by_market_type(self):
        infos = {**self.spot_info, **self.linear_info, **self.inverse_info}
        result = self.parser.parse_tickers(load("linear_tickers"), "linear", infos)

        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertIn("1000SHIB/USDT:USDT-PERP", result)


class TestBinanceCandlesticks(unittest.TestCase):
    def setUp(self):
        self.parser = BinanceParser()
        infos = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_exchange_info_parser)
        self.spot_info = infos["BTC/USDT:USDT"]

    def test_parse_candlesticks_list(self):
        raw = load("spot_klines")
        result = self.parser.parse_candlesticks(raw, self.spot_info, "spot", "1h")

        self.assertEqual(len(result), 3)
        first = result[0]
        self.assertEqual(first["timestamp"], 1700000000000)
        self.assertEqual(first["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(first["market_type"], "spot")
        self.assertEqual(first["interval"], "1h")
        self.assertEqual(first["open"], 19900.0)
        self.assertEqual(first["high"], 20050.0)
        self.assertEqual(first["low"], 19850.0)
        self.assertEqual(first["close"], 20000.0)
        self.assertEqual(first["base_volume"], 10.0)
        self.assertEqual(first["quote_volume"], 200000.0)
        self.assertEqual(first["contract_volume"], 10.0)

    def test_parse_candlesticks_single_returns_dict(self):
        raw = load("spot_klines")[:1]
        result = self.parser.parse_candlesticks(raw, self.spot_info, "spot", "1h")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["timestamp"], 1700000000000)


class TestBinanceFundingRate(unittest.TestCase):
    def setUp(self):
        self.parser = BinanceParser()
        info = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.futures_exchange_info_parser("linear")
        )
        self.linear_info = info["BTC/USDT:USDT-PERP"]

    def test_parse_current_funding_rate(self):
        raw = load("linear_premium_index")
        result = self.parser.parse_current_funding_rate(raw, self.linear_info)

        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(result["next_funding_time"], 1700028800000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(result["market_type"], "perp")
        self.assertEqual(result["funding_rate"], 0.0001)

    def test_parse_history_funding_rate(self):
        raw = load("linear_funding_rate_history")
        result = self.parser.parse_history_funding_rate(raw, self.linear_info)

        self.assertEqual(len(result), 3)
        for item in result:
            self.assertEqual(item["perp_instrument_id"], "BTC/USDT:USDT-PERP")
            self.assertEqual(item["market_type"], "perp")
            self.assertIsNone(item["realized_rate"])
        self.assertEqual(result[0]["timestamp"], 1699992000000)
        self.assertEqual(result[0]["funding_rate"], 0.0001)


class TestBinanceDerivedPrices(unittest.TestCase):
    def setUp(self):
        self.parser = BinanceParser()
        linear = self.parser.parse_exchange_info(
            load("linear_exchange_info"), self.parser.futures_exchange_info_parser("linear")
        )
        self.linear_info = linear["BTC/USDT:USDT-PERP"]

    def test_parse_index_price_linear(self):
        result = self.parser.parse_index_price(load("linear_premium_index"), self.linear_info, "linear")
        self.assertEqual(result["index_price"], 20010.0)
        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    def test_parse_mark_price_linear(self):
        result = self.parser.parse_mark_price(load("linear_premium_index"), self.linear_info, "linear")
        self.assertEqual(result["mark_price"], 20000.0)

    def test_parse_open_interest_linear(self):
        result = self.parser.parse_open_interest(load("linear_open_interest"), self.linear_info, "linear")
        self.assertEqual(result["oi_contract"], 12345.678)
        self.assertIsNone(result["oi_currency"])
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")


class TestBinanceOrderbook(unittest.TestCase):
    def setUp(self):
        self.parser = BinanceParser()
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_exchange_info_parser)
        self.spot_info = spot["BTC/USDT:USDT"]

    def test_parse_orderbook_sorted(self):
        result = self.parser.parse_orderbook(load("spot_orderbook"), self.spot_info, "spot", depth=None)

        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT")
        # bids sorted descending by price
        bid_prices = [b["price"] for b in result["bids"]]
        self.assertEqual(bid_prices, sorted(bid_prices, reverse=True))
        # asks sorted ascending by price
        ask_prices = [a["price"] for a in result["asks"]]
        self.assertEqual(ask_prices, sorted(ask_prices))

    def test_parse_orderbook_depth(self):
        result = self.parser.parse_orderbook(load("spot_orderbook"), self.spot_info, "spot", depth=2)
        self.assertEqual(len(result["bids"]), 2)
        self.assertEqual(len(result["asks"]), 2)


if __name__ == "__main__":
    unittest.main()
