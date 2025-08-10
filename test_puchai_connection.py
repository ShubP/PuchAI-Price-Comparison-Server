#!/usr/bin/env python3
"""
Test script to simulate PuchAI's MCP connection
"""
import asyncio
import json
import httpx

async def test_puchai_connection():
    """Test the MCP connection exactly like PuchAI would"""
    
    url = "https://web-production-31371.up.railway.app/mcp/"
    token = "supersecret"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json, text/event-stream"
    }
    
    # Initialize request (what PuchAI sends first)
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "PuchAI",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"🔗 Testing connection to: {url}")
            print(f"🔑 Using token: {token}")
            print(f"📤 Sending initialize request...")
            
            response = await client.post(
                url,
                headers=headers,
                json=init_request,
                timeout=30.0
            )
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📥 Response Headers: {dict(response.headers)}")
            print(f"📥 Response Body: {response.text[:500]}...")
            
            if response.status_code == 200:
                print("✅ Connection successful!")
                
                # Try to list tools
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                print(f"📤 Requesting tools list...")
                tools_response = await client.post(
                    url,
                    headers=headers,
                    json=tools_request,
                    timeout=30.0
                )
                
                print(f"📥 Tools Response: {tools_response.status_code}")
                print(f"📥 Tools Body: {tools_response.text[:500]}...")
                
            else:
                print(f"❌ Connection failed with status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_puchai_connection())
