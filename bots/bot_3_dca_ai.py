"""
AI Quant Bootstrap — Bot #3: DCA with AI Correction
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config, print_config_summary
from lib.log import setup_logger
from lib.exchange import ExchangeClient
from lib.ai_client import AIClient
from lib.telegram_alerter import TelegramAlerter
from lib.journal import log_trade
from lib.helpers import format_usdt, format_percent


class DCAWithAI:
    def __init__(self, config) -> None:
        self.cfg = config
        self.logger = setup_logger("DCA_Bot", config.general.log_level)
        self.telegram = TelegramAlerter(
            bot_token=config.api_keys.telegram_bot_token,
            chat_id=config.api_keys.telegram_chat_id,
            enabled=config.notifications.telegram
        )
        self.exchange = ExchangeClient(
            exchange_name=config.general.primary_exchange,
            api_key=config.api_keys.binance_api_key,
            secret=config.api_keys.binance_secret,
            testnet=config.api_keys.binance_testnet,
            logger=self.logger
        )
        self.ai = AIClient(config, logger=self.logger)
        self.orders_executed = 0
        self.orders_skipped = 0
        self.total_spent = 0.0
        self.total_bought = 0.0
        self.first_buy_price = None
        self.start_time = datetime.now()

    def _fetch_news(self) -> list[str]:
        try:
            import requests
            url = "https://cryptopanic.com/api/v1/posts/?filter=important&public=true"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                headlines = [post.get("title", "") for post in data.get("results", [])[:10] if post.get("title")]
                if headlines:
                    return headlines
        except Exception:
            pass
        return []

    def _should_buy(self) -> tuple[bool, str]:
        if not self.ai.enabled:
            return True, "AI disabled, proceeding."
        news = self._fetch_news()
        result = self.ai.check_news_sentiment(news, self.cfg.bot_dca.symbol)
        if result is None:
            return True, "AI unavailable, proceeding."
        should_buy = result.get("should_buy", True)
        reasoning = result.get("reasoning", "")
        self.logger.info(f"AI decision: {'BUY' if should_buy else 'SKIP'} — {reasoning}")
        return should_buy, reasoning

    def _execute_buy(self) -> None:
        symbol = self.cfg.bot_dca.symbol
        amount = self.cfg.bot_dca.order_amount
        ticker = self.exchange.fetch_ticker(symbol)
        if not ticker:
            return
        price = ticker["last"]
        quantity = amount / price
        if self.first_buy_price is None:
            self.first_buy_price = price
        drawdown = (self.first_buy_price - price) / self.first_buy_price * 100
        if drawdown > self.cfg.bot_dca.max_drawdown_percent:
            self.logger.warning(f"⚠️ Drawdown {format_percent(drawdown/100)} exceeds limit. Skipping.")
            self.orders_skipped += 1
            return
        order = self.exchange.market_buy(symbol, amount)
        if order:
            self.logger.info(f"🟢 BOUGHT ${amount} of {symbol} at {format_usdt(price)}")
            self.total_spent += amount
            self.total_bought += quantity
            self.orders_executed += 1
            log_trade(bot_name="DCA_Bot", action="BUY", symbol=symbol, price=price,
                      quantity=quantity, amount_usdt=amount, reasoning="DCA buy")

    def _print_stats(self) -> None:
        avg_price = self.total_spent / self.total_bought if self.total_bought > 0 else 0
        self.logger.info(f"📊 DCA | Spent: {format_usdt(self.total_spent)} | Bought: {self.total_bought:.6f} | Avg: {format_usdt(avg_price)} | Skipped: {self.orders_skipped}")

    def run(self) -> None:
        symbol = self.cfg.bot_dca.symbol
        interval = self.cfg.bot_dca.interval_hours * 3600
        self.logger.info(f"🚀 DCA Bot STARTED | {symbol} | ${self.cfg.bot_dca.order_amount} every {self.cfg.bot_dca.interval_hours}h")
        self.telegram.send_startup_message("DCA Bot", f"Пара: {symbol}\nСумма: {format_usdt(self.cfg.bot_dca.order_amount)}")
        try:
            while self.orders_executed < self.cfg.bot_dca.max_dca_orders:
                self._print_stats()
                if self.cfg.bot_dca.ai_news_check:
                    should_buy, reasoning = self._should_buy()
                    if not should_buy:
                        self.logger.warning(f"⏭️ AI says SKIP: {reasoning}")
                        self.orders_skipped += 1
                        self.telegram.send_message(f"⏭️ DCA пропустил. AI: {reasoning}")
                    else:
                        self._execute_buy()
                        self.telegram.send_message(f"🟢 DCA докупил {symbol} на {format_usdt(self.cfg.bot_dca.order_amount)}. AI: {reasoning}")
                else:
                    self._execute_buy()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.logger.info("⏹️ Stopped.")
        finally:
            self._print_stats()


def main():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        config = load_config(config_path)
        if not config.bot_dca.enabled:
            print("⏸️ DCA Bot disabled.")
            return
        print_config_summary(config)
        DCAWithAI(config).run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()