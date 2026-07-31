"""
AI Quant Bootstrap — Trade Journal
Records all trades to CSV for dashboard and analysis.
"""

import csv
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


JOURNAL_DIR = Path("data")
JOURNAL_FILE = JOURNAL_DIR / "trades.csv"

# CSV columns
COLUMNS = [
    "timestamp",
    "bot_name",
    "action",
    "symbol",
    "price",
    "quantity",
    "amount_usdt",
    "pnl",
    "pnl_percent",
    "reasoning",
]


def init_journal() -> None:
    """Creates journal file with headers if it doesn't exist."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    
    if not JOURNAL_FILE.exists():
        with open(JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)


def log_trade(
    bot_name: str,
    action: str,
    symbol: str,
    price: float,
    quantity: float,
    amount_usdt: float,
    pnl: float = 0.0,
    pnl_percent: float = 0.0,
    reasoning: str = "",
) -> None:
    """Records a trade to the CSV journal."""
    init_journal()
    
    try:
        with open(JOURNAL_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(),
                str(bot_name).replace(",", ";"),
                str(action).replace(",", ";"),
                str(symbol).replace(",", ";"),
                f"{price:.6f}",
                f"{quantity:.6f}",
                f"{amount_usdt:.2f}",
                f"{pnl:.2f}",
                f"{pnl_percent:.2f}",
                str(reasoning).replace(",", ";").replace("\n", " ")[:200],
            ])
    except Exception:
        pass  # Never crash the bot because of journal


def get_all_trades() -> list[dict]:
    """Reads all trades from journal. Skips broken rows."""
    init_journal()
    
    trades = []
    try:
        with open(JOURNAL_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get("timestamp", "")
                if not re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', ts):
                    continue
                trades.append(row)
    except Exception:
        pass
    return trades


def get_trades_by_bot(bot_name: str) -> list[dict]:
    """Returns trades for a specific bot."""
    return [t for t in get_all_trades() if t["bot_name"] == bot_name]


def get_pnl_summary() -> dict:
    """Returns PnL summary per bot."""
    trades = get_all_trades()
    summary = {}
    
    for t in trades:
        bot = t["bot_name"]
        if bot not in summary:
            summary[bot] = {"total_pnl": 0.0, "trades": 0, "wins": 0, "losses": 0}
        
        try:
            pnl = float(t["pnl"])
        except (ValueError, KeyError):
            pnl = 0.0
        
        summary[bot]["total_pnl"] += pnl
        summary[bot]["trades"] += 1
        if pnl > 0:
            summary[bot]["wins"] += 1
        elif pnl < 0:
            summary[bot]["losses"] += 1
    
    return summary


# Quick test
if __name__ == "__main__":
    init_journal()
    log_trade("TestBot", "BUY", "BTC/USDT", 65000.0, 0.001, 65.0, reasoning="Test buy")
    log_trade("TestBot", "SELL", "BTC/USDT", 66000.0, 0.001, 66.0, pnl=1.0, pnl_percent=1.54, reasoning="Test sell")
    
    trades = get_all_trades()
    print(f"Total trades: {len(trades)}")
    for t in trades:
        print(f"  {t['timestamp']} | {t['bot_name']} | {t['action']} {t['symbol']} | PnL: ${t['pnl']}")