# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`cex-adaptors` is a Python package (published to PyPI) that wraps centralized crypto exchange APIs
behind a single unified async interface. Supported exchanges: Binance, OKX, Bybit, Bitget, Bitmex,
Gate.io, HTX, KuCoin, Woo. Version `1.0.x` covers public endpoints only; private endpoints are
planned for `2.0.x`. Target runtime is Python 3.13 and **all public methods are `async`**.

## Common commands

```bash
# Install runtime + dev deps
pip install -r requirements.txt
pip install -r test_requirements.txt

# Run the unit suite (offline, fixture-driven — this is what CI runs)
PYTHONPATH=. python3 -m unittest discover tests/unit -v

# Run a single unit test case
PYTHONPATH=. python3 -m unittest tests.unit.binance.test_parser.TestBinanceTicker

# Run live integration smoke tests (opt-in, hits real exchange APIs)
RUN_INTEGRATION_TESTS=1 PYTHONPATH=. python3 -m unittest discover tests/integration -v

# Lint / format (pre-commit enforces these; runs black, isort, flake8, yamllint)
pre-commit run --all-files

# Build and publish (see dev.md) — bump version in setup.py first
python3 setup.py sdist bdist_wheel
twine upload dist/*
```

CI runs `pre-commit run --all-files` and `python3 -m unittest discover tests/unit` on every
push/PR (`.github/workflows/`). The `tests/unit` suite is fixture-driven and never hits the
network — exchange HTTP clients are mocked with `unittest.mock.AsyncMock`. The `tests/integration`
suite hits real public endpoints and is gated by `RUN_INTEGRATION_TESTS=1`; run it locally (or in
a nightly workflow) to catch exchange-side API drift.

## Architecture

Each exchange is implemented as **three stacked classes**. Adding or modifying an exchange means
touching all three layers:

1. `cex_adaptors/exchanges/{name}.py` — a `{Name}Unified` class extending `BaseClient`
   ([cex_adaptors/exchanges/base.py](cex_adaptors/exchanges/base.py)). This layer owns the raw HTTP
   calls and auth headers. Private `_get_*` / `_post_*` methods here return the exchange's raw JSON.
   Auth is centralized in [cex_adaptors/exchanges/auth.py](cex_adaptors/exchanges/auth.py) and
   dispatched by exchange `name` inside `BaseClient._request`.
2. `cex_adaptors/parsers/{name}.py` — a `{Name}Parser` class extending `Parser`
   ([cex_adaptors/parsers/base.py](cex_adaptors/parsers/base.py)). Parsers convert raw exchange
   responses into the unified dict schemas (Ticker, Kline, ExchangeInfo, FundingRate, …). Parsers
   are declarative: most parse a raw record with a `{field: callable}` dict passed into
   `Parser.get_result_with_parser`. The base class holds the market-type constants
   (`SPOT_TYPES`, `FUTURES_TYPES`, `PERPETUAL_TYPES`, etc.) used across exchanges.
3. `cex_adaptors/{name}.py` — the user-facing adaptor (e.g. `Okx`, `Binance`). Inherits the
   `Unified` HTTP class, owns a parser instance, caches `self.exchange_info`, and exposes the
   unified async API (`get_exchange_info`, `get_tickers`, `get_ticker`,
   `get_current_candlestick`, `get_history_candlesticks`, `get_current_funding_rate`,
   `get_history_funding_rate`). Each adaptor also defines its own `market_type_map` /
   `_market_type_map` translating between unified tokens (`spot`, `margin`, `futures`, `perp`) and
   the exchange's native naming.

### Unified vocabulary (important)

- **Unified `instrument_id` format** — spot/margin: `BASE/QUOTE:SETTLE` (e.g. `BTC/USDT:USDT`);
  perp/futures: `BASE/QUOTE:SETTLE-PERP` (e.g. `BTC/USDT:USDT-PERP`). Inverse contracts swap base
  and settle. The adaptor rejects instrument ids not present in its cached `exchange_info`.
- **Lifecycle** — construct the adaptor, then `await exchange.sync_exchange_info()` before calling
  any other method that resolves instrument ids. Always `await exchange.close()` at shutdown; the
  underlying `aiohttp.ClientSession` is created in `BaseClient.__init__`.
- **`raw_data`** — every unified record includes the untouched exchange payload under `raw_data` so
  callers can access exchange-specific fields without breaking the abstraction.

### Testing layout

Tests are split into two strictly separated folders:

- `tests/unit/{exchange}/` — fast, offline, fixture-driven. Each exchange has a `fixtures/`
  folder of raw JSON captured from the exchange, plus `test_parser.py` (exercises parser
  methods directly on fixtures) and `test_adaptor.py` (instantiates the adaptor and replaces
  the underlying HTTP client methods with `AsyncMock`). CI runs only this suite, and it must
  not touch the network.
- `tests/integration/{exchange}/` — live smoke tests against real public endpoints, gated by
  `RUN_INTEGRATION_TESTS=1`. These catch exchange-side API drift and verify the unified
  contract end-to-end. Keep them small (one assertion per endpoint).

When fixtures go stale (exchange changes a field), the unit suite will still pass while the
integration suite starts failing — that divergence is the signal to re-capture fixtures.

### Candle / funding-rate range semantics

`get_history_candlesticks` and `get_history_funding_rate` take either `(start, end)` timestamps in
**milliseconds** or a `num` count; if both are given, `(start, end)` wins. Exchanges paginate
differently, so each adaptor contains its own loop to assemble the requested window — keep this
logic in the top-level adaptor class, not in the parser.

## Adding a new exchange

Follow [dev.md](dev.md): create `cex_adaptors/exchanges/{name}.py` (extending `BaseClient`),
`cex_adaptors/parsers/{name}.py` (extending `Parser`), and `cex_adaptors/{name}.py` (the adaptor
stitching them together). Mirror the `Binance` implementation as a reference. Add tests under
both `tests/unit/{name}/` (fixtures + parser + adaptor) and `tests/integration/{name}/`
(live smoke tests, gated by `RUN_INTEGRATION_TESTS=1`).

## Style

- Line length 120 (black + flake8 both configured).
- flake8 ignores: W605, E501, E203, W503.
- isort profile is `black`.
- pre-commit is `fail_fast: true` — fix the first failure before re-running.
