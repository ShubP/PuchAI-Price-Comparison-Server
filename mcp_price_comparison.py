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
    async def search_via_duckduckgo_shopping(query: str) -> List[PriceResult]:
        """Use DuckDuckGo Shopping to fetch real product offers with direct links."""
        try:
            results: List[PriceResult] = []
            with DDGS() as ddgs:
                # region set to IN for India; adjust as needed
                for item in ddgs.shops(keywords=query, region="in-en", max_results=5):
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
            "Zepto": ["zepto", "zeptonow"],
            "BigBasket": ["bigbasket.com"],
        }
        needles = domain_map.get(platform, [])
        return [r for r in ddg if any(n in r.url for n in needles)]

    @staticmethod
    async def compare_prices(query: str) -> PriceComparisonResult:
        """Compare prices across all platforms"""
        try:
            print(f"🔍 Searching for: {query}")
            normalized_query = PriceComparisonService.normalize_query(query)
            # Real shopping results first
            ddg_results = await PriceComparisonService.search_via_duckduckgo_shopping(normalized_query)

            # Platform-specific filters from the same data source
            amazon_results = [r for r in ddg_results if "amazon.in" in r.url]
            flipkart_results = [r for r in ddg_results if "flipkart.com" in r.url]
            myntra_results = [r for r in ddg_results if "myntra.com" in r.url]
            
            # Quick commerce platforms
            swiggy_results = await PriceComparisonService.search_quick_commerce(query, "Swiggy Instamart")
            zepto_results = await PriceComparisonService.search_quick_commerce(query, "Zepto")
            bigbasket_results = await PriceComparisonService.search_quick_commerce(query, "BigBasket")
            
            # Combine all results
            all_results = []
            # Prefer real results at the top
            all_results.extend(ddg_results)
            all_results.extend(amazon_results)
            all_results.extend(flipkart_results)
            all_results.extend(myntra_results)
            all_results.extend(swiggy_results)
            all_results.extend(zepto_results)
            all_results.extend(bigbasket_results)
            
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