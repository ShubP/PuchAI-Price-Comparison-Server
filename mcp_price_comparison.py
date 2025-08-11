#!/usr/bin/env python3
"""
Price Comparison MCP Server
A comprehensive price comparison tool that searches across multiple e-commerce platforms
"""

import asyncio
import os
import re
from datetime import datetime
from typing import List, Annotated, Optional
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

# FastMCP imports
from fastmcp import FastMCP
## Note: Running without auth to avoid startup issues from deprecated BearerAuthProvider

# Load environment variables
load_dotenv()

# Configuration (must be set via environment variables in Railway)
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY")

# Debug log for environment configuration
print(f"[Startup] MY_NUMBER env raw: {MY_NUMBER}")

# Validation
assert MY_NUMBER is not None, "MY_NUMBER is required (set Railway env var to your PuchAI phone in {country_code}{number} format, e.g., 919876543210)"

# (Auth disabled for now to ensure stable deployment)

# --- Data Models ---
class PriceResult(BaseModel):
    platform: str = Field(description="Name of the e-commerce platform")
    title: str = Field(description="Product title as returned by Google Shopping")
    price: str = Field(description="Price of the product")
    url: str = Field(description="URL to the product page")
    last_updated: str = Field(description="When this price was last updated")
    quantity: Optional[str] = Field(default="", description="Detected pack size/quantity, e.g., 500 ml, 1 kg")

class PriceComparisonResult(BaseModel):
    query: str = Field(description="The search query used")
    results: List[PriceResult] = Field(description="List of price results from different platforms")
    summary: str = Field(description="Summary of the comparison results")
    best_deal: str = Field(description="Platform with the best deal")

