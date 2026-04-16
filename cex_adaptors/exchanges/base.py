import json
from typing import Optional

import aiohttp

from .auth import BinanceAuth, OkxAuth

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=10, sock_connect=3, sock_read=5)


class BaseClient(object):
    name = None

    def __init__(self) -> None:
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=60,
            )
            self._session = aiohttp.ClientSession(connector=connector, timeout=DEFAULT_TIMEOUT)
        return self._session

    async def _request(self, method: str, url: str, **kwargs):
        if "auth_data" in kwargs:
            # Private endpoint request
            auth_data = kwargs.pop("auth_data")

            # Split into different exchange method
            if self.name == "okx":
                auth = OkxAuth(**auth_data)
                headers = auth.get_private_header(method, url, kwargs.get("params", {}))
                kwargs["headers"] = headers
                if method == "POST":
                    kwargs["data"] = auth.body
                    del kwargs["params"]
            elif self.name == "binance":
                auth = BinanceAuth(**auth_data)
                headers = auth.get_private_header()
                kwargs["params"] = auth.update_params(kwargs.get("params", {}))
                kwargs["headers"] = headers

        session = self._get_session()
        if method == "GET":
            async with session.get(url, **kwargs) as response:
                return await self._handle_response(response)
        elif method == "POST":
            async with session.post(url, **kwargs) as response:
                return await self._handle_response(response)
        else:
            raise ValueError(f"Invalid method: {method}")

    async def _handle_response(self, response: aiohttp.ClientResponse):
        if response.status == 200:
            try:
                return await response.json()
            except Exception as e:
                print(e)
                return json.loads(await response.text())
        else:
            raise Exception(f"Error {response.status} {response.reason} {await response.text()}")

    async def _get(self, url: str, **kwargs):
        return await self._request("GET", url, **kwargs)

    async def _post(self, url: str, **kwargs):
        return await self._request("POST", url, **kwargs)

    async def close(self):
        if self._session is not None and not self._session.closed:
            await self._session.close()
