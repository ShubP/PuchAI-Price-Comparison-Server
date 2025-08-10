#!/usr/bin/env python3
"""
Simple health check server for Railway deployment
"""
import asyncio
import os
from datetime import datetime
from aiohttp import web
import json

# Get environment variables
TOKEN = os.environ.get("AUTH_TOKEN", "supersecret")
MY_NUMBER = os.environ.get("MY_NUMBER", "919876543210")

async def health_check(request):
    """Health check endpoint for Railway"""
    return web.json_response({
        "status": "healthy",
        "service": "Price Comparison MCP Server",
        "timestamp": datetime.now().isoformat(),
        "phone_number": str(MY_NUMBER),
        "auth_token": TOKEN[:10] + "..." if len(TOKEN) > 10 else TOKEN
    })

async def root(request):
    """Root endpoint"""
    return web.json_response({
        "message": "Price Comparison MCP Server",
        "status": "running",
        "mcp_endpoint": "/mcp/",
        "health_check": "/validate",
        "timestamp": datetime.now().isoformat()
    })

async def init_app():
    """Initialize the web application"""
    app = web.Application()
    app.router.add_get('/validate', health_check)
    app.router.add_get('/', root)
    return app

async def main():
    """Main function to run the health check server"""
    port = int(os.environ.get("PORT", 8080))
    print(f"🏥 Starting Health Check Server on http://0.0.0.0:{port}")
    
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"✅ Health Check Server running on port {port}")
    print(f"🔗 Health check: http://0.0.0.0:{port}/validate")
    print(f"🔗 Root endpoint: http://0.0.0.0:{port}/")
    
    # Keep the server running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("🛑 Shutting down health check server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
