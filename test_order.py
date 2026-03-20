#!/usr/bin/env python3
"""Quick test: open a BTC long market order through the proxy."""
import asyncio
import os
import time
import lighter
from lighter import SignerClient, Configuration, ApiClient, OrderApi

PROXY_USER = os.environ.get("LIGHTER_PROXY_USER", "")
PROXY_PASS = os.environ.get("LIGHTER_PROXY_PASS", "")
PROXY_HOST = os.environ.get("LIGHTER_PROXY_HOST", "64.137.96.74")
PROXY_PORT = os.environ.get("LIGHTER_PROXY_PORT", "6641")
PROXY = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}/" if PROXY_USER else None
URL = "https://mainnet.zklighter.elliot.ai"
ACCOUNT_INDEX = int(os.environ.get("LIGHTER_ACCOUNT_INDEX", "0"))
API_KEY_INDEX = 3
API_KEY_PRIVATE = os.environ.get("LIGHTER_API_PRIVATE_KEY", "")

BTC_MARKET = 1
SIZE_DECIMALS = 5  # 0.00001 BTC = 1 unit
PRICE_DECIMALS = 1  # $0.1 = 1 unit

async def main():
    # Read prices
    config = Configuration(host=URL)
    config.proxy = PROXY
    client = ApiClient(configuration=config)
    order_api = OrderApi(client)

    ob = await order_api.order_book_orders(BTC_MARKET, 1)
    best_ask_str = ob.asks[0].price
    best_ask = int(best_ask_str.replace(".", ""))
    print(f"BTC best ask: {best_ask_str} -> {best_ask}")

    # $15 USDC at market
    # At $70,977: $15 / 70977 = 0.0002113 BTC
    # In size units: 0.0002113 * 100000 = 21.13 -> 21
    usd_amount = 15.0
    btc_price = float(best_ask_str)
    btc_amount = usd_amount / btc_price
    base_amount = round(btc_amount * (10 ** SIZE_DECIMALS))
    print(f"${usd_amount} -> {btc_amount:.6f} BTC -> base_amount={base_amount}")

    # Create signer with proxy
    signer_config = Configuration(host=URL)
    signer_config.proxy = PROXY
    signer = SignerClient(
        url=URL,
        account_index=ACCOUNT_INDEX,
        api_private_keys={API_KEY_INDEX: API_KEY_PRIVATE},
    )
    signer.api_client = ApiClient(configuration=signer_config)
    signer.tx_api = lighter.TransactionApi(signer.api_client)
    signer.order_api = lighter.OrderApi(signer.api_client)

    # Place market buy order
    client_order_index = int(time.time()) % 100000
    print(f"\nPlacing: BUY {base_amount} units BTC-PERP at ~{best_ask} (market {BTC_MARKET})")

    try:
        create_order, resp, err = await signer.create_market_order(
            market_index=BTC_MARKET,
            client_order_index=client_order_index,
            base_amount=base_amount,
            avg_execution_price=best_ask,
            is_ask=False,  # BUY
        )
        if err:
            print(f"ERROR: {err}")
        else:
            print(f"SUCCESS! tx_hash={resp.tx_hash if hasattr(resp, 'tx_hash') else resp}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")

    await client.close()
    await signer.api_client.close()

asyncio.run(main())
