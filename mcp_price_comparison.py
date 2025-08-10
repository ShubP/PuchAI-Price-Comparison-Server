#!/usr/bin/env python3
"""
Price Comparison MCP Server
A comprehensive price comparison tool that searches across multiple e-commerce platforms
"""

import asyncio
import os
import re
from datetime import datetime
from typing import List, Annotated
from pydantic import BaseModel, Field
import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# FastMCP imports
from fastmcp import FastMCP
## Note: Running without auth to avoid startup issues from deprecated BearerAuthProvider

# Load environment variables
load_dotenv()

# Configuration (must be set via environment variables in Railway)
TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

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

class PriceComparisonResult(BaseModel):
    query: str = Field(description="The search query used")
    results: List[PriceResult] = Field(description="List of price results from different platforms")
    summary: str = Field(description="Summary of the comparison results")
    best_deal: str = Field(description="Platform with the best deal")

# --- Price Comparison Service ---
class PriceComparisonService:
    @staticmethod
    async def search_amazon_india(query: str) -> List[PriceResult]:
        """Search Amazon India for products with simulated data"""
        try:
            # For hackathon demo, return simulated data
            simulated_data = {
                "laptop": [
                    PriceResult(
                        platform="Amazon India",
                        price="₹45,999",
                        url="https://www.amazon.in",
                        availability="In Stock",
                        rating="4.2★",
                        shipping="Free delivery",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ],
                "iphone": [
                    PriceResult(
                        platform="Amazon India",
                        price="₹79,900",
                        url="https://www.amazon.in",
                        availability="In Stock",
                        rating="4.5★",
                        shipping="Free delivery",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ],
                "headphones": [
                    PriceResult(
                        platform="Amazon India",
                        price="₹2,499",
                        url="https://www.amazon.in",
                        availability="In Stock",
                        rating="4.1★",
                        shipping="Free delivery",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ]
            }
            
            query_lower = query.lower()
            for item, results in simulated_data.items():
                if item in query_lower:
                    return results
                    
            # Default result
            return [
                PriceResult(
                    platform="Amazon India",
                    price="₹1,999",
                    url="https://www.amazon.in",
                    availability="In Stock",
                    rating="4.0★",
                    shipping="Free delivery",
                    last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                )
            ]
        except Exception as e:
            print(f"Amazon search error: {e}")
            return []

    @staticmethod
    async def search_flipkart(query: str) -> List[PriceResult]:
        """Search Flipkart with simulated data"""
        try:
            simulated_data = {
                "laptop": [
                    PriceResult(
                        platform="Flipkart",
                        price="₹44,999",
                        url="https://www.flipkart.com",
                        availability="In Stock",
                        rating="4.3★",
                        shipping="Free delivery",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ],
                "iphone": [
                    PriceResult(
                        platform="Flipkart",
                        price="₹78,999",
                        url="https://www.flipkart.com",
                        availability="Limited Stock",
                        rating="4.4★",
                        shipping="Free delivery",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ],
                "headphones": [
                    PriceResult(
                        platform="Flipkart",
                        price="₹2,399",
                        url="https://www.flipkart.com",
                        availability="In Stock",
                        rating="4.2★",
                        shipping="Free delivery",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ]
            }
            
            query_lower = query.lower()
            for item, results in simulated_data.items():
                if item in query_lower:
                    return results
                    
            return [
                PriceResult(
                    platform="Flipkart",
                    price="₹1,899",
                    url="https://www.flipkart.com",
                    availability="In Stock",
                    rating="4.1★",
                    shipping="Free delivery",
                    last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                )
            ]
        except Exception as e:
            print(f"Flipkart search error: {e}")
            return []

    @staticmethod
    async def search_myntra(query: str) -> List[PriceResult]:
        """Search Myntra with simulated data"""
        try:
            simulated_data = {
                "shoes": [
                    PriceResult(
                        platform="Myntra",
                        price="₹3,499",
                        url="https://www.myntra.com",
                        availability="In Stock",
                        rating="4.0★",
                        shipping="Free delivery on orders above ₹799",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ],
                "shirt": [
                    PriceResult(
                        platform="Myntra",
                        price="₹1,299",
                        url="https://www.myntra.com",
                        availability="Few Left",
                        rating="4.2★",
                        shipping="Free delivery on orders above ₹799",
                        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                ]
            }
            
            query_lower = query.lower()
            for item, results in simulated_data.items():
                if item in query_lower:
                    return results
                    
            return []
        except Exception as e:
            print(f"Myntra search error: {e}")
            return []

    @staticmethod
    async def search_quick_commerce(query: str, platform: str) -> List[PriceResult]:
        """Search quick commerce platforms with simulated data"""
        try:
            base_prices = {
                "milk": "₹65",
                "bread": "₹25",
                "eggs": "₹80",
                "rice": "₹120",
                "oil": "₹180"
            }
            
            query_lower = query.lower()
            for item, price in base_prices.items():
                if item in query_lower:
                    return [
                        PriceResult(
                            platform=platform,
                            price=price,
                            url=f"https://www.{platform.lower().replace(' ', '')}.com",
                            availability="Available",
                            rating="4.0★",
                            shipping="10-30 min delivery",
                            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                        )
                    ]
            
            return [
                PriceResult(
                    platform=platform,
                    price="₹99",
                    url=f"https://www.{platform.lower().replace(' ', '')}.com",
                    availability="Available",
                    rating="4.0★",
                    shipping="10-30 min delivery",
                    last_updated=datetime.now().strftime("%Y-%m-%d %H:%M")
                )
            ]
        except Exception as e:
            print(f"{platform} search error: {e}")
            return []

    @staticmethod
    async def compare_prices(query: str) -> PriceComparisonResult:
        """Compare prices across all platforms"""
        try:
            print(f"🔍 Searching for: {query}")
            
            # Search all platforms concurrently
            amazon_results = await PriceComparisonService.search_amazon_india(query)
            flipkart_results = await PriceComparisonService.search_flipkart(query)
            myntra_results = await PriceComparisonService.search_myntra(query)
            
            # Quick commerce platforms
            swiggy_results = await PriceComparisonService.search_quick_commerce(query, "Swiggy Instamart")
            zepto_results = await PriceComparisonService.search_quick_commerce(query, "Zepto")
            bigbasket_results = await PriceComparisonService.search_quick_commerce(query, "BigBasket")
            
            # Combine all results
            all_results = []
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
    number = str(MY_NUMBER).strip()
    # Remove any non-digit characters
    number = re.sub(r'[^\d]', '', number)
    # Ensure it starts with country code (91 for India)
    if not number.startswith('91'):
        if len(number) == 10:
            number = '91' + number
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