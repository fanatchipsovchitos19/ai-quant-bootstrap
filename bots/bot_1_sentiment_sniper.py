"""
AI Quant Bootstrap — Bot #1: AI-Sentiment Sniper
Monitors Twitter influencers, analyzes tweet sentiment via ChatGPT,
and executes short-term long trades on positive sentiment spikes.
"""

import sys
import os
import io
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.journal import log_trade
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config, print_config_summary
from lib.log import setup_logger
from lib.exchange import ExchangeClient
from lib.ai_client import AIClient
from lib.telegram_alerter import TelegramAlerter
from lib.helpers import format_usdt, format_percent, timestamp_local, extract_tickers_from_text


class SentimentSniper:
    """
    Watches Twitter accounts for crypto mentions.
    When a positive tweet appears, enters a short-term long position.
    """

    def __init__(self, config) -> None:
        self.cfg = config
        self.logger = setup_logger("SentimentSniper", config.general.log_level)
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

        # State
        self.tweets_processed = 0
        self.trades_executed = 0
        self.total_pnl = 0.0
        self.active_trades = []  # list of {'symbol', 'entry_price', 'entry_time', 'quantity'}
        self.processed_tweet_ids = set()  # avoid duplicate processing

    # ============================================================
    # Twitter Monitoring (simulated — uses cached tweets)
    # ============================================================

    def _fetch_recent_tweets(self) -> list[dict]:
        """
        Fetches recent tweets from monitored accounts.
        Uses Twitter API v2 if credentials available, otherwise simulated mode.
        Returns list of {'id', 'author', 'text', 'created_at'}.
        """
        bearer_token = self.cfg.api_keys.twitter_bearer_token

        # If real Twitter API key is set, use it
        if bearer_token and "ВАШ" not in bearer_token:
            return self._fetch_tweets_from_api(bearer_token)
        else:
            return self._fetch_tweets_simulated()

    def _fetch_tweets_from_api(self, bearer_token: str) -> list[dict]:
        """Fetches real tweets from Twitter API v2."""
        try:
            import requests

            accounts = self.cfg.bot_sentiment.monitored_accounts
            all_tweets = []

            for username in accounts:
                # Get user ID first
                user_url = f"https://api.twitter.com/2/users/by/username/{username}"
                headers = {"Authorization": f"Bearer {bearer_token}"}
                resp = requests.get(user_url, headers=headers, timeout=10)

                if resp.status_code != 200:
                    self.logger.debug(f"Cannot fetch user {username}: {resp.status_code}")
                    continue

                user_id = resp.json().get("data", {}).get("id")
                if not user_id:
                    continue

                # Get recent tweets
                tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
                params = {
                    "max_results": 5,
                    "tweet.fields": "created_at",
                    "exclude": "retweets,replies"
                }
                resp = requests.get(tweets_url, headers=headers, params=params, timeout=10)

                if resp.status_code == 200:
                    for tweet in resp.json().get("data", []):
                        tweet_id = tweet["id"]
                        if tweet_id not in self.processed_tweet_ids:
                            all_tweets.append({
                                "id": tweet_id,
                                "author": username,
                                "text": tweet["text"],
                                "created_at": tweet.get("created_at", "")
                            })

            return all_tweets

        except Exception as e:
            self.logger.error(f"Twitter API error: {e}")
            return []

    def _fetch_tweets_simulated(self) -> list[dict]:
        """
        Simulated mode: generates sample tweets for testing.
        In production, replace with real Twitter API.
        """
        import random

        # Sample tweet templates for testing
        templates = [
            {
                "author": "elonmusk",
                "texts": [
                    "DOGE is the people's crypto! 🚀",
                    "Bitcoin is interesting. Not financial advice.",
                    "Maybe we should accept DOGE for Tesla merch again?",
                ]
            },
            {
                "author": "cz_binance",
                "texts": [
                    "BNB chain growing fast. More projects coming.",
                    "Funds are SAFU. Ignore the FUD.",
                    "New listing coming next week. Any guesses?",
                ]
            },
            {
                "author": "VitalikButerin",
                "texts": [
                    "Ethereum L2 scaling is the future. 100x cheaper transactions.",
                    "SOL has some interesting tech, but centralization concerns remain.",
                ]
            },
        ]

        all_tweets = []
        for template in templates:
            for text in template["texts"]:
                tweet_id = f"sim_{hash(text) % 1000000}"
                if tweet_id not in self.processed_tweet_ids:
                    all_tweets.append({
                        "id": tweet_id,
                        "author": template["author"],
                        "text": text,
                        "created_at": datetime.now().isoformat()
                    })

        return all_tweets

    # ============================================================
    # Sentiment Analysis
    # ============================================================

    def _analyze_tweet(self, tweet: dict) -> dict:
        """
        Runs AI sentiment analysis on a tweet.
        Returns {'score': float, 'token': str, 'reasoning': str} or None.
        """
        if not self.ai.enabled:
            # Fallback: simple keyword heuristic
            text = tweet["text"].upper()
            for token in self.cfg.bot_sentiment.monitored_tokens:
                if token.upper() in text:
                    score = 0.7  # Neutral-positive default
                    if any(w in text for w in ["🚀", "MOON", "BULLISH", "GREAT", "BEST", "FUTURE"]):
                        score = 0.9
                    elif any(w in text for w in ["SCAM", "RUG", "CRASH", "FUD"]):
                        score = 0.2
                    return {
                        "score": score,
                        "token_mentioned": token,
                        "reasoning": "Heuristic fallback (no AI key set)"
                    }
            return None

        # AI analysis
        result = self.ai.evaluate_sentiment(tweet["text"], tweet["author"])
        return result

    # ============================================================
    # Trade Execution
    # ============================================================

    def _execute_trade(self, token: str, reasoning: str) -> None:
        """Enters a long position on the token."""
        symbol = f"{token}/USDT"
        amount = self.cfg.general.default_position_size

        # Check if token is available on exchange
        ticker = self.exchange.fetch_ticker(symbol)
        if not ticker:
            self.logger.warning(f"{symbol} not available on exchange. Skipping.")
            return

        price = ticker["last"]

        # Execute buy
        order = self.exchange.market_buy(symbol, amount)
        if order:
            self.trades_executed += 1
            trade = {
                "symbol": symbol,
                "entry_price": price,
                "entry_time": datetime.now(),
                "quantity": amount / price,
                "take_profit": price * (1 + self.cfg.bot_sentiment.take_profit_percent / 100),
                "stop_loss": price * (1 - self.cfg.bot_sentiment.stop_loss_percent / 100),
                "exit_time": datetime.now() + timedelta(minutes=self.cfg.bot_sentiment.trade_duration_minutes),
                "reasoning": reasoning,
            }
            self.active_trades.append(trade)

            log_trade(
                bot_name="SentimentSniper",
                action="BUY",
                symbol=symbol,
                price=price,
                quantity=trade["quantity"],
                amount_usdt=amount,
                reasoning=reasoning,
            )

            self.logger.info(
                f"🟢 TRADE OPENED: {symbol} @ {format_usdt(price)} "
                f"(TP: {format_usdt(trade['take_profit'])}, SL: {format_usdt(trade['stop_loss'])})"
            )

            self.telegram.send_trade_signal(
                bot_name="Sentiment Sniper",
                action="BUY",
                symbol=symbol,
                price=price,
                reasoning=reasoning,
                level="INFO"
            )

    def _check_exits(self) -> None:
        """Checks if any active trades should be closed."""
        for trade in self.active_trades[:]:  # iterate copy
            symbol = trade["symbol"]
            ticker = self.exchange.fetch_ticker(symbol)
            if not ticker:
                continue

            current_price = ticker["last"]
            should_exit = False
            exit_reason = ""

            # Check take profit
            if current_price >= trade["take_profit"]:
                should_exit = True
                exit_reason = f"Take profit hit: {format_usdt(trade['take_profit'])}"
            # Check stop loss
            elif current_price <= trade["stop_loss"]:
                should_exit = True
                exit_reason = f"Stop loss hit: {format_usdt(trade['stop_loss'])}"
            # Check time limit
            elif datetime.now() >= trade["exit_time"]:
                should_exit = True
                exit_reason = "Time limit reached (15 min)"

            if should_exit:
                self._close_trade(trade, current_price, exit_reason)

    def _close_trade(self, trade: dict, current_price: float, reason: str) -> None:
        """Closes a trade and calculates PnL."""
        symbol = trade["symbol"]


        log_trade(
                bot_name="SentimentSniper",
                action="SELL",
                symbol=symbol,
                price=current_price,
                quantity=trade["quantity"],
                amount_usdt=current_price * trade["quantity"],
                pnl=pnl,
                pnl_percent=((current_price - trade["entry_price"]) / trade["entry_price"]) * 100,
                reasoning=reason,
            )

        # Execute sell
        order = self.exchange.market_sell(symbol, trade["quantity"])
        if order:
            pnl = (current_price - trade["entry_price"]) * trade["quantity"]
            self.total_pnl += pnl
            self.active_trades.remove(trade)

            pnl_str = f"+{format_usdt(pnl)}" if pnl >= 0 else f"-{format_usdt(abs(pnl))}"
            self.logger.info(f"🔴 TRADE CLOSED: {symbol} @ {format_usdt(current_price)} | PnL: {pnl_str} | {reason}")

            self.telegram.send_trade_signal(
                bot_name="Sentiment Sniper",
                action="SELL",
                symbol=symbol,
                price=current_price,
                reasoning=f"{reason}. PnL: {pnl_str}",
                level="INFO"
            )

    # ============================================================
    # Stats
    # ============================================================

    def _print_stats(self) -> None:
        self.logger.info("=" * 50)
        self.logger.info("  📊 SENTIMENT SNIPER STATS")
        self.logger.info(f"  Tweets processed: {self.tweets_processed}")
        self.logger.info(f"  Trades executed: {self.trades_executed}")
        self.logger.info(f"  Active trades: {len(self.active_trades)}")
        self.logger.info(f"  Total PnL: {format_usdt(self.total_pnl)}")
        self.logger.info("=" * 50)

    # ============================================================
    # Main Loop
    # ============================================================

    def run(self) -> None:
        self.logger.info("=" * 55)
        self.logger.info("🚀 Sentiment Sniper STARTED")
        self.logger.info(f"   Monitored tokens: {', '.join(self.cfg.bot_sentiment.monitored_tokens)}")
        self.logger.info(f"   Monitored accounts: {', '.join(self.cfg.bot_sentiment.monitored_accounts)}")
        self.logger.info(f"   Sentiment threshold: {self.cfg.bot_sentiment.sentiment_threshold}")
        self.logger.info(f"   Trade duration: {self.cfg.bot_sentiment.trade_duration_minutes}min")
        self.logger.info(f"   TP: {format_percent(self.cfg.bot_sentiment.take_profit_percent/100)}")
        self.logger.info(f"   SL: {format_percent(self.cfg.bot_sentiment.stop_loss_percent/100)}")
        self.logger.info("=" * 55)

        self.telegram.send_startup_message(
            "Sentiment Sniper",
            f"Токены: {', '.join(self.cfg.bot_sentiment.monitored_tokens)}\n"
            f"Аккаунты: {', '.join(self.cfg.bot_sentiment.monitored_accounts)}\n"
            f"AI: {'✅' if self.ai.enabled else '⚠️ (heuristic mode)'}"
        )

        try:
            while True:
                # Check exits for active trades
                self._check_exits()

                # Fetch and process tweets
                tweets = self._fetch_recent_tweets()

                for tweet in tweets:
                    if tweet["id"] in self.processed_tweet_ids:
                        continue

                    self.processed_tweet_ids.add(tweet["id"])
                    self.tweets_processed += 1

                    self.logger.info(f"🐦 New tweet from @{tweet['author']}: {tweet['text'][:80]}...")

                    # Analyze sentiment
                    analysis = self._analyze_tweet(tweet)

                    if analysis is None:
                        self.logger.debug("  → No token detected or AI unavailable.")
                        continue

                    score = analysis.get("score", 0)
                    token = analysis.get("token_mentioned", "NONE")
                    reasoning = analysis.get("reasoning", "")

                    self.logger.info(f"  → Token: {token}, Score: {score:.2f}, Reasoning: {reasoning}")

                    # Check if above threshold
                    if token != "NONE" and score >= self.cfg.bot_sentiment.sentiment_threshold:
                        self.logger.info(f"  🎯 Signal! {token} sentiment {score:.2f} > {self.cfg.bot_sentiment.sentiment_threshold}")
                        self._execute_trade(token, reasoning)
                    else:
                        self.logger.debug(f"  → Below threshold ({self.cfg.bot_sentiment.sentiment_threshold}). Ignored.")

                # Stats
                self._print_stats()

                # Sleep
                self.logger.info(f"⏰ Sleeping {self.cfg.general.scan_interval_seconds}s...")
                time.sleep(self.cfg.general.scan_interval_seconds)

        except KeyboardInterrupt:
            self.logger.info("⏹️  Shutdown signal received.")
        except Exception as e:
            self.logger.error(f"❌ Fatal error: {e}")
            self.telegram.send_error("Sentiment Sniper", str(e))
        finally:
            # Close all active trades
            for trade in self.active_trades:
                ticker = self.exchange.fetch_ticker(trade["symbol"])
                if ticker:
                    self._close_trade(trade, ticker["last"], "Bot shutdown")
            self._print_stats()
            self.telegram.send_shutdown_message(
                "Sentiment Sniper",
                f"Твитов: {self.tweets_processed}\nСделок: {self.trades_executed}\nPnL: {format_usdt(self.total_pnl)}"
            )


def main():
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        config = load_config(config_path)
        if not config.bot_sentiment.enabled:
            print("⏸️  Sentiment Sniper disabled in config.")
            return
        print_config_summary(config)
        bot = SentimentSniper(config)
        bot.run()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()