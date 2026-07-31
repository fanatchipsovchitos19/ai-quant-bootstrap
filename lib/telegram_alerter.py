"""
AI Quant Bootstrap — Telegram Alerter
Sends formatted notifications to a Telegram bot.
"""

import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ requests not installed. Run: pip install requests")
    sys.exit(1)


class TelegramAlerter:
    """
    Simple Telegram notification sender.
    
    Usage:
        alerter = TelegramAlerter(bot_token="...", chat_id="...")
        alerter.send_message("Hello!")
        alerter.send_trade_signal("Arbitrage", "BUY", "BTC/USDT", 67000.0, "Spread 0.52%")
    """
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Args:
            bot_token: Telegram bot token from @BotFather.
            chat_id: Your chat ID (get from @userinfobot).
            enabled: If False, messages are only printed to console.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token) and "ВАШ" not in bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}" if self.enabled else ""
    
    def send_message(self, text: str) -> bool:
        """
        Sends a plain text message to Telegram.
        Returns True if successful.
        """
        # Always print to console
        print(f"📱 Telegram: {text}")
        
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                print(f"⚠️  Telegram API error: {response.status_code} — {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print("⚠️  Telegram API timeout.")
            return False
        except Exception as e:
            print(f"⚠️  Telegram send failed: {e}")
            return False
    
    def send_trade_signal(
        self,
        bot_name: str,
        action: str,
        symbol: str,
        price: float,
        reasoning: str = "",
        level: str = "INFO"
    ) -> bool:
        """
        Sends a formatted trade signal.
        
        Args:
            bot_name: Name of the bot (e.g. "Arbitrage Scanner").
            action: "BUY", "SELL", "ENTRY", "EXIT".
            symbol: Trading pair (e.g. "BTC/USDT").
            price: Price at signal.
            reasoning: Why the signal was generated.
            level: "INFO", "WARNING", "ALERT".
        """
        
        emoji_map = {
            "BUY": "🟢",
            "SELL": "🔴",
            "ENTRY": "🟢",
            "EXIT": "🔴",
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ALERT": "🚨"
        }
        
        emoji = emoji_map.get(level, "📊")
        action_emoji = emoji_map.get(action, "📈")
        
        if level == "ALERT":
            header = f"🚨🚨 {bot_name} — СИГНАЛ! 🚨🚨"
        else:
            header = f"{emoji} {bot_name}"
        
        message = (
            f"{header}\n"
            f"\n"
            f"{action_emoji} <b>{action}</b> — {symbol}\n"
            f"💰 Цена: <code>${price:,.2f}</code>\n"
        )
        
        if reasoning:
            message += f"\n📝 <i>{reasoning}</i>"
        
        return self.send_message(message)
    
    def send_error(self, bot_name: str, error_text: str) -> bool:
        """Sends an error notification."""
        message = (
            f"🔴 <b>{bot_name} — ОШИБКА</b>\n"
            f"\n"
            f"<pre>{error_text}</pre>"
        )
        return self.send_message(message)
    
    def send_startup_message(self, bot_name: str, details: str = "") -> bool:
        """Sends a bot startup notification."""
        message = f"🟢 <b>{bot_name}</b> запущен."
        if details:
            message += f"\n{details}"
        return self.send_message(message)
    
    def send_shutdown_message(self, bot_name: str, reason: str = "") -> bool:
        """Sends a bot shutdown notification."""
        message = f"⏹️ <b>{bot_name}</b> остановлен."
        if reason:
            message += f"\nПричина: {reason}"
        return self.send_message(message)


# ============================================================
# Quick Test
# ============================================================
if __name__ == "__main__":
    print("=== Telegram Alerter Test ===\n")
    
    # Test with fake token (will print to console only)
    alerter = TelegramAlerter(
        bot_token="12345:FAKE_TOKEN",
        chat_id="123456789",
        enabled=False  # No real API call
    )
    
    alerter.send_message("Это тестовое сообщение.")
    alerter.send_trade_signal(
        bot_name="Arbitrage Scanner",
        action="BUY",
        symbol="BTC/USDT",
        price=67000.00,
        reasoning="Spread 0.52% between Binance and OKX",
        level="INFO"
    )
    alerter.send_error("DCA Bot", "Binance API returned 403 Forbidden")
    alerter.send_startup_message("Grid ML Bot", "Symbol: ETH/USDT\nLevels: 10")
    alerter.send_shutdown_message("Sentiment Sniper", "Twitter API rate limit")
    
    print("\n✅ Telegram alerter works (console mode)!")
    print("⚠️  Set real bot_token and chat_id in config.yaml for actual Telegram messages.")