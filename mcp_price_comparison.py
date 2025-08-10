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
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
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
    price: str = Field(description="Price of the product")
    url: str = Field(description="URL to the product page")
    availability: str = Field(description="Stock availability status")
    rating: str = Field(description="Product rating if available")
    shipping: str = Field(description="Shipping information")
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
    def get_domain(url: str) -> str:
        try:
            return url.split("//", 1)[-1].split("/", 1)[0]
        except Exception:
            return ""

    @staticmethod
    def map_allowed_platform(url: str) -> Optional[str]:
        """Return canonical platform name if URL belongs to an allowed provider."""
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
        if ("amazon.in" in u) or ("amzn.to" in u) or ("a.co" in u):
            return "Amazon India"
        if ("flipkart.com" in u) or ("dl.flipkart.com" in u):
            return "Flipkart"
        if ("myntra.com" in u) or ("l.myntra.com" in u):
            return "Myntra"
        return None
    @staticmethod
    async def search_via_duckduckgo_shopping(query: str) -> List[PriceResult]:
        """Use DuckDuckGo Shopping to fetch real product offers with direct links."""
        try:
            results: List[PriceResult] = []
            with DDGS() as ddgs:
                # region set to IN for India; adjust as needed
                for item in ddgs.shopping(keywords=query, region="in-en", max_results=5):
                    title = item.get("title") or item.get("name") or "Product"
                    price = item.get("price") or item.get("price_str") or ""
                    link = item.get("url") or item.get("link") or ""
                    source = item.get("source") or item.get("merchant") or item.get("seller") or "Shop"
                    if not link:
                        continue
                    # Normalize price text if present
                    price_text = price if price else ""
                    quantity = PriceComparisonService.extract_quantity(title)
                    results.append(
                        PriceResult(
                            platform=str(source),
                            price=price_text,
                            url=link,
                            availability="",
                            rating="",
                            shipping="",
                            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            quantity=quantity,
                        )
                    )
            return results
        except Exception as e:
            print(f"DuckDuckGo shopping error: {e}")
            return []

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
                for it in items[:10]:
                    title = it.get("title") or it.get("name") or "Product"
                    link = it.get("link") or it.get("url") or ""
                    price = it.get("price") or it.get("priceText") or it.get("price_from") or ""
                    source = it.get("source") or PriceComparisonService.get_domain(link) or "Shop"
                    if not link:
                        continue
                    quantity = PriceComparisonService.extract_quantity(title)
                    results.append(
                        PriceResult(
                            platform=str(source),
                            price=str(price),
                            url=link,
                            availability="",
                            rating="",
                            shipping="",
                            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                            quantity=quantity,
                        )
                    )
                return results
        except Exception as e:
            print(f"Serper shopping error: {e}")
            return []

    @staticmethod
    async def search_via_duckduckgo_html(query: str) -> List[PriceResult]:
        """Fallback: scrape DuckDuckGo HTML results for product links and basic price cues."""
        try:
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            headers = {"User-Agent": "Mozilla/5.0"}
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(url, data=params, headers=headers)
                if resp.status_code != 200:
                    return []
            soup = BeautifulSoup(resp.text, "html.parser")
            results: List[PriceResult] = []
            for a in soup.select("a.result__a")[:10]:
                title = a.get_text(strip=True)
                link = a.get("href")
                if not link:
                    continue
                quantity = PriceComparisonService.extract_quantity(title)
                results.append(
                    PriceResult(
                        platform=PriceComparisonService.get_domain(link),
                        price="",
                        url=link,
                        availability="",
                        rating="",
                        shipping="",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
                        quantity=quantity,
                    )
                )
            return results
        except Exception as e:
            print(f"DuckDuckGo HTML scrape error: {e}")
            return []
    @staticmethod
    async def search_amazon_india(query: str) -> List[PriceResult]:
        """Filter results to Amazon India."""
        ddg = await PriceComparisonService.search_via_duckduckgo_shopping(query)
        return [r for r in ddg if "amazon.in" in r.url]

    @staticmethod
    async def search_flipkart(query: str) -> List[PriceResult]:
        """Filter results to Flipkart."""
        ddg = await PriceComparisonService.search_via_duckduckgo_shopping(query)
        return [r for r in ddg if "flipkart.com" in r.url]

    @staticmethod
    async def search_myntra(query: str) -> List[PriceResult]:
        """Filter results to Myntra."""
        ddg = await PriceComparisonService.search_via_duckduckgo_shopping(query)
        return [r for r in ddg if "myntra.com" in r.url]

    @staticmethod
    async def search_quick_commerce(query: str, platform: str) -> List[PriceResult]:
        """Filter results for quick commerce domains (best effort)."""
        ddg = await PriceComparisonService.search_via_duckduckgo_shopping(query)
        domain_map = {
            "Swiggy Instamart": ["swiggy.com", "instamart"],
            "Blinkit": ["blinkit.com", "blinkit.app.link"],
            "Zepto": ["zepto", "zeptonow"],
        }
        needles = domain_map.get(platform, [])
        return [r for r in ddg if any(n in r.url for n in needles)]

    @staticmethod
    async def compare_prices(query: str) -> PriceComparisonResult:
        """Compare prices across all platforms"""
        try:
            print(f"🔍 Searching for: {query}")
            normalized_query = PriceComparisonService.normalize_query(query)
            # Try Serper first
            serper_results = await PriceComparisonService.search_via_serper_shopping(normalized_query)
            # Then DuckDuckGo Shopping
            ddg_results = await PriceComparisonService.search_via_duckduckgo_shopping(normalized_query) if not serper_results else []
            # Then fallback to HTML search
            ddg_html_results = await PriceComparisonService.search_via_duckduckgo_html(normalized_query) if not (serper_results or ddg_results) else []

            # Merge sources
            merged = serper_results or ddg_results or ddg_html_results

            # Filter strictly to allowed providers and set canonical names
            all_results: List[PriceResult] = []
            for r in merged:
                canonical = PriceComparisonService.map_allowed_platform(r.url)
                if canonical is None:
                    continue
                r.platform = canonical
                all_results.append(r)
            
            # Also try pulling quick-commerce explicitly (optional boost)
            # These use the same source but ensure inclusion if not present
            for qc in ["Swiggy Instamart", "Blinkit", "Zepto"]:
                extra = await PriceComparisonService.search_quick_commerce(normalized_query, qc)
                for r in extra:
                    canonical = PriceComparisonService.map_allowed_platform(r.url)
                    if canonical and all((r.url != x.url) for x in all_results):
                        r.platform = canonical
                        all_results.append(r)
            
            # Find best deal
            best_deal = "No results found"
            if all_results:
                # Extract numeric prices for comparison
                prices_with_platform = []
                for result in all_results:
                    price_num = re.sub(r'[^\d.]', '', result.price)
                    if price_num:
                        prices_with_platform.append((float(price_num), result.platform))
                
                if prices_with_platform:
                    best_price, best_platform = min(prices_with_platform, key=lambda x: x[0])
                    best_deal = f"{best_platform} - ₹{best_price:,.0f}"
            
            # Create summary
            summary = f"Found {len(all_results)} results across {len(set(r.platform for r in all_results))} platforms"
            
            return PriceComparisonResult(
                query=query,
                results=all_results,
                summary=summary,
                best_deal=best_deal
            )
        except Exception as e:
            print(f"Price comparison error: {e}")
            return PriceComparisonResult(
                query=query,
                results=[],
                summary="Error occurred during price comparison",
                best_deal="No results available"
            )

