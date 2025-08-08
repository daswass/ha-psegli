#!/usr/bin/env python3
"""Test script for PSEG Long Island Automation Addon"""

import asyncio
import aiohttp
import json

async def test_addon():
    """Test the addon endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing PSEG Long Island Automation Addon...")
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("\n1. Testing health endpoint...")
        try:
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Health check passed: {data}")
                else:
                    print(f"❌ Health check failed: {resp.status}")
                    return
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return
        
        # Test login endpoint (with dummy credentials)
        print("\n2. Testing login endpoint...")
        login_data = {
            "username": "test@example.com",
            "password": "testpassword"
        }
        
        try:
            async with session.post(
                f"{base_url}/login",
                json=login_data,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success") == False:
                        print(f"✅ Login endpoint working (expected failure): {data.get('error', 'Unknown error')}")
                    else:
                        print(f"⚠️  Unexpected success with test credentials: {data}")
                else:
                    print(f"❌ Login endpoint failed: {resp.status}")
        except Exception as e:
            print(f"❌ Login endpoint error: {e}")
    
    print("\n🎯 Addon test completed!")

if __name__ == "__main__":
    asyncio.run(test_addon())
