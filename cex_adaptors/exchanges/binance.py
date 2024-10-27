import hashlib
import hmac
import json
import time

import aiohttp

from .base import PublicClient


class BinancePrivateClient(object):
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

        self._session = aiohttp.ClientSession()

    def get_private_header(self):
        headers = {"X-MBX-APIKEY": self.api_key}
        return headers

    def update_params(self, params: dict):
        params["timestamp"] = int(time.time() * 1000)

        payload = "&".join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(self.api_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    async def _get(self, url: str, **kwargs):
        return await self._request("GET", url, **kwargs)

    async def _post(self, url: str, **kwargs):
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs):
        kwargs["params"] = self.update_params(kwargs.get("params", {}))
        kwargs["headers"] = self.get_private_header()

        if method == "GET":
            async with self._session.get(url, **kwargs) as response:
                return await self._handle_response(response)
        elif method == "POST":
            async with self._session.post(url, **kwargs) as response:
                return await self._handle_response(response)

    async def _handle_response(self, response: aiohttp.ClientResponse):
        if response.status == 200:
            try:
                return await response.json()
            except Exception as e:
                print(e)
                return json.loads(await response.text())
        else:
            raise Exception(f"Error {response.status} {response.reason} {await response.text()}")

    async def close(self):
        await self._session.close()


class BinanceSpot(PublicClient):
    BASE_ENDPOINT = "https://api{}.binance.com"
    name = "binance"

    def __init__(self, api_key: str, api_secret: str, api_version: int = 3):
        super().__init__()
        self.base_endpoint = self.BASE_ENDPOINT.format(api_version)

        self.private_client = BinancePrivateClient(api_key, api_secret)

    async def _get_exchange_info(self):
        return await self._get(self.base_endpoint + "/api/v3/exchangeInfo")

    async def _get_ticker(self, symbol: str):
        return await self._get(self.base_endpoint + "/api/v3/ticker/24hr", params={"symbol": symbol})

    async def _get_tickers(self):
        return await self._get(self.base_endpoint + "/api/v3/ticker/24hr")

    async def _get_klines(
        self,
        symbol: str,
        interval: str,
        startTime: int = None,
        endTime: int = None,
        limit: int = 500,
        timeZone: str = "0",
    ):
        params = {"symbol": symbol, "interval": interval, "limit": limit, "timeZone": timeZone}
        if startTime:
            params["startTime"] = startTime
        if endTime:
            params["endTime"] = endTime
        return await self._get(self.base_endpoint + "/api/v3/klines", params=params)

    async def _get_orderbook(self, symbol: str, limit: int = 5000):
        params = {k: v for k, v in {"symbol": symbol, "limit": limit}.items() if v}
        return await self._get(self.base_endpoint + "/api/v3/depth", params=params)

    async def _get_margin_price_index(self, symbol: str):
        params = {"symbol": symbol}
        return await self.private_client._get(self.base_endpoint + "/sapi/v1/margin/priceIndex", params=params)

    async def _get_recent_trades_list(self, symbol: str, limit: int = 500):
        params = {k: v for k, v in {"symbol": symbol, "limit": limit}.items() if v}
        return await self._get(self.base_endpoint + "/api/v3/trades", params=params)

    # Private endpoint
    async def _get_account_info(self):
        return await self.private_client._get(self.base_endpoint + "/api/v3/account")

    async def _get_margin_account_info(self):
        return await self.private_client._get(self.base_endpoint + "/sapi/v1/margin/account")

    async def _get_order_book(self, symbol: str, limit: int = 5000):
        params = {"symbol": symbol, "limit": limit}
        return await self._get(self.base_endpoint + "/api/v3/depth", params=params)

    async def _place_margin_order(
        self,
        symbol: str,
        side: str,
        type: str,
        quantity: float = None,
        price: float = None,
        quoteOrderQty: float = None,
    ):
        params = {
            k: v
            for k, v in {
                "symbol": symbol,
                "side": side,
                "type": type,
                "quantity": quantity,
                "price": price,
                "quoteOrderQty": quoteOrderQty,
            }.items()
            if v
        }

        return await self.private_client._post(self.base_endpoint + "/sapi/v1/margin/order", params=params)


