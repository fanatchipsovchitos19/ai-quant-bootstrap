"""
AI Quant Bootstrap — Bot #2: Arbitrage Scanner
Scans prices across Binance, Bybit, OKX for arbitrage opportunities.
"""

import sys
import os
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config, print_config_summary
from lib.log import setup_logger
from lib.exchange import ExchangeClient
from lib.telegram_alerter import TelegramAlerter
from lib.journal import log_trade
from lib.helpers import format_usdt, format_percent


TOP_USDT_PAIRS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
    "MATIC/USDT", "UNI/USDT", "SHIB/USDT", "LTC/USDT", "ATOM/USDT",
    "ETC/USDT", "XLM/USDT", "FIL/USDT", "TRX/USDT", "NEAR/USDT",
    "APT/USDT", "ARB/USDT", "OP/USDT", "SUI/USDT", "PEPE/USDT",
    "INJ/USDT", "TIA/USDT", "SEI/USDT", "WLD/USDT", "RNDR/USDT",
    "FET/USDT", "AGIX/USDT", "GRT/USDT", "AAVE/USDT", "ALGO/USDT",
    "SAND/USDT", "MANA/USDT", "AXS/USDT", "CRV/USDT", "COMP/USDT",
    "SNX/USDT", "MKR/USDT", "1INCH/USDT", "ZRX/USDT", "BAT/USDT",
    "ENJ/USDT", "CHZ/USDT", "LDO/USDT", "EOS/USDT",
]


