"""FYERS API v3 Market Data Provider for Optopsy.

Fetches live Indian options chains (NIFTY, BANKNIFTY, FINNIFTY, NSE equity options),
Greeks (Delta, Theta, Gamma, Vega, IV), Open Interest, and underlying quotes via FYERS API v3.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from .base import DataProvider

_log = logging.getLogger(__name__)

_FYERS_DATA_URL = "https://api-t1.fyers.in/data"
_OPTIONS_CHAIN_URL = f"{_FYERS_DATA_URL}/options-chain-v3"
_QUOTES_URL = f"{_FYERS_DATA_URL}/quotes"
_HISTORY_URL = f"{_FYERS_DATA_URL}/history"

_SYMBOL_ALIASES = {
    "NIFTY": "NSE:NIFTY50-INDEX",
    "NIFTY50": "NSE:NIFTY50-INDEX",
    "BANKNIFTY": "NSE:NIFTYBANK-INDEX",
    "NIFTYBANK": "NSE:NIFTYBANK-INDEX",
    "FINNIFTY": "NSE:FINNIFTY-INDEX",
    "NIFTYFIN": "NSE:FINNIFTY-INDEX",
    "MIDCPNIFTY": "NSE:MIDCPNIFTY-INDEX",
    "SENSEX": "BSE:SENSEX-INDEX",
    "BANKEX": "BSE:BANKEX-INDEX",
}


def _normalize_symbol(symbol: str) -> str:
    """Normalize input symbol to FYERS format (e.g. NIFTY -> NSE:NIFTY50-INDEX)."""
    clean = symbol.strip().upper()
    if clean in _SYMBOL_ALIASES:
        return _SYMBOL_ALIASES[clean]
    if ":" in clean:
        return clean
    # Default to NSE index if ending with -INDEX or equity if standard ticker
    if clean.endswith("-INDEX"):
        return f"NSE:{clean}"
    return f"NSE:{clean}-EQ"


class FyersProvider(DataProvider):
    """FYERS API v3 data provider for live Indian options chains & market data."""

    def __init__(self) -> None:
        self._session = requests.Session()

    @property
    def name(self) -> str:
        return "FYERS"

    @property
    def env_key(self) -> str:
        return "FYERS_ACCESS_TOKEN"

    def is_available(self) -> bool:
        """Available if FYERS_ACCESS_TOKEN is configured."""
        token = os.environ.get(self.env_key, "").strip()
        return bool(token)

    def _get_auth_header(self) -> str:
        """Construct FYERS Authorization header: '<app_id>:<access_token>'."""
        token = os.environ.get("FYERS_ACCESS_TOKEN", "").strip()
        app_id = os.environ.get("FYERS_APP_ID", "").strip()

        # If user supplied 'app_id:token' together in FYERS_ACCESS_TOKEN
        if ":" in token:
            return token
        if app_id:
            return f"{app_id}:{token}"
        return token

    def get_tool_names(self) -> list[str]:
        return ["fetch_fyers_options", "fetch_fyers_quotes", "fetch_fyers_history"]

    def replaces_dataset(self, tool_name: str) -> bool:
        """Options chain replaces active dataset for strategy backtesting."""
        return tool_name == "fetch_fyers_options"

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "fetch_fyers_options",
                    "description": (
                        "Fetch live Indian option chain data (strikes, premiums, delta, "
                        "gamma, theta, vega, IV, OI) from FYERS API for Indian indices and stocks "
                        "(e.g., NIFTY, BANKNIFTY, FINNIFTY, RELIANCE). Sets the chain as active dataset "
                        "for backtesting and option selling analysis."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": (
                                    "Underlying symbol (e.g. 'NIFTY', 'BANKNIFTY', 'FINNIFTY', "
                                    "'NSE:NIFTY50-INDEX', or 'NSE:RELIANCE-EQ')."
                                ),
                            },
                            "strikecount": {
                                "type": "integer",
                                "description": "Number of strikes above and below ATM (default 15, max 50).",
                                "default": 15,
                            },
                            "expiry": {
                                "type": "string",
                                "description": (
                                    "Optional specific expiry timestamp or date. Leave empty for the nearest expiry."
                                ),
                            },
                        },
                        "required": ["symbol"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_fyers_quotes",
                    "description": "Fetch live market quotes, LTP, day high, low, volume for an Indian stock or index via FYERS.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Underlying symbol (e.g. 'NIFTY', 'BANKNIFTY', 'NSE:RELIANCE-EQ').",
                            }
                        },
                        "required": ["symbol"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_fyers_history",
                    "description": "Fetch historical candlestick (OHLCV) data for an Indian index, stock, or option contract via FYERS.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Symbol name in FYERS format (e.g. 'NSE:NIFTY50-INDEX').",
                            },
                            "resolution": {
                                "type": "string",
                                "description": "Candle timeframe: 'D' (daily), '1', '5', '15', '60' (minutes). Default 'D'.",
                                "default": "D",
                            },
                            "range_from": {
                                "type": "string",
                                "description": "Start date in 'YYYY-MM-DD' format.",
                            },
                            "range_to": {
                                "type": "string",
                                "description": "End date in 'YYYY-MM-DD' format.",
                            },
                        },
                        "required": ["symbol", "range_from", "range_to"],
                    },
                },
            },
        ]

    def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> tuple[str, pd.DataFrame | None]:
        if tool_name == "fetch_fyers_options":
            return self._fetch_options_chain(
                symbol=arguments.get("symbol", "NIFTY"),
                strikecount=int(arguments.get("strikecount", 15)),
                expiry=arguments.get("expiry"),
            )
        if tool_name == "fetch_fyers_quotes":
            return self._fetch_quotes(symbol=arguments.get("symbol", "NIFTY"))
        if tool_name == "fetch_fyers_history":
            return self._fetch_history(
                symbol=arguments.get("symbol", "NIFTY"),
                resolution=arguments.get("resolution", "D"),
                range_from=arguments.get("range_from", ""),
                range_to=arguments.get("range_to", ""),
            )
        return f"Unknown tool: {tool_name}", None

    def _auth_expired_message(self) -> str:
        app_id = os.environ.get("FYERS_APP_ID", "GOHBCRZYVM-100").strip()
        auth_url = (
            f"https://api-t1.fyers.in/api/v3/generate-authcode?"
            f"client_id={app_id}&redirect_uri=https%3A%2F%2Ftrade.fyers.in%2Fapi-login%2Fredirect-uri%2Findex.html"
            f"&response_type=code&state=sample_state"
        )
        return (
            f"⚠️ **FYERS Access Token Expired (HTTP 401)**\n\n"
            f"Per FYERS/SEBI security rules, broker session tokens expire daily at 6:00 AM IST.\n\n"
            f"👉 **To renew in 1 click:**\n"
            f"1. Open authorization URL: [{auth_url}]({auth_url})\n"
            f"2. Log in with your FYERS PIN/OTP to approve the app.\n"
            f"3. Copy the `auth_code` from the redirect page URL and send it here to activate today's token."
        )

    def _fetch_options_chain(
        self, symbol: str, strikecount: int = 15, expiry: str | None = None
    ) -> tuple[str, pd.DataFrame | None]:
        fyers_symbol = _normalize_symbol(symbol)
        auth_header = self._get_auth_header()
        if not auth_header:
            return "FYERS_ACCESS_TOKEN not configured. Add it in your environment variables.", None

        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }
        params: dict[str, Any] = {
            "symbol": fyers_symbol,
            "strikecount": min(max(strikecount, 1), 50),
            "greeks": 1,
        }
        if expiry:
            params["timestamp"] = expiry

        try:
            resp = self._session.get(_OPTIONS_CHAIN_URL, headers=headers, params=params, timeout=20)
            if resp.status_code != 200:
                if resp.status_code == 401 or "valid token" in resp.text:
                    return self._auth_expired_message(), None
                return f"FYERS API error (HTTP {resp.status_code}): {resp.text}", None

            res_json = resp.json()
            if res_json.get("s") == "error" or res_json.get("code") not in (200, 201):
                msg = res_json.get("message") or res_json.get("s")
                return f"FYERS Option Chain Error: {msg}", None

            data = res_json.get("data", {})
            raw_chain = data.get("optionsChain", [])
            if not raw_chain:
                return f"No option chain contracts returned by FYERS for {fyers_symbol}.", None

            expiry_data = data.get("expiryData", [])
            nearest_expiry_str = (
                expiry_data[0].get("date", "N/A") if expiry_data else "Current"
            )

            # Spot price lookup
            spot_price = None
            rows = []
            quote_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            for item in raw_chain:
                strike_price = item.get("strike_price")
                opt_type_raw = str(item.get("option_type", "")).upper()

                # Underlying index row
                if strike_price in (-1, None) or not opt_type_raw:
                    spot_price = item.get("ltp") or item.get("fp")
                    continue

                if opt_type_raw not in ("CE", "PE"):
                    continue

                opt_type = "c" if opt_type_raw == "CE" else "p"
                ltp = float(item.get("ltp") or 0.0)
                bid = float(item.get("bid") or ltp)
                ask = float(item.get("ask") or ltp)
                volume = int(item.get("volume") or 0)
                oi = int(item.get("oi") or 0)

                # Expiration resolution
                exp_timestamp = item.get("expiry_date")
                if exp_timestamp:
                    try:
                        exp_dt = datetime.fromtimestamp(int(exp_timestamp), tz=timezone.utc)
                        exp_str = exp_dt.strftime("%Y-%m-%d")
                    except Exception:
                        exp_str = nearest_expiry_str
                else:
                    exp_str = nearest_expiry_str

                # Greeks extraction
                greeks = item.get("greeks") or {}
                delta = float(greeks.get("delta") or (0.5 if opt_type == "c" else -0.5))
                gamma = float(greeks.get("gamma") or 0.0)
                theta = float(greeks.get("theta") or 0.0)
                vega = float(greeks.get("vega") or 0.0)
                rho = float(greeks.get("rho") or 0.0)
                iv = float(item.get("iv") or greeks.get("iv") or 0.0)

                rows.append({
                    "underlying_symbol": symbol.upper(),
                    "option_type": opt_type,
                    "expiration": pd.to_datetime(exp_str),
                    "quote_date": pd.to_datetime(quote_date),
                    "strike": float(strike_price),
                    "bid": bid,
                    "ask": ask,
                    "last": ltp,
                    "volume": volume,
                    "open_interest": oi,
                    "delta": delta,
                    "gamma": gamma,
                    "theta": theta,
                    "vega": vega,
                    "rho": rho,
                    "implied_volatility": iv / 100.0 if iv > 1.0 else iv,
                })

            if not rows:
                return f"Could not parse valid option contracts for {fyers_symbol}.", None

            df = pd.DataFrame(rows)
            # Ensure proper sort order: expiration, strike, option_type
            df.sort_values(by=["expiration", "strike", "option_type"], inplace=True)
            df.reset_index(drop=True, inplace=True)

            strikes_count = df["strike"].nunique()
            min_strike = df["strike"].min()
            max_strike = df["strike"].max()
            spot_info = f" | Spot: {spot_price}" if spot_price else ""
            summary = (
                f"✅ **FYERS Option Chain Loaded**: {symbol.upper()} ({fyers_symbol})\n"
                f"- Expiry: `{nearest_expiry_str}`\n"
                f"- Strikes: `{min_strike:,.1f}` to `{max_strike:,.1f}` ({strikes_count} unique strikes){spot_info}\n"
                f"- Total Contracts: `{len(df)}` (Calls & Puts with Delta, Greeks, IV, & OI)\n"
                f"- Ready for strategy simulation (e.g. Short Straddles, Strangles, Iron Condors)."
            )
            return summary, df

        except Exception as exc:
            _log.exception("Failed to fetch FYERS options chain")
            return f"Error connecting to FYERS API: {exc}", None

    def _fetch_quotes(self, symbol: str) -> tuple[str, pd.DataFrame | None]:
        fyers_symbol = _normalize_symbol(symbol)
        auth_header = self._get_auth_header()
        if not auth_header:
            return "FYERS_ACCESS_TOKEN not configured.", None

        headers = {"Authorization": auth_header}
        params = {"symbols": fyers_symbol}

        try:
            resp = self._session.get(_QUOTES_URL, headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                if resp.status_code == 401 or "valid token" in resp.text:
                    return self._auth_expired_message(), None
                return f"FYERS Quotes API error (HTTP {resp.status_code}): {resp.text}", None

            res_json = resp.json()
            quotes_list = res_json.get("d", [])
            if not quotes_list:
                return f"No quote returned for {fyers_symbol}.", None

            q = quotes_list[0].get("v", {})
            summary = (
                f"📈 **Quote for {symbol.upper()} ({fyers_symbol})**:\n"
                f"- LTP: `{q.get('lp', 'N/A')}` ({q.get('chp', '0')}%)\n"
                f"- Open: `{q.get('open_price', 'N/A')}` | High: `{q.get('high_price', 'N/A')}` | Low: `{q.get('low_price', 'N/A')}`\n"
                f"- Previous Close: `{q.get('prev_close_price', 'N/A')}` | Volume: `{q.get('volume', 'N/A'):,}`"
            )
            df = pd.DataFrame([{
                "symbol": fyers_symbol,
                "ltp": q.get("lp"),
                "open": q.get("open_price"),
                "high": q.get("high_price"),
                "low": q.get("low_price"),
                "close": q.get("prev_close_price"),
                "volume": q.get("volume"),
            }])
            return summary, df
        except Exception as exc:
            return f"Error fetching FYERS quote: {exc}", None

    def _fetch_history(
        self, symbol: str, resolution: str, range_from: str, range_to: str
    ) -> tuple[str, pd.DataFrame | None]:
        fyers_symbol = _normalize_symbol(symbol)
        auth_header = self._get_auth_header()
        if not auth_header:
            return "FYERS_ACCESS_TOKEN not configured.", None

        headers = {"Authorization": auth_header}
        params = {
            "symbol": fyers_symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": range_from,
            "range_to": range_to,
            "cont_flag": "1",
        }

        try:
            resp = self._session.get(_HISTORY_URL, headers=headers, params=params, timeout=20)
            if resp.status_code != 200:
                if resp.status_code == 401 or "valid token" in resp.text:
                    return self._auth_expired_message(), None
                return f"FYERS History API error: {resp.text}", None

            res_json = resp.json()
            candles = res_json.get("candles", [])
            if not candles:
                return f"No historical candles returned for {fyers_symbol} ({range_from} to {range_to}).", None

            cols = ["timestamp", "open", "high", "low", "close", "volume"]
            df = pd.DataFrame(candles, columns=cols)
            df["date"] = pd.to_datetime(df["timestamp"], unit="s")
            summary = (
                f"📊 Loaded {len(df)} candles for {symbol.upper()} "
                f"from {range_from} to {range_to} (Timeframe: {resolution})."
            )
            return summary, df
        except Exception as exc:
            return f"Error fetching FYERS history: {exc}", None