# --- Price Comparison Service ---
class PriceComparisonService:
    PRODUCT_SIZE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s?(ml|l|g|kg|pcs|pc|pack|packet|tablets|capsules)", re.IGNORECASE)
    # Tokens that indicate flavors/variants we should avoid when the user didn't specify any
    VARIANT_EXCLUDE_TOKENS = {
        "zero", "diet", "sugar free", "sugar-free", "sugarfree",
        "lite", "light", "max", "extra", "charged", "plus",
        "cherry", "blast", "berry", "peach", "lemon", "orange",
        "mango", "vanilla", "strawberry", "mint", "masala",
        "lychee", "cola zero", "caffeine-free",
    }
    
    @staticmethod
    def normalize_query(user_query: str) -> str:
        if not user_query:
            return ""
        q = user_query.lower().strip()
        noise = [
            "find me", "find", "cheapest", "lowest price", "price of",
            "buy", "for", "please", "best price",
        ]
        for word in noise:
            q = q.replace(word, " ")
        q = re.sub(r"\s+", " ", q).strip()
        return q

    @staticmethod
    def extract_quantity(text: str) -> str:
        if not text:
            return ""
        m = PriceComparisonService.PRODUCT_SIZE_REGEX.search(text)
        if m:
            value, unit = m.group(1), m.group(2)
            unit = unit.lower()
            if unit == "l":
                unit = "L"
            return f"{value} {unit}"
        return ""

    @staticmethod
    def has_explicit_quantity_in_query(query: str) -> bool:
        return bool(PriceComparisonService.PRODUCT_SIZE_REGEX.search(query or ""))

    @staticmethod
    def query_variant_tokens(query: str) -> set:
        q = (query or "").lower()
        return {t for t in PriceComparisonService.VARIANT_EXCLUDE_TOKENS if t in q}

    @staticmethod
    def title_contains_any(title: str, tokens: set) -> bool:
        t = (title or "").lower()
        return any(tok in t for tok in tokens)

    @staticmethod
    def filter_out_variants_if_generic(results: List["PriceResult"], query: str) -> List["PriceResult"]:
        """If the query is generic (no variant mentioned), drop results containing variant tokens.
        Never filters when the user includes variant tokens in the query.
        """
        tokens_in_query = PriceComparisonService.query_variant_tokens(query)
        if tokens_in_query:
            return results
        exclude = PriceComparisonService.VARIANT_EXCLUDE_TOKENS
        filtered: List[PriceComparisonResult] = []
        for r in results:
            if PriceComparisonService.title_contains_any(getattr(r, "title", ""), exclude):
                continue
            filtered.append(r)
        return filtered or results

    @staticmethod
    def filter_by_query_quantity_if_any(results: List["PriceResult"], query: str) -> List["PriceResult"]:
        """If the query contains a specific quantity, keep only matching results."""
        m = PriceComparisonService.PRODUCT_SIZE_REGEX.search(query or "")
        if not m:
            return results
        query_value = m.group(1)
        query_unit = m.group(2).lower()
        if query_unit == "l":
            query_unit = "L"
        query_qty = f"{query_value} {query_unit}"
        matched = [r for r in results if (r.quantity or "").lower().replace("l", "L") == query_qty]
        return matched or results

    @staticmethod
    def filter_to_mode_quantity_if_generic(results: List["PriceResult"], query: str) -> List["PriceResult"]:
        """When no explicit quantity in query, prefer the most common detected quantity across results."""
        if PriceComparisonService.has_explicit_quantity_in_query(query):
            return results
        # Count non-empty quantities
        counts: dict[str, int] = {}
        for r in results:
            q = (r.quantity or "").strip()
            if q:
                counts[q] = counts.get(q, 0) + 1
        if not counts:
            return results
        # Choose the most common quantity (mode)
        mode_qty = max(counts.items(), key=lambda kv: kv[1])[0]
        filtered = [r for r in results if (r.quantity or "") == mode_qty]
        return filtered or results

    @staticmethod
    def get_domain(url: str) -> str:
        try:
            return url.split("//", 1)[-1].split("/", 1)[0]
        except Exception:
            return ""

    @staticmethod
    def map_allowed_platform(url: str, source_hint: str | None = None) -> Optional[str]:
        """Return canonical platform name if URL or source belongs to an allowed provider.

        Allowed providers: Amazon, Blinkit, Zepto, Swiggy Instamart
        """
        # Prefer explicit source name when provided by Serper
        if source_hint:
            s = source_hint.lower()
            if "amazon" in s:
                return "Amazon"
            if "blinkit" in s:
                return "Blinkit"
            if "zepto" in s:
                return "Zepto"
            if "instamart" in s or "swiggy" in s:
                return "Swiggy Instamart"

        if not url:
            return None
        u = url.lower()
        # Quick commerce / grocery
        if ("swiggy.com" in u) and ("instamart" in u):
            return "Swiggy Instamart"
        if ("blinkit.com" in u) or ("blinkit.app.link" in u):
            return "Blinkit"
        if ("zeptonow.com" in u) or ("zepto.app.link" in u) or (".zepto" in u):
            return "Zepto"
        # E-commerce
        if ("amazon.in" in u) or ("amazon.com" in u) or ("amzn.to" in u) or ("a.co" in u):
            return "Amazon"
        return None
    @staticmethod
    async def search_via_serper_shopping(query: str) -> List[PriceResult]:
        """Use Serper Google Shopping API when SERPER_API_KEY is provided."""
        if not SERPER_API_KEY:
            return []
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://google.serper.dev/shopping",
                    headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                    json={"q": query, "gl": "in", "hl": "en"},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                items = data.get("shopping", []) or data.get("results", [])
                results: List[PriceResult] = []
                for it in items[:20]:
                    title = it.get("title") or it.get("name") or "Product"
                    link = it.get("link") or it.get("url") or ""
                    price = it.get("price") or it.get("priceText") or it.get("price_from") or ""
                    source = it.get("source") or PriceComparisonService.get_domain(link) or ""
                    if not link:
                        continue
                    quantity = PriceComparisonService.extract_quantity(title)
                    canonical = PriceComparisonService.map_allowed_platform(link, source)
                    if canonical is None:
                        # Skip non-allowed providers entirely
                        continue
                    results.append(
                        PriceResult(
                            platform=str(canonical),
                            title=str(title),
                            price=str(price),
                            url=link,
                            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            quantity=quantity,
                        )
                    )
                return results
        except Exception as e:
            print(f"Serper shopping error: {e}")
            return []
    # All DuckDuckGo and site scraping helpers removed to comply with Serper-only sourcing

    @staticmethod
    async def compare_prices(query: str) -> PriceComparisonResult:
        """Compare prices using only Google Shopping (Serper) and restrict to Amazon, Blinkit, Zepto, Swiggy Instamart.

        If no results from the allowed providers are found, summary explicitly states that we couldn't find
        the requested product on online quick commerce sites.
        """
        try:
            print(f"🔍 Searching for: {query}")
            normalized_query = PriceComparisonService.normalize_query(query)
            serper_results = await PriceComparisonService.search_via_serper_shopping(normalized_query)

            # Step 1: remove unwanted variants if user asked generic item
            step1 = PriceComparisonService.filter_out_variants_if_generic(serper_results, normalized_query)
            # Step 2: if user specified a quantity in the query, keep only that size
            step2 = PriceComparisonService.filter_by_query_quantity_if_any(step1, normalized_query)
            # Step 3: if user didn't specify size, prefer the most common quantity
            all_results: List[PriceResult] = PriceComparisonService.filter_to_mode_quantity_if_generic(step2, normalized_query)

            if not all_results:
                return PriceComparisonResult(
                    query=query,
                    results=[],
                    summary="We couldn't find the requested product on online quick commerce sites.",
                    best_deal="No results available",
                )

            # Find best deal by numeric price value when present
            best_deal = "No results found"
            prices_with_platform: List[tuple[float, str]] = []
            for result in all_results:
                price_num_str = re.sub(r"[^\d.]", "", result.price)
                if price_num_str:
                    try:
                        prices_with_platform.append((float(price_num_str), result.platform))
                    except Exception:
                        pass
            if prices_with_platform:
                best_price, best_platform = min(prices_with_platform, key=lambda x: x[0])
                best_deal = f"{best_platform} - ₹{best_price:,.0f}"

            platforms_set = {r.platform for r in all_results}
            summary = f"Found {len(all_results)} results across {len(platforms_set)} platforms"

            return PriceComparisonResult(
                query=query,
                results=all_results,
                summary=summary,
                best_deal=best_deal,
            )
        except Exception as e:
            print(f"Price comparison error: {e}")
            return PriceComparisonResult(
                query=query,
                results=[],
                summary="We couldn't find the requested product on online quick commerce sites.",
                best_deal="No results available",
            )