class ArbitrageScanner:
    """Monitors prices across exchanges and detects arbitrage spreads."""

    def __init__(self, config) -> None:
        self.cfg = config
        self.logger = setup_logger("ArbitrageScanner", config.general.log_level)
        self.telegram = TelegramAlerter(
            bot_token=config.api_keys.telegram_bot_token,
            chat_id=config.api_keys.telegram_chat_id,
            enabled=config.notifications.telegram
        )
        self.exchanges: dict[str, ExchangeClient] = {}
        self.symbols = TOP_USDT_PAIRS.copy()
        self.scans_count = 0
        self.opportunities_found = 0
        self._init_exchanges()

    def _init_exchanges(self) -> None:
        exchange_configs = {
            "binance": (self.cfg.api_keys.binance_api_key, self.cfg.api_keys.binance_secret),
            "bybit": (self.cfg.api_keys.bybit_api_key, self.cfg.api_keys.bybit_secret),
            "okx": (self.cfg.api_keys.okx_api_key, self.cfg.api_keys.okx_secret),
        }
        for ex_name in self.cfg.bot_arbitrage.exchanges:
            api_key, secret = exchange_configs.get(ex_name, ("", ""))
            try:
                client = ExchangeClient(exchange_name=ex_name, api_key=api_key, secret=secret,
                                        testnet=False, logger=self.logger)
                if client.test_connection():
                    self.exchanges[ex_name] = client
                    self.logger.info(f"✅ Connected to {ex_name.upper()}")
            except Exception as e:
                self.logger.error(f"❌ Error initializing {ex_name}: {e}")
        if len(self.exchanges) < 2:
            self.logger.error("Need at least 2 exchanges. Exiting.")
            sys.exit(1)

    def _get_best_spread(self) -> Optional[dict]:
        best = None
        for symbol in self.symbols:
            prices = {}
            for name, ex in self.exchanges.items():
                price = ex.fetch_price(symbol)
                if price:
                    prices[name] = price
            if len(prices) >= 2:
                min_ex = min(prices, key=prices.get)
                max_ex = max(prices, key=prices.get)
                spread = ((prices[max_ex] - prices[min_ex]) / prices[min_ex]) * 100
                if best is None or spread > best["spread"]:
                    best = {"symbol": symbol, "spread": spread}
        return best

    def scan_once(self) -> list[dict]:
        opportunities = []
        for symbol in self.symbols:
            prices = {}
            for name, ex in self.exchanges.items():
                price = ex.fetch_price(symbol)
                if price:
                    prices[name] = price
            if len(prices) < 2:
                continue
            min_ex = min(prices, key=prices.get)
            max_ex = max(prices, key=prices.get)
            min_price = prices[min_ex]
            max_price = prices[max_ex]
            spread = ((max_price - min_price) / min_price) * 100
            if spread >= self.cfg.bot_arbitrage.min_spread_percent:
                opportunities.append({
                    "symbol": symbol,
                    "spread": spread,
                    "buy_exchange": min_ex,
                    "buy_price": min_price,
                    "sell_exchange": max_ex,
                    "sell_price": max_price,
                })
        opportunities.sort(key=lambda x: x["spread"], reverse=True)
        return opportunities

    def print_opportunity(self, opp: dict) -> None:
        print(f"\n{'='*60}")
        print(f"  🔍 ARBITRAGE: {opp['symbol']}")
        print(f"  Buy on:  {opp['buy_exchange'].upper():10} @ {format_usdt(opp['buy_price'])}")
        print(f"  Sell on: {opp['sell_exchange'].upper():10} @ {format_usdt(opp['sell_price'])}")
        print(f"  Spread:  {format_percent(opp['spread']/100)}")
        print(f"  {'='*60}")

    def send_telegram_alert(self, opp: dict) -> None:
        message = (
            f"🔍 <b>АРБИТРАЖ</b>\n"
            f"📊 <b>{opp['symbol']}</b>\n\n"
            f"🟢 Купить: <b>{opp['buy_exchange'].upper()}</b> @ {format_usdt(opp['buy_price'])}\n"
            f"🔴 Продать: <b>{opp['sell_exchange'].upper()}</b> @ {format_usdt(opp['sell_price'])}\n\n"
            f"📈 Спред: <b>{format_percent(opp['spread']/100)}</b>"
        )
        self.telegram.send_message(message)
        # Journal
        log_trade(
            bot_name="ArbitrageScanner",
            action="SIGNAL",
            symbol=opp["symbol"],
            price=opp["buy_price"],
            quantity=0,
            amount_usdt=0,
            reasoning=f"Buy {opp['buy_exchange']} Sell {opp['sell_exchange']} Spread {opp['spread']:.3f}%",
        )

    def run(self) -> None:
        self.logger.info("=" * 55)
        self.logger.info("🚀 Arbitrage Scanner STARTED")
        self.logger.info(f"   Exchanges: {', '.join(e.upper() for e in self.exchanges)}")
        self.logger.info(f"   Pairs: {len(self.symbols)}")
        self.logger.info(f"   Min spread: {format_percent(self.cfg.bot_arbitrage.min_spread_percent/100)}")
        self.logger.info("=" * 55)
        self.telegram.send_startup_message("Arbitrage Scanner", f"Биржи: {', '.join(e.upper() for e in self.exchanges)}\nПар: {len(self.symbols)}")
        try:
            while True:
                self.scans_count += 1
                opportunities = self.scan_once()
                if opportunities:
                    self.opportunities_found += len(opportunities)
                    self.logger.info(f"🎯 Found {len(opportunities)} opportunities!")
                    for opp in opportunities[:3]:
                        self.print_opportunity(opp)
                        self.send_telegram_alert(opp)
                else:
                    best = self._get_best_spread()
                    if best:
                        self.logger.info(f"Scan #{self.scans_count}: Best {format_percent(best['spread']/100)} on {best['symbol']} (need {format_percent(self.cfg.bot_arbitrage.min_spread_percent/100)})")
                    else:
                        self.logger.info(f"Scan #{self.scans_count}: No data")
                time.sleep(self.cfg.general.scan_interval_seconds)
        except KeyboardInterrupt:
            self.logger.info("⏹️  Shutdown signal received.")
        except Exception as e:
            self.logger.error(f"❌ Fatal error: {e}")
        finally:
            self.logger.info(f"Stopped. Scans: {self.scans_count}, Opportunities: {self.opportunities_found}")


def main():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        config = load_config(config_path)
        if not config.bot_arbitrage.enabled:
            print("⏸️  Arbitrage Scanner disabled in config.")
            return
        print_config_summary(config)
        scanner = ArbitrageScanner(config)
        scanner.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()