#!/usr/bin/env python3
"""Retry BTC long with slippage buffer to account for proxy latency."""
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

async def main():
    config = Configuration(host=URL)
    config.proxy = PROXY
    client = ApiClient(configuration=config)
    order_api = OrderApi(client)

    # Get fresh price
    ob = await order_api.order_book_orders(BTC_MARKET, 1)
    best_ask_str = ob.asks[0].price
    best_ask = int(best_ask_str.replace(".", ""))
    print(f"BTC best ask: {best_ask_str} -> {best_ask}")

    # Add 0.5% slippage buffer for proxy latency
    price_with_slippage = int(best_ask * 1.005)
    print(f"Price with 0.5% buffer: {price_with_slippage}")

    # $15 USDC -> BTC amount
    btc_amount = 15.0 / float(best_ask_str)
    base_amount = round(btc_amount * 100000)  # size_decimals=5
    print(f"base_amount: {base_amount}")

    # Create signer
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

    client_order_index = int(time.time()) % 100000
    print(f"\nPlacing: BUY {base_amount} units BTC-PERP at limit {price_with_slippage}")

    try:
        create_order, resp, err = await signer.create_market_order(
            market_index=BTC_MARKET,
            client_order_index=client_order_index,
            base_amount=base_amount,
            avg_execution_price=price_with_slippage,  # limit with slippage
            is_ask=False,
        )
        if err:
            print(f"ERROR: {err}")
        else:
            print(f"SUCCESS! resp={resp}")
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")

    # Verify position
    await asyncio.sleep(2)
    account_api = lighter.AccountApi(client)
    result = await account_api.account(by="index", value=str(ACCOUNT_INDEX))
    for acc in result.accounts:
        for p in acc.positions:
            if p.position and float(p.position) != 0:
                print(f"Position confirmed: market={p.market_index} size={p.position} entry={p.avg_entry_price}")

    await client.close()
    await signer.api_client.close()

asyncio.run(main())
