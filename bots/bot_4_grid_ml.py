"""
AI Quant Bootstrap — Bot #4: Grid Bot with ML
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from sklearn.linear_model import LinearRegression

from lib.config import load_config, print_config_summary
from lib.log import setup_logger
from lib.exchange import ExchangeClient
from lib.telegram_alerter import TelegramAlerter
from lib.journal import log_trade
from lib.helpers import format_usdt, format_percent


class GridMLBot:
    def __init__(self, config) -> None:
        self.cfg = config
        self.logger = setup_logger("GridML", config.general.log_level)
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
        self.grid_low = 0.0
        self.grid_high = 0.0
        self.grid_levels = []
        self.trades_count = 0

    def _fetch_historical(self, days=30):
        sym = self.cfg.bot_grid.symbol.replace("/", "")
        try:
            import requests
            resp = requests.get(f"https://api.binance.com/api/v3/klines", params={"symbol": sym, "interval": "1d", "limit": days}, timeout=10)
            if resp.status_code == 200:
                candles = resp.json()
                return [{"open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4])} for c in candles]
        except Exception:
            pass
        return []

    def _predict_range(self):
        data = self._fetch_historical(self.cfg.bot_grid.ml_lookback_days + 7)
        if len(data) < 14:
            ticker = self.exchange.fetch_ticker(self.cfg.bot_grid.symbol)
            if ticker:
                p = ticker["last"]
                return p * 0.95, p * 1.05
            return 0, 0
        X, yh, yl = [], [], []
        for i in range(7, len(data)):
            w = data[i-7:i]
            vol = np.mean([(d["high"]-d["low"])/d["close"] for d in w])
            trend = (w[-1]["close"]-w[0]["close"])/w[0]["close"]
            X.append([vol, trend])
            yh.append((data[i]["high"]-data[i]["open"])/data[i]["open"])
            yl.append((data[i]["low"]-data[i]["open"])/data[i]["open"])
        X, yh, yl = np.array(X), np.array(yh), np.array(yl)
        mh, ml = LinearRegression(), LinearRegression()
        mh.fit(X, yh); ml.fit(X, yl)
        w = data[-7:]
        vol = np.mean([(d["high"]-d["low"])/d["close"] for d in w])
        trend = (w[-1]["close"]-w[0]["close"])/w[0]["close"]
        cur = data[-1]["close"]
        pred_h = cur*(1+max(mh.predict([[vol, trend]])[0], 0.005))
        pred_l = cur*(1+min(ml.predict([[vol, trend]])[0], -0.005))
        self.logger.info(f"ML Prediction: Low={format_usdt(pred_l)} High={format_usdt(pred_h)} (Current: {format_usdt(cur)})")
        return pred_l, pred_h

    def _calculate_grid(self, low, high):
        n = self.cfg.bot_grid.grid_levels
        step = (high-low)/(n+1)
        mid = (high+low)/2
        levels = []
        for i in range(1, n+1):
            price = low+step*i
            levels.append({"price": price, "side": "buy" if price < mid else "sell"})
        return levels

    def _place_orders(self):
        symbol = self.cfg.bot_grid.symbol
        amt = self.cfg.bot_grid.order_amount
        self.exchange.cancel_all_orders(symbol)
        placed = 0
        for lvl in self.grid_levels:
            price, side = lvl["price"], lvl["side"]
            qty = amt/price
            if side == "buy":
                self.exchange.limit_buy(symbol, qty, price)
            else:
                self.exchange.limit_sell(symbol, qty, price)
            placed += 1
            self.logger.info(f"📝 {side.upper()} order: {qty:.6f} @ {format_usdt(price)}")
            log_trade(bot_name="GridML", action=f"LIMIT_{side.upper()}", symbol=symbol, price=price,
                      quantity=qty, amount_usdt=amt, reasoning="Grid order")
        self.logger.info(f"Placed {placed}/{len(self.grid_levels)} grid orders")

    def _print_stats(self):
        self.logger.info(f"📊 Grid | Range: {format_usdt(self.grid_low)} — {format_usdt(self.grid_high)} | Levels: {len(self.grid_levels)} | Trades: {self.trades_count}")

    def run(self):
        symbol = self.cfg.bot_grid.symbol
        self.logger.info(f"🚀 Grid ML Bot STARTED | {symbol} | {self.cfg.bot_grid.grid_levels} levels")
        self.telegram.send_startup_message("Grid ML Bot", f"Пара: {symbol}\nУровней: {self.cfg.bot_grid.grid_levels}")
        interval = self.cfg.bot_grid.recalculate_hours * 3600
        last = 0
        try:
            while True:
                now = time.time()
                if now - last >= interval or self.grid_low == 0:
                    self.logger.info("🔄 Recalculating grid with ML...")
                    low, high = self._predict_range()
                    self.grid_low, self.grid_high = low, high
                    self.grid_levels = self._calculate_grid(low, high)
                    self._place_orders()
                    self.telegram.send_message(f"🔄 Grid ML обновил сетку.\nДиапазон: {format_usdt(low)} — {format_usdt(high)}\nУровней: {len(self.grid_levels)}")
                    last = now
                self._print_stats()
                time.sleep(min(interval - (now-last), 3600))
        except KeyboardInterrupt:
            self.logger.info("⏹️ Stopped.")


def main():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        config = load_config(config_path)
        if not config.bot_grid.enabled:
            print("⏸️ Grid ML Bot disabled.")
            return
        print_config_summary(config)
        GridMLBot(config).run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()