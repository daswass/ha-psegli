#!/usr/bin/env python3
"""Automated login for PSEG Long Island using the automation addon."""

import asyncio
import logging
import aiohttp
from typing import Dict, Optional

logger = logging.getLogger(__name__)

async def get_fresh_cookies(username: str, password: str) -> Optional[Dict[str, str]]:
    """Get fresh cookies using the automation addon."""
    try:
        logger.info("Requesting fresh cookies from PSEG automation addon...")
        
        # Try to connect to the addon
        async with aiohttp.ClientSession() as session:
            # First check if addon is available via direct port access
            try:
                async with session.get("http://localhost:8000/health", timeout=5) as resp:
                    if resp.status == 200:
                        logger.info("Addon accessible via direct port")
                        addon_base_url = "http://localhost:8000"
                    else:
                        logger.warning("Addon health check failed")
                        return None
            except Exception as e:
                logger.warning(f"Addon not available via direct port: {e}")
                return None
            
            # Request login via addon
            login_data = {
                "username": username,
                "password": password
            }
            
            async with session.post(
                f"{addon_base_url}/login",
                json=login_data,
                timeout=60  # Longer timeout for login process
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success") and result.get("cookies"):
                        logger.info("Successfully obtained cookies from addon")
                        return result["cookies"]
                    else:
                        logger.error(f"Addon login failed: {result.get('error', 'Unknown error')}")
                        return None
                else:
                    logger.error(f"Addon request failed with status {resp.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"Failed to get cookies from addon: {e}")
        return None