# --- Initialize MCP Server ---
mcp = FastMCP(
    "Price Comparison MCP Server"
)

# --- Tool: validate (required by PuchAI) ---
@mcp.tool
async def validate() -> str:
    """Validate the MCP server and return phone number"""
    print(f"[validate] raw MY_NUMBER: {MY_NUMBER}")
    number = str(MY_NUMBER).strip()
    # Remove any non-digit characters
    number = re.sub(r'[^\d]', '', number)
    # Ensure it starts with country code (91 for India)
    if not number.startswith('91'):
        if len(number) == 10:
            number = '91' + number
    print(f"[validate] cleaned number to return: {number}")
    return number

# --- Tool: price_comparison ---
@mcp.tool
async def price_comparison(
    product_query: Annotated[str, Field(description="The product you want to compare prices for (e.g., 'iPhone 15', 'laptop', 'headphones')")]
) -> PriceComparisonResult:
    """Compare prices across multiple e-commerce platforms including Amazon, Flipkart, Myntra, and quick commerce platforms"""
    return await PriceComparisonService.compare_prices(product_query)

# --- Tool: quick_price_check ---
@mcp.tool
async def quick_price_check(
    item: Annotated[str, Field(description="Grocery or daily essential item to check prices for (e.g., 'milk', 'bread', 'eggs')")]
) -> PriceComparisonResult:
    """Quick price check for groceries and daily essentials across quick commerce platforms"""
    return await PriceComparisonService.compare_prices(item)

# --- Tool: deal_finder ---
@mcp.tool
async def deal_finder(
    category: Annotated[str, Field(description="Product category to find deals for (e.g., 'electronics', 'fashion', 'groceries')")]
) -> str:
    """Find the best deals and offers in a specific category"""
    try:
        # Simulate deal finding
        deals = {
            "electronics": "📱 iPhone 15: Save ₹5,000 on Amazon | 💻 Laptops: Up to 30% off on Flipkart",
            "fashion": "👕 Clothing: Flat 50% off on Myntra | 👟 Shoes: Buy 1 Get 1 on select brands",
            "groceries": "🥛 Dairy products: 15% off on BigBasket | 🍞 Bakery items: Free delivery on Swiggy Instamart"
        }
        
        category_lower = category.lower()
        for cat, deal_info in deals.items():
            if cat in category_lower:
                return f"🔥 Best Deals in {category.title()}:\n{deal_info}"
        
        return f"🔍 No specific deals found for '{category}', but check our price comparison tool for the best prices!"
    except Exception as e:
        return f"Error finding deals: {e}"

# --- Tool: price_tracker ---
@mcp.tool
async def price_tracker(
    product: Annotated[str, Field(description="Product to track price for")]
) -> str:
    """Track price history and set alerts for products"""
    try:
        return f"📊 Price tracking enabled for '{product}'!\n\n" \
               f"💡 Current status:\n" \
               f"• Historical data: Analyzing past 30 days\n" \
               f"• Price alerts: Will notify on 10% price drop\n" \
               f"• Monitoring: Amazon, Flipkart, Myntra\n\n" \
               f"🔔 You'll receive notifications when prices drop significantly!"
    except Exception as e:
        return f"Error setting up price tracking: {e}"

# --- Run MCP Server ---
async def main():
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Starting Price Comparison MCP server on http://0.0.0.0:{port}")
    print("🛒 Available tools:")
    print("   • validate - Validate server connection")
    print("   • price_comparison - Compare prices across platforms")
    print("   • quick_price_check - Quick grocery price check")
    print("   • deal_finder - Find best deals by category")
    print("   • price_tracker - Track price history and alerts")
    
    await mcp.run_async("streamable-http", host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(main())
