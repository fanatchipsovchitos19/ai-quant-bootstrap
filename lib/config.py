"""
AI Quant Bootstrap — Configuration Loader
Reads config.yaml, validates values, returns typed AppConfig object.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    import yaml
except ImportError:
    print("❌ PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


# ============================================================
# Data Classes (typed config sections)
# ============================================================

@dataclass
class ApiKeys:
    binance_api_key: str = ""
    binance_secret: str = ""
    binance_testnet: bool = True
    bybit_api_key: str = ""
    bybit_secret: str = ""
    okx_api_key: str = ""
    okx_secret: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    routerai_api_key: str = ""
    routerai_model_complex: str = "deepseek/deepseek-chat"
    routerai_model_fast: str = "openai/gpt-4o-mini"
    ollama_enabled: bool = False
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    twitter_bearer_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class GeneralConfig:
    primary_exchange: str = "binance"
    quote_currency: str = "USDT"
    max_positions: int = 3
    default_position_size: float = 100.0
    slippage_percent: float = 0.5
    scan_interval_seconds: int = 30
    log_level: str = "INFO"


@dataclass
class BotSentimentConfig:
    enabled: bool = True
    monitored_tokens: list = field(default_factory=lambda: ["BTC", "ETH", "DOGE", "SOL"])
    monitored_accounts: list = field(default_factory=lambda: ["elonmusk", "cz_binance"])
    sentiment_threshold: float = 0.8
    trade_duration_minutes: int = 15
    take_profit_percent: float = 5.0
    stop_loss_percent: float = 3.0


@dataclass
class BotArbitrageConfig:
    enabled: bool = True
    exchanges: list = field(default_factory=lambda: ["binance", "bybit", "okx"])
    symbols_mode: str = "common"
    min_spread_percent: float = 0.4
    auto_execute: bool = False
    max_trade_amount: float = 500.0


@dataclass
class BotDCAConfig:
    enabled: bool = True
    symbol: str = "BTC/USDT"
    order_amount: float = 50.0
    interval_hours: int = 4
    ai_news_check: bool = True
    max_dca_orders: int = 20
    max_drawdown_percent: float = 30.0


@dataclass
class BotGridConfig:
    enabled: bool = True
    symbol: str = "ETH/USDT"
    grid_levels: int = 10
    grid_spacing_percent: float = 1.0
    order_amount: float = 50.0
    ml_lookback_days: int = 7
    recalculate_hours: int = 24
    min_balance_usdt: float = 100.0


@dataclass
class BotDexSniperConfig:
    enabled: bool = False
    chain: str = "bsc"
    rpc_url: str = "https://bsc-dataseed.binance.org"
    factory_address: str = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
    buy_amount_native: float = 0.05
    gas_mode: str = "auto"
    take_profit_percent: float = 20.0
    ai_scam_filter: bool = True
    min_liquidity_usd: float = 5000.0


@dataclass
class NotificationsConfig:
    telegram: bool = True
    console: bool = True


@dataclass
class AppConfig:
    """Root config aggregating all sections."""
    api_keys: ApiKeys = field(default_factory=ApiKeys)
    general: GeneralConfig = field(default_factory=GeneralConfig)
    bot_sentiment: BotSentimentConfig = field(default_factory=BotSentimentConfig)
    bot_arbitrage: BotArbitrageConfig = field(default_factory=BotArbitrageConfig)
    bot_dca: BotDCAConfig = field(default_factory=BotDCAConfig)
    bot_grid: BotGridConfig = field(default_factory=BotGridConfig)
    bot_dex_sniper: BotDexSniperConfig = field(default_factory=BotDexSniperConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)


# ============================================================
# Config Loader
# ============================================================

def load_config(config_path: str = "config.yaml") -> AppConfig:
    """
    Loads config.yaml from the given path and returns a validated AppConfig object.
    
    Args:
        config_path: Path to config.yaml file.
    
    Returns:
        AppConfig instance with all settings.
    
    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If critical fields are missing or invalid.
    """
    
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"❌ Config file not found: {path.absolute()}\n"
            f"   Make sure 'config.yaml' is in the same folder as the bot script."
        )
    
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    if raw is None:
        raise ValueError(f"❌ Config file is empty: {path.absolute()}")
    
    # --- Parse API Keys ---
    api = raw.get("api_keys", {})
    api_keys = ApiKeys(
        binance_api_key=api.get("binance", {}).get("api_key", ""),
        binance_secret=api.get("binance", {}).get("api_secret", ""),
        binance_testnet=api.get("binance", {}).get("testnet", True),
        bybit_api_key=api.get("bybit", {}).get("api_key", ""),
        bybit_secret=api.get("bybit", {}).get("api_secret", ""),
        okx_api_key=api.get("okx", {}).get("api_key", ""),
        okx_secret=api.get("okx", {}).get("api_secret", ""),
        openai_api_key=api.get("openai", {}).get("api_key", ""),
        openai_model=api.get("openai", {}).get("model", "gpt-4o-mini"),
        routerai_api_key=api.get("routerai", {}).get("api_key", ""),
        routerai_model_complex=api.get("routerai", {}).get("model_complex", "deepseek/deepseek-chat"),
        routerai_model_fast=api.get("routerai", {}).get("model_fast", "openai/gpt-4o-mini"),
        ollama_enabled=bool(api.get("ollama", {}).get("enabled", False)),
        ollama_url=api.get("ollama", {}).get("url", "http://localhost:11434"),
        ollama_model=api.get("ollama", {}).get("model", "llama3.2"),
        twitter_bearer_token=api.get("twitter", {}).get("bearer_token", ""),
        telegram_bot_token=api.get("telegram", {}).get("bot_token", ""),
        telegram_chat_id=api.get("telegram", {}).get("chat_id", ""),
    )
    
    # --- Parse General ---
    gen = raw.get("general", {})
    general = GeneralConfig(
        primary_exchange=gen.get("primary_exchange", "binance"),
        quote_currency=gen.get("quote_currency", "USDT"),
        max_positions=int(gen.get("max_positions", 3)),
        default_position_size=float(gen.get("default_position_size", 100)),
        slippage_percent=float(gen.get("slippage_percent", 0.5)),
        scan_interval_seconds=int(gen.get("scan_interval_seconds", 30)),
        log_level=gen.get("log_level", "INFO"),
    )
    
    # --- Parse Bot Configs ---
    bot_sentiment = BotSentimentConfig(**raw.get("bot_sentiment", {}))
    bot_arbitrage = BotArbitrageConfig(**raw.get("bot_arbitrage", {}))
    bot_dca = BotDCAConfig(**raw.get("bot_dca", {}))
    bot_grid = BotGridConfig(**raw.get("bot_grid", {}))
    bot_dex_sniper = BotDexSniperConfig(**raw.get("bot_dex_sniper", {}))
    notifications = NotificationsConfig(**raw.get("notifications", {}))
    
    config = AppConfig(
        api_keys=api_keys,
        general=general,
        bot_sentiment=bot_sentiment,
        bot_arbitrage=bot_arbitrage,
        bot_dca=bot_dca,
        bot_grid=bot_grid,
        bot_dex_sniper=bot_dex_sniper,
        notifications=notifications,
    )
    
    # --- Validate ---
    _validate_config(config)
    
    return config


def _validate_config(config: AppConfig) -> None:
    """Raises ValueError if config contains invalid values."""
    
    # At least one exchange API key should be set
    has_exchange = any([
        "ВАШ" not in config.api_keys.binance_api_key and config.api_keys.binance_api_key,
        "ВАШ" not in config.api_keys.bybit_api_key and config.api_keys.bybit_api_key,
    ])
    if not has_exchange:
        import sys as _sys
        _sys.stderr.write("⚠️  WARNING: No exchange API keys set. Bots won't be able to trade.\n")
        _sys.stderr.write("   Edit config.yaml and add your Binance or Bybit API keys.\n")
    
    # Validate numeric ranges
    if not (0 < config.general.slippage_percent <= 10):
        raise ValueError(f"slippage_percent must be between 0 and 10, got {config.general.slippage_percent}")
    
    if not (0 < config.bot_sentiment.sentiment_threshold <= 1):
        raise ValueError(f"sentiment_threshold must be between 0 and 1, got {config.bot_sentiment.sentiment_threshold}")
    
    if config.bot_arbitrage.min_spread_percent <= 0:
        raise ValueError(f"min_spread_percent must be > 0, got {config.bot_arbitrage.min_spread_percent}")
    
    if config.bot_dca.max_dca_orders <= 0:
        raise ValueError(f"max_dca_orders must be > 0, got {config.bot_dca.max_dca_orders}")


def print_config_summary(config: AppConfig) -> None:
    """Prints a human-readable summary of the loaded config."""
    
    print("\n" + "=" * 55)
    print("   📋 CONFIG SUMMARY")
    print("=" * 55)
    print(f"   Exchange: {config.general.primary_exchange.upper()}")
    print(f"   Testnet: {config.api_keys.binance_testnet}")
    print(f"   Position size: ${config.general.default_position_size}")
    print(f"   Max positions: {config.general.max_positions}")
    print(f"   Slippage: {config.general.slippage_percent}%")
    print(f"   Log level: {config.general.log_level}")
    print("-" * 55)
    print(f"   Bot 1 (Sentiment): {'✅ ON' if config.bot_sentiment.enabled else '⏸️  OFF'}")
    print(f"   Bot 2 (Arbitrage): {'✅ ON' if config.bot_arbitrage.enabled else '⏸️  OFF'}")
    print(f"   Bot 3 (DCA): {'✅ ON' if config.bot_dca.enabled else '⏸️  OFF'}")
    print(f"   Bot 4 (Grid ML): {'✅ ON' if config.bot_grid.enabled else '⏸️  OFF'}")
    print(f"   Bot 5 (DEX Sniper): {'✅ ON' if config.bot_dex_sniper.enabled else '⏸️  OFF'}")
    print(f"   Telegram alerts: {'✅ ON' if config.notifications.telegram else '⏸️  OFF'}")
    print("=" * 55 + "\n")


# ============================================================
# Quick Test
# ============================================================
if __name__ == "__main__":
    try:
        cfg = load_config("config.yaml")
        print_config_summary(cfg)
        print("✅ Config loaded successfully!")
    except FileNotFoundError as e:
        print(e)
    except ValueError as e:
        print(f"❌ Config validation error: {e}")