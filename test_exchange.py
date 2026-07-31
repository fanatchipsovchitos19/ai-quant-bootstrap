import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from lib.exchange import ExchangeClient
from lib.helpers import format_usdt

for ex in ["binance", "bybit", "okx"]:
    print(f"\nTesting {ex.upper()}...")
    client = ExchangeClient(ex)
    if client.test_connection():
        price = client.fetch_price("BTC/USDT")
        if price:
            print(f"  ✅ BTC: {format_usdt(price)}")
        else:
            print(f"  ❌ fetch_price() returned None")
    else:
        print(f"  ❌ Connection failed")
    print()