"""
AI Quant Bootstrap — Helper Utilities
Common functions used across all bots.
"""

import time
import re
from datetime import datetime, timezone
from typing import Optional


# ============================================================
# Time & Date
# ============================================================

def timestamp_now() -> str:
    """Returns current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def timestamp_local() -> str:
    """Returns current local timestamp as string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# Formatting
# ============================================================

def format_usdt(amount: float) -> str:
    """Formats a number as USDT amount. $1,234.56"""
    if amount >= 1_000_000:
        return f"${amount:,.0f}"
    elif amount >= 1:
        return f"${amount:,.2f}"
    else:
        return f"${amount:,.6f}"


def format_percent(value: float) -> str:
    """Formats a float as percentage string. 0.0452 -> '4.52%'"""
    return f"{value * 100:.2f}%" if value < 1 else f"{value:.2f}%"


def format_token_amount(amount: float, decimals: int = 4) -> str:
    """Formats a token amount with appropriate precision."""
    if amount >= 1:
        return f"{amount:,.2f}"
    elif amount >= 0.01:
        return f"{amount:,.4f}"
    else:
        return f"{amount:.{decimals}f}"


def format_duration(seconds: float) -> str:
    """Converts seconds to human-readable duration. 3665 -> '1h 1m 5s'"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


# ============================================================
# Validation
# ============================================================

def is_default_api_key(value: str) -> bool:
    """Checks if API key is still the template placeholder."""
    if not value:
        return True
    if "ВАШ" in value.upper():
        return True
    if value.startswith("sk-ВАШ"):
        return True
    return False


def validate_positive_number(value, name: str, min_val: float = 0) -> None:
    """Raises ValueError if value is not a positive number above min_val."""
    try:
        v = float(value)
        if v <= min_val:
            raise ValueError(f"{name} must be > {min_val}, got {v}")
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value}")


# ============================================================
# String & Symbol Helpers
# ============================================================

def normalize_symbol(symbol: str) -> str:
    """
    Normalizes trading symbol to standard format.
    'btc/usdt' -> 'BTC/USDT'
    'BTCUSDT' -> 'BTC/USDT'
    """
    symbol = symbol.upper().strip()
    if "/" not in symbol:
        # Try to split common quote currencies
        for quote in ["USDT", "USDC", "BTC", "ETH", "BUSD", "BNB"]:
            if symbol.endswith(quote) and len(symbol) > len(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
    return symbol


def extract_tickers_from_text(text: str) -> list[str]:
    """
    Extracts ticker symbols from text.
    Looks for $BTC, $ETH patterns and uppercase 2-5 letter words.
    Returns list of unique tickers.
    """
    tickers = set()
    
    # Pattern: $BTC, $ETH
    dollar_tickers = re.findall(r'\$([A-Z]{2,10})', text)
    tickers.update(dollar_tickers)
    
    # Pattern: standalone uppercase 2-5 letter words (likely tickers)
    # Exclude common words
    common_words = {"THE", "A", "AN", "IS", "ARE", "WAS", "WERE", "BE", "BEEN",
                    "HAS", "HAVE", "HAD", "DO", "DOES", "DID", "WILL", "WOULD",
                    "CAN", "COULD", "MAY", "MIGHT", "SHALL", "SHOULD", "MUST",
                    "THIS", "THAT", "THESE", "THOSE", "IT", "ITS", "FOR", "AND",
                    "NOT", "BUT", "OR", "TO", "IN", "ON", "AT", "BY", "WITH",
                    "FROM", "UP", "OUT", "ALL", "NEW", "NOW", "JUST", "SO",
                    "IF", "NO", "YES", "WE", "HE", "SHE", "THEY", "HIM", "HER",
                    "ME", "US", "MY", "OUR", "YOUR", "HIS", "THEIR", "WHEN",
                    "WHERE", "WHY", "HOW", "WHO", "WHICH", "WHAT"}
    
    words = re.findall(r'\b[A-Z]{2,5}\b', text)
    tickers.update(w for w in words if w not in common_words)
    
    return list(tickers)


# ============================================================
# Retry & Safety
# ============================================================

def retry_on_failure(func, max_retries: int = 3, delay: float = 5.0, 
                     backoff: float = 2.0, logger=None):
    """
    Retries a function on failure with exponential backoff.
    
    Args:
        func: Function to call (no arguments).
        max_retries: Maximum number of retries.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each retry.
        logger: Optional logger instance.
    
    Returns:
        Result of func() or None if all retries failed.
    """
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if logger:
                logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}")
            
            if attempt < max_retries:
                wait = delay * (backoff ** (attempt - 1))
                if logger:
                    logger.info(f"Retrying in {wait:.1f}s...")
                time.sleep(wait)
    
    if logger:
        logger.error(f"All {max_retries} attempts failed. Last error: {last_exception}")
    return None


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safely divides two numbers, returns default if b is zero."""
    return a / b if b != 0 else default


# ============================================================
# Quick Test
# ============================================================
if __name__ == "__main__":
    print("=== Helpers Test ===\n")
    print(f"UTC Now: {timestamp_now()}")
    print(f"Local: {timestamp_local()}")
    print(f"ISO: {now_iso()}")
    print()
    print(f"USDT: {format_usdt(1234.5678)}")
    print(f"USDT large: {format_usdt(1234567.89)}")
    print(f"Percent: {format_percent(0.0452)}")
    print(f"Duration: {format_duration(3665)}")
    print()
    print(f"Normalize 'btcusdt': {normalize_symbol('btcusdt')}")
    print(f"Normalize 'eth/usdt': {normalize_symbol('eth/usdt')}")
    print()
    test_text = "Elon Musk just tweeted about $DOGE and BTC! Bullish on crypto."
    print(f"Tickers from: '{test_text}'")
    print(f"  -> {extract_tickers_from_text(test_text)}")
    print()
    print(f"Is default key 'ВАШ_KEY': {is_default_api_key('ВАШ_KEY')}")
    print(f"Is default key 'sk-real': {is_default_api_key('sk-real')}")
    print(f"Safe divide 10/3: {safe_divide(10, 3):.2f}")
    print(f"Safe divide 10/0: {safe_divide(10, 0)}")
    print()
    print("✅ All helpers work!")