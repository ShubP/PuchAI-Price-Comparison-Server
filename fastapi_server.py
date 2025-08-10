#!/usr/bin/env python3
"""
FastAPI server that handles both health checks and MCP requests
"""
import asyncio
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import threading
import time

# Import the MCP server components
from mcp_price_comparison import mcp

# Get environment variables
TOKEN = os.environ.get("AUTH_TOKEN", "supersecret")
MY_NUMBER = os.environ.get("MY_NUMBER", "919876543210")

# Create FastAPI app
app = FastAPI(title="Price Comparison MCP Server")

@app.get("/validate")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "Price Comparison MCP Server",
        "timestamp": datetime.now().isoformat(),
        "phone_number": str(MY_NUMBER),
        "auth_token": TOKEN[:10] + "..." if len(TOKEN) > 10 else TOKEN
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Price Comparison MCP Server",
        "status": "running",
        "mcp_endpoint": "/mcp/",
        "health_check": "/validate",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/mcp/")
async def mcp_endpoint(request: Request):
    """MCP endpoint that forwards requests to the MCP server"""
    # Get the request body
    body = await request.body()
    headers = dict(request.headers)
    
    # Forward to MCP server
    # This is a simplified approach - in practice, you'd need to properly handle the MCP protocol
    return JSONResponse(
        content={
            "message": "MCP endpoint available",
            "note": "Direct MCP connection required for full functionality"
        },
        status_code=200
    )

def run_mcp_server():
    """Run the MCP server in a separate thread"""
    port = int(os.environ.get("PORT", 8080))
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🏥 Starting FastAPI Server on http://0.0.0.0:{port}")
    
    # Start MCP server in a separate thread
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()
    
    # Give MCP server time to start
    time.sleep(2)
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=port)
