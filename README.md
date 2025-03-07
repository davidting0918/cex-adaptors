# cex-adaptors
This package is designed for interacting with many crypto centralized exchanges. Currently only support **public API endpoints** in Version `1.0.x`. Will add private API endpoints in version `2.0.x`.

## Getting started
use ```pip install cex-adaptor``` to install the package.

## Usage
After installing the package, you can use the following code start using the adaptors.
**All the codes is written in async mode.**
```python
from cex_adaptors.binance import Binance
import asyncio
async def main():
    binance = Binance()
    await binance.sync_exchange_info()
    # get exchange info
    print(await binance.get_exchange_info())

    # get all tickers
    print(await binance.get_tickers())

if __name__ == "__main__":
    asyncio.run(main())
```

## Unified function parameters and output format
<details>
<summary><strong>1. <code>get_exchange_info</code></strong></summary>

#### Input
#### Output (Nested Dictionary)
</details>

<details>
<summary><strong>2. <code>get_tickers</code></strong></summary>

#### Input
```json
{
    "market": "spot"  // must be in "spot", "perp", "futures". If `null` will return all tickers on the exchange
}
```

#### Output (nested dict)
```json
{
    "BTC/USDT:USDT" : {
        "timestamp": 1630000000000,
        "instrument_id": "BTC/USDT:USDT",
        "open_time": 1630000000000,
        "close_time": 1630000000000,
        "open": 10000.0,
        "high": 11000.0,
        "low": 9000.0,
        "last": 10000.0,
        "base_volume": 1000.0,
        "quote_volume": 10000000.0,
        "price_change": 0.0,  // must in quote currency
        "price_change_percent": 0.01, // must in percentage, if 0.01 means 1%,
        "raw_data": {},
    },
  // many instrument ticker
}
```
</details>


<details>
<summary><strong>3. <code>get_ticker</code></strong></summary>

#### Input
```json
{
    "instrument_id": "BTC/USDT:USDT"  // must be perp_instrument_id in exchange's exchange info
}
```

#### Output (Dictionary)
```json
{
    "BTC/USDT:USDT" : {
        "timestamp": 1630000000000,
        "instrument_id": "BTC/USDT:USDT",
        "open_time": 1630000000000,
        "close_time": 1630000000000,
        "open": 10000.0,
        "high": 11000.0,
        "low": 9000.0,
        "last": 10000.0,
        "base_volume": 1000.0,
        "quote_volume": 10000000.0,
        "price_change": 0.0,  // must in quote currency
        "price_change_percent": 0.01, // must in percentage, if 0.01 means 1%,
        "raw_data": {},
    }
}
```
</details>

<details>
<summary><strong>4. <code>get_current_candlestick</code></strong></summary>

#### Input
```json
{
  "instrument_id": "BTC/USDT:USDT-PERP", // required
  "interval": "1m", // required, vary from different exchanges
}
```

#### Output (List of Dictionary)
```json
{
  "timestamp": 1629350400000, // timestamp in millisecond
  "interval": "1m",
  "instrument_id": "BTC/USDT:USDT-PERP",
  "market_type": "perp", // "spot", "futures", "perp
  "open": 10000.0, // open price
  "high": 10100, // high price
  "low": 9900, // low price
  "close": 10050, // close price
  "base_volume": 1000, // volume in base currency
  "quote_volume": 10000000, // quote volume
  "contract_volume": 1000, // contract volume
  "raw_data": {} // raw data from exchange
}
```

</details>

<details>
<summary><strong>5. <code>get_history_candlesticks</code></strong></summary>

#### Input
```json
{
  "instrument_id": "BTC/USDT:USDT-PERP", // required
  "interval": "1m", // required, vary from different exchanges
  "start": 1629350400000, // optional, timestamp in millisecond
  "end": 1629350400000, // optional, timestamp in millisecond
  "num": 100, // optional, number of data to return
}
```

#### Output (List of Dictionary)
```json
[
  {
    "timestamp": 1629350400000, // timestamp in millisecond
    "interval": "1m",
    "instrument_id": "BTC/USDT:USDT-PERP",
    "market_type": "perp", // "spot", "futures", "perp
    "open": 10000.0, // open price
    "high": 10100, // high price
    "low": 9900, // low price
    "close": 10050, // close price
    "base_volume": 1000, // volume in base currency
    "quote_volume": 10000000, // quote volume
    "contract_volume": 1000, // contract volume, if is spot then will equal to base_volume
    "raw_data": {} // raw data from exchange
  },
  // many history candlesticks data
]
```


</details>

<details>
<summary><strong>6. <code>get_current_funding_rate</code></strong></summary>

#### Input
```json
{
  "instrument_id": "BTC/USDT:USDT-PERP", // required, funding rate only support futures and perp
}
```
#### Output
```json
{
  "BTC/USDT:USDT-PERP": {
    "timestamp": 1629350400000, // timestamp in millisecond
    "next_funding_time": 1629350400000, // timestamp in milliseconds
    "instrument_id": "BTC/USDT:USDT-PERP",
    "market_type": "perp",
    "funding_rate": 0.001, // funding rate in percentage, 0.01 means 1%
    "raw_data": {} // raw data from exchange
  }
}
```

</details>

<details>
<summary><strong>7. <code>get_history_funding_rate</code></strong></summary>

#### Input
```json
{
  "instrument_id": "BTC/USDT:USDT-PERP", // required, funding rate only support futures and perp
  "start": 1629350400000, // optional, timestamp in millisecond
  "end": 1629350400000, // optional, timestamp in millisecond
  "num": 100, // optional, number of data to return
}
```
**(`start`, `end`)** or **`num`** must be provided, if both provided, use **start** and **end**.

#### Output
```json
[
  {
    "timestamp": 1629350400000, // timestamp in millisecond
    "instrument_id": "BTC/USDT:USDT-PERP",
    "market_type": "perp",
    "funding_rate": 0.001, // funding rate in percentage, 0.01 means 1%
    "realized_rate": 0.001, // realized rate in percentage, 0.01 means 1%
    "raw_data": {} // raw data from exchange
  }, // many history funding rate data
]
```