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
    delivery: Optional[str] = Field(default="", description="Delivery info if available (e.g., Free delivery, 10-30 min)")

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
    # Very small brand hints for common beverages; extend as needed
    BRAND_HINTS = {
        "coke": {"coke", "coca", "coca-cola", "coca cola"},
        "coca": {"coke", "coca", "coca-cola", "coca cola"},
        "coca-cola": {"coke", "coca", "coca-cola", "coca cola"},
        "thums": {"thums", "thums up", "thumbs up"},
        "pepsi": {"pepsi"},
        "sprite": {"sprite"},
        "fanta": {"fanta"},
        "mirinda": {"mirinda"},
        "limca": {"limca"},
        "dew": {"dew", "mountain dew"},
        "7up": {"7up"},
    }

    QUICK_COMMERCE_PLATFORMS = {"Swiggy Instamart", "Blinkit", "Zepto"}

    @staticmethod
    def parse_price_number(price_text: str) -> Optional[float]:
        if not price_text:
            return None
        try:
            # Keep digits and dot; some prices like "₹40" or "40.00"
            cleaned = re.sub(r"[^\d.]", "", str(price_text))
            if cleaned == "":
                return None
            return float(cleaned)
        except Exception:
            return None

    @staticmethod
    def choose_vendor_link(preferred_platform: str, item: dict, fallback_link: str) -> str:
        """From Serper item, pick the most direct vendor link available.
        Tries several field names and prefers links containing the vendor's domain.
        """
        vendor = (preferred_platform or "").lower()
        candidates = []
        # Common fields in Serper shopping results and nested offers
        for key in ("product_link", "productLink", "merchantLink", "sourceLink", "url", "link", "redirect", "productUrl", "product_url"):
            val = item.get(key)
            if isinstance(val, str) and val:
                candidates.append(val)
        # Pick the first candidate that contains a domain matching the platform
        domain_hints = {
            "amazon": "amazon.",
            "blinkit": "blinkit.",
            "zepto": "zepto",
            "instamart": "swiggy.com",
            "swiggy": "swiggy.com",
            "jiomart": "jiomart.com",
            "bigbasket": "bigbasket.com",
        }
        hint = None
        for k, h in domain_hints.items():
            if k in vendor:
                hint = h
                break
        if hint:
            for c in candidates:
                if hint in c.lower():
                    return c
        # Fallback to the first reasonable URL or the provided fallback link
        return candidates[0] if candidates else fallback_link
    
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
    def filter_by_brand_hints_if_present(results: List["PriceResult"], query: str) -> List["PriceResult"]:
        """If the query clearly indicates a brand (e.g., coke, pepsi, thums), keep results matching that brand."""
        q = (query or "").lower()
        hinted_tokens: set[str] = set()
        for key, aliases in PriceComparisonService.BRAND_HINTS.items():
            if key in q:
                hinted_tokens.update(aliases)
        if not hinted_tokens:
            return results
        filtered: List[PriceResult] = []
        for r in results:
            title = (getattr(r, "title", "") or "").lower()
            if any(alias in title for alias in hinted_tokens):
                filtered.append(r)
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

        Allowed providers: Amazon, Blinkit, Zepto, Swiggy Instamart, JioMart Grocery, BigBasket
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
        if ("jiomart.com" in u) or ("jiomart" in u and "grocery" in u):
            return "JioMart Grocery"
        if ("bigbasket.com" in u) or ("bbdaily" in u):
            return "BigBasket"
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
                for it in items[:50]:
                    title = it.get("title") or it.get("name") or "Product"
                    link = it.get("link") or it.get("url") or ""
                    price = it.get("price") or it.get("priceText") or it.get("price_from") or ""
                    source = it.get("source") or PriceComparisonService.get_domain(link) or ""
                    delivery = it.get("delivery") or it.get("deliveryTime") or it.get("deliveryInfo") or ""
                    if not link:
                        continue
                    quantity = PriceComparisonService.extract_quantity(title)
                    canonical = PriceComparisonService.map_allowed_platform(link, source)
                    if canonical is None:
                        # Skip non-allowed providers entirely
                        continue
                    # Choose best vendor link if the default link is a Google aggregator
                    vendor_link = PriceComparisonService.choose_vendor_link(canonical, it, link)
                    # Add default quick commerce delivery hint
                    if not delivery and canonical in PriceComparisonService.QUICK_COMMERCE_PLATFORMS:
                        delivery = "10-30 min delivery"
                    results.append(
                        PriceResult(
                            platform=str(canonical),
                            title=str(title),
                            price=str(price),
                            url=vendor_link,
                            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            quantity=quantity,
                            delivery=str(delivery) if delivery else "",
                        )
                    )

                    # Also expand seller/offer listings when available to include more buying options
                    for sellers_key in ("sellers", "offers", "offer", "stores"):
                        sellers = it.get(sellers_key) or []
                        if isinstance(sellers, dict):
                            sellers = [sellers]
                        for s in sellers:
                            s_name = s.get("name") or s.get("source") or s.get("seller") or ""
                            s_link = s.get("link") or s.get("url") or ""
                            s_price = s.get("price") or s.get("priceText") or s.get("price_from") or price
                            s_delivery = s.get("delivery") or s.get("deliveryTime") or s.get("deliveryInfo") or delivery
                            if not s_link and not s_name:
                                continue
                            canonical_s = PriceComparisonService.map_allowed_platform(s_link, s_name)
                            if canonical_s is None:
                                continue
                            # Choose best vendor link for seller entry
                            vendor_s_link = PriceComparisonService.choose_vendor_link(canonical_s, s, s_link or link)
                            if not s_delivery and canonical_s in PriceComparisonService.QUICK_COMMERCE_PLATFORMS:
                                s_delivery = "10-30 min delivery"
                            results.append(
                                PriceResult(
                                    platform=str(canonical_s),
                                    title=str(title),
                                    price=str(s_price or price),
                                    url=vendor_s_link,
                                    last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    quantity=quantity,
                                    delivery=str(s_delivery) if s_delivery else "",
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

            # Sort all results by numeric price when available and compute best deal
            priced_pairs: List[tuple[float, PriceResult]] = []
            for result in all_results:
                price_num = PriceComparisonService.parse_price_number(result.price)
                if price_num is not None:
                    priced_pairs.append((price_num, result))
            if priced_pairs:
                priced_pairs.sort(key=lambda x: x[0])
                sorted_results = [r for _, r in priced_pairs] + [r for r in all_results if PriceComparisonService.parse_price_number(r.price) is None]
                all_results = sorted_results
                best_price_num, best_result = priced_pairs[0]
                best_deal = f"{best_result.platform} - ₹{best_price_num:,.0f}"
            else:
                best_deal = "No results found"

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
@mcp.tool(description="Search prices for a product across Amazon, Blinkit, Zepto, Swiggy Instamart, JioMart Grocery, and BigBasket using Google Shopping (Serper). Returns title, quantity, price, delivery info, and direct product links.")
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