class BinanceLinear(PublicClient):
    BASE_ENDPOINT = "https://fapi.binance.com"

    def __init__(self) -> None:
        super().__init__()
        self.linear_base_endpoint = self.BASE_ENDPOINT

    async def _get_exchange_info(self):
        return await self._get(self.linear_base_endpoint + "/fapi/v1/exchangeInfo")

    async def _get_ticker(self, symbol: str):
        return await self._get(self.linear_base_endpoint + "/fapi/v1/ticker/24hr", params={"symbol": symbol})

    async def _get_tickers(self):
        return await self._get(self.linear_base_endpoint + "/fapi/v1/ticker/24hr")

    async def _get_klines(
        self, symbol: str, interval: str, startTime: int = None, endTime: int = None, limit: int = 500
    ):
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if startTime:
            params["startTime"] = startTime
        if endTime:
            params["endTime"] = endTime
        return await self._get(self.linear_base_endpoint + "/fapi/v1/klines", params=params)

    async def _get_funding_rate_history(
        self, symbol: str, startTime: int = None, endTime: int = None, limit: int = 1000
    ):
        params = {
            k: v
            for k, v in {
                "symbol": symbol,
                "startTime": startTime,
                "endTime": endTime,
                "limit": limit,
            }.items()
            if v
        }
        return await self._get(self.linear_base_endpoint + "/fapi/v1/fundingRate", params=params)

    async def _get_index_and_mark_price(self, symbol: str):
        params = {"symbol": symbol}
        return await self._get(self.linear_base_endpoint + "/fapi/v1/premiumIndex", params=params)

    async def _get_open_interest(self, symbol: str):
        params = {"symbol": symbol}
        return await self._get(self.linear_base_endpoint + "/fapi/v1/openInterest", params=params)

    async def _get_open_interest_statistics(
        self, symbol: str, period: str, limit: int = 500, startTime: int = None, endTime: int = None
    ):
        params = {
            k: v
            for k, v in {
                "symbol": symbol,
                "period": period,
                "limit": limit,
                "startTime": startTime,
                "endTime": endTime,
            }.items()
            if v
        }
        return await self._get(self.linear_base_endpoint + "/fapi/v1/openInterestHist", params=params)

    async def _get_order_book(self, symbol: str, limit: int = 1000):
        params = {"symbol": symbol, "limit": limit}
        return await self._get(self.linear_base_endpoint + "/fapi/v1/depth", params=params)


class BinanceInverse(PublicClient):
    BASE_ENDPOINT = "https://dapi.binance.com"

    def __init__(self) -> None:
        super().__init__()
        self.inverse_base_endpoint = self.BASE_ENDPOINT

    async def _get_exchange_info(self):
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/exchangeInfo")

    async def _get_ticker(self, symbol: str):
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/ticker/24hr", params={"symbol": symbol})

    async def _get_tickers(self):
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/ticker/24hr")

    async def _get_klines(
        self, symbol: str, interval: str, startTime: int = None, endTime: int = None, limit: int = 500
    ):
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if startTime:
            params["startTime"] = startTime
        if endTime:
            params["endTime"] = endTime
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/klines", params=params)

    async def _get_funding_rate_history(
        self, symbol: str, startTime: int = None, endTime: int = None, limit: int = 1000
    ):
        params = {
            k: v
            for k, v in {
                "symbol": symbol,
                "startTime": startTime,
                "endTime": endTime,
                "limit": limit,
            }.items()
            if v
        }
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/fundingRate", params=params)

    async def _get_index_and_mark_price(self, symbol: str = None, pair: str = None):
        params = {
            k: v
            for k, v in {
                "symbol": symbol,
                "pair": pair,
            }.items()
            if v
        }
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/premiumIndex", params=params)

    async def _get_open_interest(self, symbol: str):
        params = {"symbol": symbol}
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/openInterest", params=params)

    async def _get_open_interest_statistics(
        self, symbol: str, contractType: str, period: str, limit: int = 500, startTime: int = None, endTime: int = None
    ):
        params = {
            k: v
            for k, v in {
                "symbol": symbol,
                "contractType": contractType,
                "period": period,
                "limit": limit,
                "startTime": startTime,
                "endTime": endTime,
            }.items()
            if v
        }
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/openInterestHist", params=params)

    async def _get_order_book(self, symbol: str, limit: int = 1000):
        params = {"symbol": symbol, "limit": limit}
        return await self._get(self.inverse_base_endpoint + "/dapi/v1/depth", params=params)
