#!/usr/bin/env python3
import os
import sys
import asyncio

# Ensure MY_NUMBER is set before importing the server module (module asserts on import)
os.environ.setdefault("MY_NUMBER", "911234567890")

import mcp_price_comparison as m

async def run(query: str):
    print(f"Query: {query}")
    print(f"SERPER_API_KEY present: {bool(os.environ.get('SERPER_API_KEY'))}")
    result = await m.PriceComparisonService.compare_prices(query)
    print(f"Summary: {result.summary}")
    print("Results:")
    for r in result.results:
        qty = f" [{r.quantity}]" if getattr(r, 'quantity', '') else ""
        print(f"- {r.platform}: {r.title} — {r.price}{qty} -> {r.url}")

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "amul milk 500ml"
    asyncio.run(run(q))
