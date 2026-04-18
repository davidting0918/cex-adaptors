import unittest

from cex_adaptors.parsers.okx import OkxParser
from tests.unit.okx._fixtures import load


class TestOkxExchangeInfo(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()

    def test_parse_spot_exchange_info(self):
        raw = load("spot_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.spot_margin_exchange_info_parser)

        self.assertIn("BTC/USDT:USDT", result)
        self.assertIn("ETH/USDT:USDT", result)

        btc = result["BTC/USDT:USDT"]
        self.assertTrue(btc["active"])
        self.assertTrue(btc["is_spot"])
        self.assertFalse(btc["is_margin"])  # margin flag is set via combine step
        self.assertFalse(btc["is_perp"])
        self.assertFalse(btc["is_futures"])
        self.assertTrue(btc["is_linear"])
        self.assertFalse(btc["is_inverse"])
        self.assertEqual(btc["base"], "BTC")
        self.assertEqual(btc["quote"], "USDT")
        self.assertEqual(btc["settle"], "USDT")
        self.assertEqual(btc["contract_size"], 1)
        self.assertEqual(btc["multiplier"], 1)
        self.assertEqual(btc["listing_time"], 1606468572000)
        self.assertEqual(btc["raw_data"]["instId"], "BTC-USDT")

        # suspend -> active False but still present
        self.assertFalse(result["SOL/USDT:USDT"]["active"])

    def test_parse_margin_exchange_info_alone(self):
        raw = load("margin_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.spot_margin_exchange_info_parser)

        btc = result["BTC/USDT:USDT"]
        self.assertTrue(btc["is_margin"])
        self.assertFalse(btc["is_spot"])
        self.assertEqual(btc["leverage"], 10)

    def test_combine_spot_margin_exchange_info(self):
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_margin_exchange_info_parser)
        margin = self.parser.parse_exchange_info(
            load("margin_exchange_info"), self.parser.spot_margin_exchange_info_parser
        )
        combined = self.parser.combine_spot_margin_exchange_info(spot, margin)

        # BTC is both spot and margin
        self.assertTrue(combined["BTC/USDT:USDT"]["is_spot"])
        self.assertTrue(combined["BTC/USDT:USDT"]["is_margin"])
        self.assertEqual(combined["BTC/USDT:USDT"]["leverage"], 10)

        # ETH is spot but not margin (not in margin fixture)
        self.assertTrue(combined["ETH/USDT:USDT"]["is_spot"])
        self.assertFalse(combined["ETH/USDT:USDT"]["is_margin"])

    def test_parse_perp_exchange_info(self):
        raw = load("perp_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.futures_perp_exchange_info_parser)

        perp = result["BTC/USDT:USDT-PERP"]
        self.assertTrue(perp["is_perp"])
        self.assertFalse(perp["is_futures"])
        self.assertTrue(perp["is_linear"])
        self.assertFalse(perp["is_inverse"])
        self.assertEqual(perp["base"], "BTC")
        self.assertEqual(perp["quote"], "USDT")
        self.assertEqual(perp["settle"], "USDT")
        self.assertEqual(perp["contract_size"], 0.01)
        self.assertEqual(perp["multiplier"], 1)
        self.assertEqual(perp["listing_time"], 1569398400000)
        self.assertIsNone(perp["expiration_time"])

        # Inverse perp: base/quote swapped; settle == contract-value currency's settle
        inverse = result["BTC/USD:BTC-PERP"]
        self.assertTrue(inverse["is_perp"])
        self.assertTrue(inverse["is_inverse"])
        self.assertFalse(inverse["is_linear"])
        self.assertEqual(inverse["base"], "BTC")
        self.assertEqual(inverse["quote"], "USD")
        self.assertEqual(inverse["settle"], "BTC")
        self.assertEqual(inverse["contract_size"], 100.0)

    def test_parse_futures_exchange_info(self):
        raw = load("futures_exchange_info")
        result = self.parser.parse_exchange_info(raw, self.parser.futures_perp_exchange_info_parser)

        futures_id = "BTC/USDT:USDT-240329"
        self.assertIn(futures_id, result)
        futures = result[futures_id]
        self.assertTrue(futures["is_futures"])
        self.assertFalse(futures["is_perp"])
        self.assertEqual(futures["expiration_time"], 1711699200000)
        self.assertTrue(futures["is_linear"])

        inverse_futures = result["BTC/USD:BTC-240329"]
        self.assertTrue(inverse_futures["is_futures"])
        self.assertTrue(inverse_futures["is_inverse"])
        self.assertEqual(inverse_futures["settle"], "BTC")


class TestOkxTicker(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_margin_exchange_info_parser)
        margin = self.parser.parse_exchange_info(
            load("margin_exchange_info"), self.parser.spot_margin_exchange_info_parser
        )
        self.spot_info = self.parser.combine_spot_margin_exchange_info(spot, margin)
        self.perp_info = self.parser.parse_exchange_info(
            load("perp_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )
        self.futures_info = self.parser.parse_exchange_info(
            load("futures_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )

    def test_parse_ticker_spot(self):
        info = self.spot_info["BTC/USDT:USDT"]
        ticker = self.parser.parse_ticker(load("spot_ticker"), "spot", info)

        self.assertEqual(ticker["timestamp"], 1700086400000)
        self.assertEqual(ticker["instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(ticker["market_type"], "spot")
        self.assertEqual(ticker["open"], 19900.0)
        self.assertEqual(ticker["high"], 20100.0)
        self.assertEqual(ticker["low"], 19800.0)
        self.assertEqual(ticker["last"], 20000.0)
        # spot uses vol24h for base_volume, volCcy24h for quote_volume
        self.assertEqual(ticker["base_volume"], 1000.0)
        self.assertEqual(ticker["quote_volume"], 20000000.0)
        # price_change = open - last = 19900 - 20000 = -100
        self.assertEqual(ticker["price_change"], -100.0)

    def test_parse_ticker_perp(self):
        info = self.perp_info["BTC/USDT:USDT-PERP"]
        ticker = self.parser.parse_ticker(load("perp_ticker"), "perp", info)

        self.assertEqual(ticker["instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(ticker["market_type"], "perp")
        # perp uses volCcy24h for base_volume (= contracts * ctVal in base ccy)
        self.assertEqual(ticker["base_volume"], 100.0)
        # quote_volume = volCcy24h * (last + open24h) / 2 = 100 * (20000 + 19900) / 2
        self.assertEqual(ticker["quote_volume"], 1995000.0)

    def test_parse_ticker_inverse_perp(self):
        info = self.perp_info["BTC/USD:BTC-PERP"]
        ticker = self.parser.parse_ticker(load("inverse_perp_ticker"), "perp", info)

        self.assertEqual(ticker["instrument_id"], "BTC/USD:BTC-PERP")
        self.assertEqual(ticker["base_volume"], 50.0)

    def test_parse_tickers_spot(self):
        infos = {**self.spot_info, **self.perp_info, **self.futures_info}
        result = self.parser.parse_tickers(load("spot_tickers"), "spot", infos)

        self.assertEqual(set(result.keys()), {"BTC/USDT:USDT", "ETH/USDT:USDT"})
        self.assertEqual(result["BTC/USDT:USDT"]["last"], 20000.0)

    def test_parse_tickers_perp(self):
        infos = {**self.spot_info, **self.perp_info, **self.futures_info}
        result = self.parser.parse_tickers(load("perp_tickers"), "perp", infos)

        self.assertIn("BTC/USDT:USDT-PERP", result)
        self.assertIn("ETH/USDT:USDT-PERP", result)
        self.assertIn("BTC/USD:BTC-PERP", result)

    def test_parse_tickers_futures(self):
        infos = {**self.spot_info, **self.perp_info, **self.futures_info}
        result = self.parser.parse_tickers(load("futures_tickers"), "futures", infos)

        self.assertIn("BTC/USDT:USDT-240329", result)


class TestOkxCandlesticks(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_margin_exchange_info_parser)
        self.spot_info = spot["BTC/USDT:USDT"]
        perp = self.parser.parse_exchange_info(
            load("perp_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )
        self.perp_info = perp["BTC/USDT:USDT-PERP"]

    def test_parse_candlesticks_spot_list(self):
        raw = load("spot_candles")
        result = self.parser.parse_candlesticks(raw, self.spot_info, "1h")

        self.assertEqual(len(result), 3)
        first = result[0]
        self.assertEqual(first["timestamp"], 1700007200000)
        self.assertEqual(first["instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(first["market_type"], "spot")
        self.assertEqual(first["interval"], "1h")
        self.assertEqual(first["open"], 20050.0)
        self.assertEqual(first["high"], 20100.0)
        self.assertEqual(first["low"], 20020.0)
        self.assertEqual(first["close"], 20080.0)
        # spot: vol[5] is base ccy, volCcyQuote[7] is quote
        self.assertEqual(first["base_volume"], 30.0)
        self.assertEqual(first["quote_volume"], 600000.0)
        self.assertEqual(first["contract_volume"], 30.0)

    def test_parse_candlesticks_perp_list(self):
        raw = load("perp_candles")
        result = self.parser.parse_candlesticks(raw, self.perp_info, "1h")

        self.assertEqual(len(result), 3)
        first = result[0]
        self.assertEqual(first["instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(first["market_type"], "perp")
        # perp: vol[5] is contracts, volCcy[6] is base ccy, volCcyQuote[7] is quote
        self.assertEqual(first["contract_volume"], 300.0)
        self.assertEqual(first["base_volume"], 3.0)
        self.assertEqual(first["quote_volume"], 60000.0)

    def test_parse_candlesticks_single_returns_dict(self):
        raw = load("spot_candles_single")
        result = self.parser.parse_candlesticks(raw, self.spot_info, "1h")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["timestamp"], 1700000000000)


class TestOkxFundingRate(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()
        perp = self.parser.parse_exchange_info(
            load("perp_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )
        self.perp_info = perp["BTC/USDT:USDT-PERP"]

    def test_parse_current_funding_rate(self):
        result = self.parser.parse_current_funding_rate(load("current_funding_rate"), self.perp_info)

        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(result["next_funding_time"], 1700028800000)
        self.assertEqual(result["instrument_id"], "BTC/USDT:USDT-PERP")
        self.assertEqual(result["market_type"], "perp")
        self.assertEqual(result["funding_rate"], 0.0001)

    def test_parse_funding_rates_history(self):
        result = self.parser.parse_funding_rates(load("history_funding_rate"), self.perp_info)

        self.assertEqual(len(result), 3)
        for item in result:
            self.assertEqual(item["instrument_id"], "BTC/USDT:USDT-PERP")
            self.assertEqual(item["market_type"], "perp")
        # fixture is newest-first (API convention)
        self.assertEqual(result[0]["timestamp"], 1700020800000)
        self.assertEqual(result[0]["funding_rate"], 0.0003)
        self.assertEqual(result[0]["realized_rate"], 0.0003)


class TestOkxDerivedPrices(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()
        perp = self.parser.parse_exchange_info(
            load("perp_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )
        self.perp_info = perp["BTC/USDT:USDT-PERP"]
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_margin_exchange_info_parser)
        self.spot_info = spot["BTC/USDT:USDT"]

    def test_parse_index_price(self):
        result = self.parser.parse_index_price(load("index_ticker"), self.perp_info)

        self.assertEqual(result["index_price"], 20010.0)
        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    def test_parse_mark_price(self):
        result = self.parser.parse_mark_price(load("mark_price"), self.perp_info)

        self.assertEqual(result["mark_price"], 20005.0)
        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    def test_parse_open_interest_single_returns_dict(self):
        perp = self.parser.parse_exchange_info(
            load("perp_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )
        result = self.parser.parse_open_interest(load("open_interest_single"), perp)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["oi_contract"], 123456.0)
        self.assertEqual(result["oi_currency"], 1234.56)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT-PERP")

    def test_parse_open_interest_market_returns_list(self):
        perp = self.parser.parse_exchange_info(
            load("perp_exchange_info"), self.parser.futures_perp_exchange_info_parser
        )
        result = self.parser.parse_open_interest(load("open_interest_market"), perp)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        ids = {item["perp_instrument_id"] for item in result}
        self.assertEqual(ids, {"BTC/USDT:USDT-PERP", "ETH/USDT:USDT-PERP"})

    def test_parse_last_price(self):
        result = self.parser.parse_last_price(load("spot_ticker"), self.spot_info)

        self.assertEqual(result["last_price"], 20000.0)
        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(result["market_type"], "spot")


class TestOkxOrderbook(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()
        spot = self.parser.parse_exchange_info(load("spot_exchange_info"), self.parser.spot_margin_exchange_info_parser)
        self.spot_info = spot["BTC/USDT:USDT"]

    def test_parse_orderbook_unwraps_levels(self):
        result = self.parser.parse_orderbook(load("orderbook"), self.spot_info)

        self.assertEqual(result["perp_instrument_id"], "BTC/USDT:USDT")
        self.assertEqual(result["timestamp"], 1700000000000)
        self.assertEqual(len(result["asks"]), 3)
        self.assertEqual(len(result["bids"]), 3)

        # Each level has price, volume, order_number
        self.assertEqual(result["asks"][0]["price"], 20001.0)
        self.assertEqual(result["asks"][0]["volume"], 0.5)
        self.assertEqual(result["asks"][0]["order_number"], 2)
        self.assertEqual(result["bids"][0]["price"], 19999.0)
        self.assertEqual(result["bids"][0]["volume"], 0.75)
        self.assertEqual(result["bids"][0]["order_number"], 2)


class TestOkxCheckResponse(unittest.TestCase):
    def setUp(self):
        self.parser = OkxParser()

    def test_check_response_success(self):
        resp = {"code": "0", "msg": "", "data": [{"foo": "bar"}]}
        result = self.parser.check_response(resp)
        self.assertEqual(result["code"], 200)
        self.assertEqual(result["data"], [{"foo": "bar"}])

    def test_check_response_error_raises(self):
        resp = {"code": "51000", "msg": "parameter error", "data": []}
        with self.assertRaises(ValueError):
            self.parser.check_response(resp)

    def test_get_interval_valid(self):
        self.assertEqual(self.parser.get_interval("1h"), "1H")
        self.assertEqual(self.parser.get_interval("1d"), "1D")
        self.assertEqual(self.parser.get_interval("5m"), "5m")

    def test_get_interval_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.parser.get_interval("7h")


if __name__ == "__main__":
    unittest.main()
