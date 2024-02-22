# cex_services
This package is designed for interacting with many crypto centralized exchanges. Currently only support **public API endpoints** in Version `1.0.x`. Will add private API endpoints in version `2.0.x`.

## Getting started
use ```pip install cex-services``` to install the package.

## Usage
After installing the package, you can use the following code start the service.
**All the codes is written in async mode.**
```python
from cex_services.binance import Binance
import asyncio
async def main():
    binance = await Binance.create()
    # get exchange info
    print(await binance.get_exchange_info())

    # get all tickers
    print(await binance.get_tickers())

if __name__ == "__main__":
    asyncio.run(main())
```

## Supported Exchanges
| Exchange | Version | Public API | Private API |
|----------|---------|------------|-------------|
| Binance  | 1.0.1   | Yes        | No          |
| OKX      | 1.0.1   | Yes        | No          |
| Bybit    | 1.0.1   | Yes        | No          |
| Gate.io  | 1.0.1   | Yes        | No          |
| Kucoin   | 1.0.1   | Yes        | No          |
| HTX      | 1.0.1   | Yes        | No          |

## Supported API endpoints
| Endpoint            | Exchanges                                         |
|---------------------|---------------------------------------------------|
| `get_exchange_info` | Binance, OKX, Bybit, Gate.io, Kucoin, HTX, Bitget |
| `get_tickers`       | Binance, OKX, Bybit, Gate.io, Kucoin, HTX, Bitget |
| `get_klines`        | Binance, OKX                                      |
                                    |


## Unified function parameters and output format
<details>
<summary><strong>1. <code>get_exchange_info</code></strong></summary>

#### Input
| Parameter     | Required | Default | Description                                  |
|---------------|----------|---------|----------------------------------------------|
| `market_type` | No       | `None`  | should be value in `spot`, `perp`, `futures` |

#### Output (Nested Dictionary)
| Field             | Type    | Description                                                                                                                                     |
|-------------------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `instrument_id`   | `str`   | The key of the dictionary. Format: `{base}/{quote}:{settle}-{delivery}`                                                                         |
| `active`          | `bool`  | Indicates whether this instrument is currently tradable.                                                                                        |
| `is_spot`         | `bool`  | Indicates whether this instrument is in the spot market.                                                                                        |
| `is_margin`       | `bool`  | Indicates whether margin trading is available for this instrument.                                                                              |
| `is_futures`      | `bool`  | Indicates whether this instrument is in the futures market.                                                                                     |
| `is_perp`         | `bool`  | Indicates whether this instrument is in the perpetual market.                                                                                   |
| `is_linear`       | `bool`  | Returns `True` if this instrument is settled in a stable currency.                                                                              |
| `is_inverse`      | `bool`  | Returns `True` if this instrument is settled in a coin.                                                                                         |
| `symbol`          | `str`   | The unified symbol of the trading pair. Format: `{base}/{quote}`                                                                                |
| `base`            | `str`   | The base currency of the instrument.                                                                                                            |
| `quote`           | `str`   | The quote currency of the instrument.                                                                                                           |
| `settle`          | `str`   | The settlement currency for the instrument.                                                                                                     |
| `multiplier`      | `int`   | The multiplier, typically indicating the quantity of the base currency included in one instrument unit.                                         |
| `leverage`        | `float` | The maximum leverage available for trading.                                                                                                     |
| `listing_time`    | `int`   | The listing time, represented as a 13-digit integer.                                                                                            |
| `expiration_time` | `int`   | The expiration time, represented as a 13-digit integer.                                                                                         |
| `contract_size`   | `float` | The contract size, with a default value of `1`. Indicates the amount of base currency per contract, usually applicable to `perp` and `futures`. |
| `tick_size`       | `float` | The minimum increment by which the price can change.                                                                                            |
| `min_order_size`  | `float` | The minimum size for an order.                                                                                                                  |
| `max_order_size`  | `float` | The maximum size for an order.                                                                                                                  |
| `raw_data`        | `dict`  | The unprocessed raw data associated with the instrument.                                                                                        |
</details>

<details>
<summary><strong>2. <code>get_tickers</code></strong></summary>

#### Input
| Parameter     | Required | Default | Description                                  |
|---------------|----------|---------|----------------------------------------------|
| `market_type` | No       | `None`  | should be value in `spot`, `perp`, `futures` |

#### Output (nested dict)
| Field                  | Type    | Description                                                             |
|------------------------|---------|-------------------------------------------------------------------------|
| `instrument_id`        | `str`   | The key of the dictionary. Format: `{base}/{quote}:{settle}-{delivery}` |
| `symbol`               | `str`   | The raw symbol from the exchange.                                       |
| `open_time`            | `int`   | The opening time of the trading pair, in 13 digits.                     |
| `close_time`           | `int`   | The closing time of the trading pair, in 13 digits.                     |
| `open`                 | `float` | The opening price of the trading pair in 24hr.                          |
| `high`                 | `float` | The highest price of the trading pair in 24hr.                          |
| `low`                  | `float` | The lowest price of the trading pair in 24hr.                           |
| `last_price`           | `float` | The last price of the trading pair.                                     |
| `base_volume`          | `float` | The trading volume of the base currency in 24hr.                        |
| `quote_volume`         | `float` | The trading volume of the quote currency in 24hr.                       |
| `price_change`         | `float` | The price change of the trading pair in 24hr.                           |
| `price_change_percent` | `float` | The price change percentage of the trading pair in 24hr.                |
| `raw_data`             | `dict`  | The unprocessed raw data associated with the trading pair.              |

</details>
