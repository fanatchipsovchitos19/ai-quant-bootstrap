"""
AI Quant Bootstrap — Bot #5: DEX Sniper
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web3 import Web3

from lib.config import load_config, print_config_summary
from lib.log import setup_logger
from lib.ai_client import AIClient
from lib.telegram_alerter import TelegramAlerter
from lib.journal import log_trade
from lib.helpers import format_percent


FACTORY_ABI = json.loads('[{"anonymous":false,"inputs":[{"indexed":true,"name":"token0","type":"address"},{"indexed":true,"name":"token1","type":"address"},{"indexed":false,"name":"pair","type":"address"},{"indexed":false,"name":"count","type":"uint256"}],"name":"PairCreated","type":"event"}]')
TOKEN_ABI = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')


class DexSniper:
    def __init__(self, config):
        self.cfg = config
        self.logger = setup_logger("DexSniper", config.general.log_level)
        self.telegram = TelegramAlerter(bot_token=config.api_keys.telegram_bot_token, chat_id=config.api_keys.telegram_chat_id, enabled=config.notifications.telegram)
        self.ai = AIClient(config, logger=self.logger)
        self.w3 = Web3(Web3.HTTPProvider(config.bot_dex_sniper.rpc_url))
        self.factory = self.w3.eth.contract(address=self.w3.to_checksum_address(config.bot_dex_sniper.factory_address), abi=FACTORY_ABI)
        self.pairs_detected = 0
        self.scams_filtered = 0
        self.trades_executed = 0
        self.total_invested = 0.0
        self.start_time = datetime.now()
        self.sniped_tokens = []

    def _get_token_info(self, addr):
        try:
            c = self.w3.eth.contract(address=self.w3.to_checksum_address(addr), abi=TOKEN_ABI)
            return {"name": c.functions.name().call(), "symbol": c.functions.symbol().call(), "decimals": c.functions.decimals().call()}
        except:
            return {}

    def _is_scam(self, info, addr):
        name = info.get("name", "Unknown").lower()
        symbol = info.get("symbol", "UNKNOWN").lower()
        patterns = ["elon", "doge", "pepe", "shib", "moon", "safe", "inu", "ai", "gpt", "2.0", "v2", "official"]
        if sum(1 for p in patterns if p in name or p in symbol) >= 2:
            return True, "Scam patterns"
        if self.ai.enabled:
            result = self.ai.classify_token_scam(info.get("name","?"), info.get("symbol","?"), self.cfg.bot_dex_sniper.chain)
            if result:
                return result.get("is_scam", False), result.get("reasoning", "")
        return False, "OK"

    def _execute_snipe(self, addr, info, pair):
        buy = self.cfg.bot_dex_sniper.buy_amount_native
        self.trades_executed += 1
        self.total_invested += buy
        self.logger.info(f"🎯 SNIPE: {info.get('name')} ({info.get('symbol')})")
        self.telegram.send_message(f"🎯 DEX SNIPER: {info.get('name')} ({info.get('symbol')})\nКонтракт: {addr[:10]}...\nСумма: {buy}")
        log_trade(bot_name="DexSniper", action="BUY", symbol=info.get("symbol","?"), price=0, quantity=0, amount_usdt=buy, reasoning=f"Sniped {info.get('name')}")
        self.sniped_tokens.append({"symbol": info.get("symbol","?"), "name": info.get("name","?"), "buy_time": datetime.now(), "amount": buy})

    def _check_exits(self):
        for t in self.sniped_tokens[:]:
            if (datetime.now() - t["buy_time"]).total_seconds() > 600:
                log_trade(bot_name="DexSniper", action="SELL", symbol=t["symbol"], price=0, quantity=0, amount_usdt=t["amount"], pnl=-t["amount"]*0.7, pnl_percent=-70, reasoning=f"Auto-exit 10min: {t['name']}")
                self.sniped_tokens.remove(t)

    def _poll(self):
        try:
            current = self.w3.eth.block_number
            filt = self.factory.events.PairCreated.create_filter(from_block=current-50, to_block=current)
            for evt in filt.get_all_entries():
                args = evt["args"]
                known = ["0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "0xe9e7CEA3DedCA5984780Bafc599bD69ADd087D56"]
                target = args["token0"] if args["token0"] not in known else args["token1"]
                self.pairs_detected += 1
                info = self._get_token_info(target)
                if not info: continue
                is_scam, reason = self._is_scam(info, target)
                if is_scam:
                    self.scams_filtered += 1
                    self.logger.warning(f"🚫 SCAM: {info.get('name')} — {reason}")
                else:
                    self._execute_snipe(target, info, args["pair"])
        except Exception as e:
            self.logger.error(f"Poll error: {e}")

    def run(self):
        self.logger.info(f"🚀 DEX Sniper | Chain: {self.cfg.bot_dex_sniper.chain.upper()} | Buy: {self.cfg.bot_dex_sniper.buy_amount_native}")
        self.telegram.send_startup_message("DEX Sniper", f"Сеть: {self.cfg.bot_dex_sniper.chain.upper()}")
        try:
            while True:
                self._poll()
                self._check_exits()
                time.sleep(self.cfg.general.scan_interval_seconds)
        except KeyboardInterrupt:
            self.logger.info("⏹️ Stopped.")


def main():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        config = load_config(config_path)
        if not config.bot_dex_sniper.enabled:
            print("⏸️ DEX Sniper disabled.")
            return
        print_config_summary(config)
        DexSniper(config).run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()