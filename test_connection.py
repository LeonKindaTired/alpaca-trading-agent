#!/usr/bin/env python3
"""Simple test to verify Alpaca connectivity"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.config.settings import get_settings
from backend.app.data.live_alpaca import LiveAlpacaClient

def test_connection():
    print("Testing Alpaca connection...")
    settings = get_settings()

    if not settings.alpaca_api_key or settings.alpaca_api_key.startswith("your_"):
        print("ERROR: Set ALPACA_API_KEY / ALPACA_SECRET_KEY in .env")
        return False

    try:
        client = LiveAlpacaClient(settings)
        print("[OK] Client created")

        account = client.get_account()
        print(f"[OK] Account connected: equity=${account.equity:,.2f}")
        print(f"  Status: {account.status}")
        print(f"  Buying Power: ${account.buying_power:,.2f}")

        quote = client.get_latest_quote("SPY")
        print(f"[OK] SPY quote: bid=${quote.bid:.2f}, ask=${quote.ask:.2f}")

        # Test options chain (might be empty on weekend)
        try:
            contracts = client.get_option_contracts("SPY", limit=5)
            print(f"[OK] Option chain query: {len(contracts)} contracts returned")
        except Exception as e:
            print(f"[WARN] Option chain query failed (may be expected on weekend): {e}")

        return True

    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)