# --- Initialize MCP Server ---
mcp = FastMCP(
    "Price Comparison MCP Server"
)

# --- Tool: validate (required by PuchAI) ---
@mcp.tool
async def validate(
    bearer_token: Annotated[str, Field(description="Bearer token provided by Puch during /mcp connect")]
) -> str:
    """Return the server owner's phone number after validating the bearer token.

    The returned value must be in the format {country_code}{number} (e.g., 919876543210).
    """
    expected = (TOKEN or "").strip()
    provided = (bearer_token or "").strip()
    if expected and provided != expected:
        # Do not leak details; simply refuse
        raise Exception("Invalid bearer token")

    number = str(MY_NUMBER or "").strip()
    number = re.sub(r"[^\d]", "", number)
    if not number:
        raise Exception("Server owner phone number not configured")
    if not number.startswith("91") and len(number) == 10:
        number = "91" + number
    return number

# --- Tool: price_comparison ---
@mcp.tool(description="Search prices for a product across Amazon, Blinkit, Zepto, and Swiggy Instamart using Google Shopping (Serper). Returns title, price and direct product links.")
async def price_comparison(
    query: Annotated[str, Field(description="Product or item to compare prices for, e.g., 'Amul milk 500ml', 'iPhone 15 128GB'")]
) -> PriceComparisonResult:
    return await PriceComparisonService.compare_prices(query)

@mcp.tool(description="Alias of price_comparison")
async def price_search(
    query: Annotated[str, Field(description="Alias for price_comparison; product or item to search")]
) -> PriceComparisonResult:
    return await PriceComparisonService.compare_prices(query)

# Removed extra tools to keep the server focused on the required price search functionality

# --- Run MCP Server ---
async def main():
    port = int(os.environ.get("PORT", 8086))
    print(f"🚀 Starting Price Comparison MCP server on http://0.0.0.0:{port}")
    print("🛒 Available tools:")
    print("   • validate - Validate server connection")
    print("   • price_comparison - Search prices across Amazon, Blinkit, Zepto, Swiggy Instamart")
    print("   • price_search - Alias for price_comparison")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
