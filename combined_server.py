#!/usr/bin/env python3
"""
Combined server that runs both health check and MCP server
"""
import asyncio
import os
from datetime import datetime
from aiohttp import web
import json
import subprocess
import sys
import signal
import threading
import time

# Import the MCP server components
from mcp_price_comparison import mcp

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

def run_mcp_server():
    """Run the MCP server in a separate thread"""
    port = int(os.environ.get("MCP_PORT", 8086))
    print(f"🚀 Starting MCP server on port {port}")
    
    async def mcp_main():
        await mcp.run_async("streamable-http", host="0.0.0.0", port=port)
    
    # Run MCP server in a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(mcp_main())
    except KeyboardInterrupt:
        print("🛑 Shutting down MCP server...")
    finally:
        loop.close()

async def main():
    """Main function to run both servers"""
    port = int(os.environ.get("PORT", 8080))
    print(f"🏥 Starting Combined Server on http://0.0.0.0:{port}")
    
    # Start MCP server in a separate thread
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()
    
    # Give MCP server time to start
    await asyncio.sleep(2)
    
    # Start health check server
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"✅ Combined Server running on port {port}")
    print(f"🔗 Health check: http://0.0.0.0:{port}/validate")
    print(f"🔗 Root endpoint: http://0.0.0.0:{port}/")
    print(f"🔗 MCP endpoint: http://0.0.0.0:8086/mcp/")
    
    # Keep the server running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("🛑 Shutting down combined server...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
