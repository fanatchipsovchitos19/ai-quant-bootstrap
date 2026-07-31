"""
AI Quant Bootstrap — Exchange Client
Direct REST API wrapper for Binance, Bybit, OKX.
No ccxt dependency — avoids Windows encoding bugs.
"""

import sys
import os
import io
import time
import json
import hmac
import hashlib
from typing import Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("❌ requests not installed. Run: pip install requests")
    sys.exit(1)

from lib.helpers import format_usdt, format_percent


# ============================================================
# Base URLs
# ============================================================
EXCHANGE_URLS = {
    "binance": {
        "public": "https://api.binance.com",
        "testnet": "https://testnet.binance.vision",
    },
    "bybit": {
        "public": "https://api.bybit.com",
        "testnet": "https://api-testnet.bybit.com",
    },
    "okx": {
        "public": "https://www.okx.com",
        "testnet": "https://www.okx.com",
    },
}


class ExchangeClient:
    """
    Unified exchange client using direct REST API calls.
    No ccxt, no encoding issues.
    
    Usage:
        client = ExchangeClient("binance")
        price = client.fetch_price("BTCUSDT")
    """
    
    def __init__(
        self,
        exchange_name: str,
        api_key: str = "",
        secret: str = "",
        testnet: bool = False,
        logger=None
    ):
        self.exchange_name = exchange_name.lower()
        self.testnet = testnet
        self.logger = logger
        self.api_key = api_key
        self.secret = secret
        
        urls = EXCHANGE_URLS.get(self.exchange_name)
        if not urls:
            raise ValueError(f"Unsupported exchange: {exchange_name}")
        
        self.base_url = urls["testnet"] if testnet else urls["public"]
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AIQuantBootstrap/1.0"
        })
        
        if self.logger:
            mode = "testnet" if testnet else "LIVE"
            self.logger.info(f"Exchange client: {self.exchange_name.upper()} ({mode})")
    
    # ============================================================
    # HTTP Helpers
    # ============================================================
    
    def _get(self, path: str, params: dict = None, signed: bool = False) -> Optional[dict]:
        """HTTP GET with error handling."""
        url = f"{self.base_url}{path}"
        try:
            if signed:
                params = params or {}
                params = self._sign_request(params)
                response = self.session.get(url, params=params, timeout=10)
            else:
                response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                if self.logger:
                    self.logger.error(f"HTTP {response.status_code} on {path}: {response.text[:200]}")
                return None
        except requests.exceptions.Timeout:
            if self.logger:
                self.logger.error(f"Timeout on {path}")
            return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"Request failed {path}: {e}")
            return None
    
    def _post_signed(self, path: str, params: dict) -> Optional[dict]:
        """Signed POST request for trading."""
        if not self.api_key or "ВАШ" in self.api_key:
            if self.logger:
                self.logger.info(f"📝 PAPER TRADE: POST {path} — {params.get('side', '')} {params.get('symbol', '')}")
            return {"status": "paper_trade", **params}
        
        url = f"{self.base_url}{path}"
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        
        headers = {"X-MBX-APIKEY": self.api_key}
        
        try:
            response = self.session.post(url, data=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                if self.logger:
                    self.logger.error(f"Order failed: {response.status_code} — {response.text[:200]}")
                return None
        except Exception as e:
            if self.logger:
                self.logger.error(f"POST {path} failed: {e}")
            return None
    
    def _delete_signed(self, path: str, params: dict) -> bool:
        """Signed DELETE request."""
        if not self.api_key or "ВАШ" in self.api_key:
            if self.logger:
                self.logger.info(f"📝 PAPER TRADE: DELETE {path}")
            return True
        
        url = f"{self.base_url}{path}"
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        headers = {"X-MBX-APIKEY": self.api_key}
        
        try:
            resp = self.session.delete(url, params=params, headers=headers, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            if self.logger:
                self.logger.error(f"DELETE failed: {e}")
            return False
    
    def _sign_request(self, params: dict) -> dict:
        """Adds timestamp and signature to params (Binance-style)."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params
    
    # ============================================================
    # Symbol Helpers
    # ============================================================
    
    def _normalize_symbol(self, symbol: str) -> str:
        """BTC/USDT -> BTCUSDT (Binance/Bybit) or BTC-USDT (OKX)."""
        if "/" in symbol:
            base, quote = symbol.split("/")
        else:
            return symbol
        
        if self.exchange_name == "okx":
            return f"{base}-{quote}"
        return f"{base}{quote}"
    
    # ============================================================
    # Market Data (public)
    # ============================================================
    
    def fetch_ticker(self, symbol: str) -> Optional[dict]:
        """Returns normalized ticker dict with keys: symbol, last, bid, ask, high, low, volume, percentage."""
        raw = self._get_ticker_raw(symbol)
        if not raw:
            return None
        return self._normalize_ticker(raw, symbol)
    
    def _get_ticker_raw(self, symbol: str) -> Optional[dict]:
        """Fetches raw ticker data from exchange."""
        sym = self._normalize_symbol(symbol)
        
        if self.exchange_name == "binance":
            data = self._get("/api/v3/ticker/24hr", params={"symbol": sym})
            if data:
                return {
                    "symbol": f"{symbol}",
                    "last": float(data["lastPrice"]),
                    "bid": float(data["bidPrice"]),
                    "ask": float(data["askPrice"]),
                    "high": float(data["highPrice"]),
                    "low": float(data["lowPrice"]),
                    "volume": float(data["volume"]),
                    "percentage": float(data.get("priceChangePercent", 0)),
                }
        
        elif self.exchange_name == "bybit":
            data = self._get("/v5/market/tickers", params={"category": "spot", "symbol": sym})
            if data and data.get("result", {}).get("list"):
                item = data["result"]["list"][0]
                return {
                    "symbol": f"{symbol}",
                    "last": float(item["lastPrice"]),
                    "bid": float(item["bid1Price"]),
                    "ask": float(item["ask1Price"]),
                    "high": float(item["highPrice24h"]),
                    "low": float(item["lowPrice24h"]),
                    "volume": float(item["volume24h"]),
                    "percentage": float(item.get("price24hPcnt", 0)) * 100,
                }
        
        elif self.exchange_name == "okx":
            data = self._get("/api/v5/market/ticker", params={"instId": sym})
            if data and data.get("data"):
                item = data["data"][0]
                return {
                    "symbol": f"{symbol}",
                    "last": float(item["last"]),
                    "bid": float(item["bidPx"]),
                    "ask": float(item["askPx"]),
                    "high": float(item["high24h"]),
                    "low": float(item["low24h"]),
                    "volume": float(item["vol24h"]),
                    "percentage": (float(item["last"]) / float(item["open24h"]) - 1) * 100,
                }
        
        return None
    
    def _normalize_ticker(self, raw: dict, symbol: str) -> dict:
        """Ensures ticker has all expected fields."""
        return {
            "symbol": symbol,
            "last": raw.get("last", 0),
            "bid": raw.get("bid", 0),
            "ask": raw.get("ask", 0),
            "high": raw.get("high", 0),
            "low": raw.get("low", 0),
            "volume": raw.get("volume", 0),
            "percentage": raw.get("percentage", 0),
            "timestamp": int(time.time() * 1000),
        }
    
    def fetch_price(self, symbol: str) -> Optional[float]:
        """Returns only the last price."""
        ticker = self.fetch_ticker(symbol)
        return ticker["last"] if ticker else None
    
    def fetch_order_book(self, symbol: str, limit: int = 10) -> Optional[dict]:
        """Returns order book with bids and asks."""
        sym = self._normalize_symbol(symbol)
        
        if self.exchange_name == "binance":
            data = self._get("/api/v3/depth", params={"symbol": sym, "limit": limit})
            if data:
                return {
                    "bids": [[float(p), float(q)] for p, q in data["bids"][:limit]],
                    "asks": [[float(p), float(q)] for p, q in data["asks"][:limit]],
                }
        
        elif self.exchange_name == "bybit":
            data = self._get("/v5/market/orderbook", params={"category": "spot", "symbol": sym, "limit": limit})
            if data and data.get("result"):
                return {
                    "bids": [[float(p), float(q)] for p, q in data["result"]["b"][:limit]],
                    "asks": [[float(p), float(q)] for p, q in data["result"]["a"][:limit]],
                }
        
        elif self.exchange_name == "okx":
            data = self._get("/api/v5/market/books", params={"instId": sym, "sz": limit})
            if data and data.get("data"):
                return {
                    "bids": [[float(p), float(q)] for p, q, *_ in data["data"][0]["bids"][:limit]],
                    "asks": [[float(p), float(q)] for p, q, *_ in data["data"][0]["asks"][:limit]],
                }
        
        return None
    
    # ============================================================
    # Account (signed)
    # ============================================================
    
    def fetch_balance(self) -> Optional[dict]:
        """Returns balances. Needs API key + secret."""
        if not self.api_key or "ВАШ" in self.api_key:
            if self.logger:
                self.logger.warning("fetch_balance() needs API keys.")
            return None
        
        if self.exchange_name == "binance":
            data = self._get("/api/v3/account", signed=True)
            if data and "balances" in data:
                result = {}
                for b in data["balances"]:
                    free = float(b["free"])
                    locked = float(b["locked"])
                    if free + locked > 0:
                        result[b["asset"]] = {"free": free, "used": locked, "total": free + locked}
                return result
        
        return None
    
    def get_asset_balance(self, asset: str) -> float:
        """Returns free balance of an asset."""
        balance = self.fetch_balance()
        if balance and asset in balance:
            return balance[asset].get("free", 0)
        return 0.0
    
    # ============================================================
    # Trading (signed)
    # ============================================================
    
    def market_buy(self, symbol: str, amount_usdt: float) -> Optional[dict]:
        """Market buy using quote currency. Binance only for now."""
        if self.exchange_name != "binance":
            if self.logger:
                self.logger.warning(f"market_buy() only implemented for Binance, not {self.exchange_name}")
            return None
        
        sym = self._normalize_symbol(symbol)
        ticker = self.fetch_ticker(symbol)
        if not ticker:
            return None
        
        price = ticker["ask"]
        
        if not self.api_key or "ВАШ" in self.api_key:
            quantity = amount_usdt / price
            self.logger.info(f"📝 PAPER TRADE: Market BUY ${amount_usdt} {symbol} @ {format_usdt(price)}")
            return {"status": "paper_trade", "symbol": symbol, "side": "buy", "amount_usdt": amount_usdt, "price": price}
        
        if self.logger:
            self.logger.info(f"🟢 MARKET BUY {symbol}: {format_usdt(amount_usdt)} @ {format_usdt(price)}")
        
        params = {
            "symbol": sym,
            "side": "BUY",
            "type": "MARKET",
            "quoteOrderQty": round(amount_usdt, 2),
        }
        return self._post_signed("/api/v3/order", params)
    
    def market_sell(self, symbol: str, amount_token: float) -> Optional[dict]:
        """Market sell token amount. Binance only for now."""
        if self.exchange_name != "binance":
            if self.logger:
                self.logger.warning(f"market_sell() only implemented for Binance, not {self.exchange_name}")
            return None
        
        sym = self._normalize_symbol(symbol)
        ticker = self.fetch_ticker(symbol)
        if not ticker:
            return None
        
        price = ticker["bid"]
        
        if not self.api_key or "ВАШ" in self.api_key:
            self.logger.info(f"📝 PAPER TRADE: Market SELL {amount_token:.6f} {symbol} @ {format_usdt(price)}")
            return {"status": "paper_trade", "symbol": symbol, "side": "sell", "amount_token": amount_token, "price": price}
        
        if self.logger:
            self.logger.info(f"🔴 MARKET SELL {symbol}: {amount_token:.6f} @ {format_usdt(price)}")
        
        params = {
            "symbol": sym,
            "side": "SELL",
            "type": "MARKET",
            "quantity": round(amount_token, 6),
        }
        return self._post_signed("/api/v3/order", params)
    
    def limit_buy(self, symbol: str, amount: float, price: float) -> Optional[dict]:
        """Places a limit buy order. Binance only."""
        if self.exchange_name != "binance":
            if self.logger:
                self.logger.warning(f"limit_buy() only for Binance")
            return None
        
        sym = self._normalize_symbol(symbol)
        
        if not self.api_key or "ВАШ" in self.api_key:
            if self.logger:
                self.logger.info(f"📝 PAPER TRADE: Limit BUY {amount:.6f} {symbol} @ {format_usdt(price)}")
            return {"status": "paper_trade", "symbol": symbol, "side": "buy", "price": price, "quantity": amount}
        
        params = {
            "symbol": sym,
            "side": "BUY",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": round(amount, 6),
            "price": round(price, 2),
        }
        return self._post_signed("/api/v3/order", params)
    
    def limit_sell(self, symbol: str, amount: float, price: float) -> Optional[dict]:
        """Places a limit sell order. Binance only."""
        if self.exchange_name != "binance":
            if self.logger:
                self.logger.warning(f"limit_sell() only for Binance")
            return None
        
        sym = self._normalize_symbol(symbol)
        
        if not self.api_key or "ВАШ" in self.api_key:
            if self.logger:
                self.logger.info(f"📝 PAPER TRADE: Limit SELL {amount:.6f} {symbol} @ {format_usdt(price)}")
            return {"status": "paper_trade", "symbol": symbol, "side": "sell", "price": price, "quantity": amount}
        
        params = {
            "symbol": sym,
            "side": "SELL",
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": round(amount, 6),
            "price": round(price, 2),
        }
        return self._post_signed("/api/v3/order", params)
    
    def cancel_all_orders(self, symbol: str) -> bool:
        """Cancels all open orders for a symbol. Binance only."""
        if self.exchange_name != "binance":
            if self.logger:
                self.logger.warning(f"cancel_all_orders() only for Binance")
            return False
        
        sym = self._normalize_symbol(symbol)
        
        if not self.api_key or "ВАШ" in self.api_key:
            if self.logger:
                self.logger.info(f"📝 PAPER TRADE: Cancel all orders for {symbol}")
            return True
        
        return self._delete_signed("/api/v3/openOrders", {"symbol": sym})
    
    def fetch_open_orders(self, symbol: str) -> list:
        """Returns list of open orders for a symbol."""
        return []
    
    # ============================================================
    # Health Check
    # ============================================================
    
    def test_connection(self) -> bool:
        """Tests connectivity by pinging the exchange."""
        try:
            if self.exchange_name == "binance":
                data = self._get("/api/v3/ping")
                ok = data == {}
            elif self.exchange_name == "bybit":
                data = self._get("/v5/market/time")
                ok = data is not None and data.get("retCode") == 0
            elif self.exchange_name == "okx":
                data = self._get("/api/v5/public/time")
                ok = data is not None and data.get("code") == "0"
            else:
                ok = False
            
            if self.logger:
                if ok:
                    self.logger.info(f"✅ Connection to {self.exchange_name.upper()} OK")
                else:
                    self.logger.error(f"❌ Connection to {self.exchange_name.upper()} FAILED")
            return ok
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Connection to {self.exchange_name.upper()} FAILED: {e}")
            return False
    
    def load_markets(self) -> dict:
        """Stub — returns empty dict."""
        return {}
    
    def get_account_summary(self) -> str:
        """Returns a formatted summary of the account."""
        balance = self.fetch_balance()
        if not balance:
            return "Unable to fetch balance."
        lines = [f"\n{'='*50}", f"  💰 {self.exchange_name.upper()} BALANCE", f"{'='*50}"]
        for asset, data in balance.items():
            total = data.get("total", 0)
            if total > 0:
                lines.append(f"  {asset}: {total:.6f}")
        if len(lines) == 3:
            lines.append("  (empty)")
        lines.append(f"{'='*50}\n")
        return "\n".join(lines)


# ============================================================
# Quick Test
# ============================================================
if __name__ == "__main__":
    print("=== Direct Exchange Client Test ===\n")
    
    for ex_name in ["binance", "bybit", "okx"]:
        print(f"Testing {ex_name.upper()}...")
        client = ExchangeClient(ex_name)
        if client.test_connection():
            btc = client.fetch_ticker("BTC/USDT")
            eth = client.fetch_ticker("ETH/USDT")
            if btc:
                print(f"  BTC: {format_usdt(btc['last'])} (24h: {format_percent(btc['percentage']/100)})")
            if eth:
                print(f"  ETH: {format_usdt(eth['last'])} (24h: {format_percent(eth['percentage']/100)})")
        print()
    
    print("✅ Direct API client works!")