"""Minimal scanner to debug hanging — v3 with full logging."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

print("Importing...")
from lib.exchange import ExchangeClient
from lib.helpers import format_usdt, format_percent
print("Imports OK")

TOP_PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

exchanges = {}
for name in ["binance", "bybit", "okx"]:
    print(f"Creating {name} client...")
    try:
        ex = ExchangeClient(name)
        print(f"  ✅ {name} created")
        if ex.test_connection():
            print(f"  ✅ {name} connected")
            exchanges[name] = ex
        else:
            print(f"  ❌ {name} connection failed")
    except Exception as e:
        print(f"  ❌ {name} ERROR: {e}")

print(f"\nExchanges ready: {list(exchanges.keys())}")

if len(exchanges) < 2:
    print("Not enough exchanges. Exiting.")
    exit()

print("\nStarting scan loop...\n")
scan = 0
while True:
    scan += 1
    print(f"=== Scan #{scan} ===")
    for symbol in TOP_PAIRS:
        prices = {}
        for name, ex in exchanges.items():
            try:
                price = ex.fetch_price(symbol)
                if price:
                    prices[name] = price
                    print(f"  {name}: {symbol} = {format_usdt(price)}")
                else:
                    print(f"  {name}: {symbol} = None ❌")
            except Exception as e:
                print(f"  ERROR {name} {symbol}: {e}")
        if len(prices) >= 2:
            min_ex = min(prices, key=prices.get)
            max_ex = max(prices, key=prices.get)
            spread = ((prices[max_ex] - prices[min_ex]) / prices[min_ex]) * 100
            print(f"  → Spread: {spread:.3f}% (Buy {min_ex}, Sell {max_ex})")
        else:
            print(f"  → Only {len(prices)} prices, no arbitrage.")
    print(f"  Sleeping 5s...")
    sys.stdout.flush()
    time.sleep(5)