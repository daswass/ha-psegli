#!/usr/bin/env python3
"""Automated login for PSEG Long Island using the automation addon."""

import logging
import os
from typing import Optional

import aiohttp

from .const import DEFAULT_ADDON_URL

logger = logging.getLogger(__name__)

# Sentinel for MFA required - caller should use complete_mfa_login(code)
MFA_REQUIRED = "MFA_REQUIRED"

ADDON_SLUG_SUFFIX = "psegli-automation"
LOGIN_TIMEOUT = aiohttp.ClientTimeout(total=300)
HEALTH_TIMEOUT = aiohttp.ClientTimeout(total=10)

_resolved_addon_url: Optional[str] = None


async def _check_url_health(session: aiohttp.ClientSession, base_url: str) -> bool:
    """Return True when the addon health endpoint responds healthy."""
    try:
        async with session.get(f"{base_url}/health", timeout=HEALTH_TIMEOUT) as resp:
            if resp.status != 200:
                return False
            result = await resp.json()
            return result.get("status") == "healthy"
    except Exception as exc:
        logger.debug("Addon health check failed for %s: %s", base_url, exc)
        return False


async def _discover_addon_base_url(session: aiohttp.ClientSession) -> Optional[str]:
    """Discover the running addon URL via the Home Assistant Supervisor API."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with session.get(
            "http://supervisor/addons",
            headers=headers,
            timeout=HEALTH_TIMEOUT,
        ) as resp:
            if resp.status != 200:
                return None
            payload = await resp.json()
            for addon in payload.get("data", {}).get("addons", []):
                slug = addon.get("slug", "")
                if not slug.endswith(ADDON_SLUG_SUFFIX):
                    continue
                if addon.get("state") != "started":
                    continue
                host = slug.replace("_", "-")
                return f"http://{host}:8000"
    except Exception as exc:
        logger.debug("Supervisor addon discovery failed: %s", exc)
    return None


async def get_addon_base_url(force_refresh: bool = False) -> str:
    """Resolve the addon base URL, preferring the internal Docker hostname on HA OS."""
    global _resolved_addon_url

    if _resolved_addon_url and not force_refresh:
        return _resolved_addon_url

    candidates: list[str] = []
    async with aiohttp.ClientSession() as session:
        discovered = await _discover_addon_base_url(session)
        if discovered:
            candidates.append(discovered)

        candidates.extend(
            [
                "http://801d8584-psegli-automation:8000",
                "http://psegli-automation:8000",
                DEFAULT_ADDON_URL,
            ]
        )

        seen: set[str] = set()
        for base_url in candidates:
            if base_url in seen:
                continue
            seen.add(base_url)
            if await _check_url_health(session, base_url):
                _resolved_addon_url = base_url
                logger.info("Using PSEG automation addon at %s", base_url)
                return base_url

    logger.warning(
        "Could not reach PSEG automation addon; falling back to %s",
        DEFAULT_ADDON_URL,
    )
    _resolved_addon_url = DEFAULT_ADDON_URL
    return DEFAULT_ADDON_URL


async def check_addon_health() -> bool:
    """Check if the addon is available and healthy."""
    base_url = await get_addon_base_url()
    async with aiohttp.ClientSession() as session:
        return await _check_url_health(session, base_url)


async def get_fresh_cookies(
    username: str,
    password: str,
    mfa_code: Optional[str] = None,
    mfa_method: str = "sms",
) -> Optional[str]:
    """Get fresh cookies using the automation addon.

    Returns:
        Cookie string on success, MFA_REQUIRED when MFA is needed (call complete_mfa_login),
        or None on failure.
    """
    base_url = await get_addon_base_url()
    if not await check_addon_health():
        logger.warning("Addon not available or unhealthy at %s", base_url)
        return None

    login_data = {
        "username": username,
        "password": password,
        "mfa_method": mfa_method or "sms",
    }
    if mfa_code:
        login_data["mfa_code"] = mfa_code

    try:
        logger.debug("Sending login request to %s/login", base_url)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/login",
                json=login_data,
                timeout=LOGIN_TIMEOUT,
            ) as resp:
                logger.debug("Addon response received: status=%s", resp.status)
                if resp.status != 200:
                    logger.error("Addon request failed with status %s", resp.status)
                    return None

                result = await resp.json()
                logger.debug("Addon response: %s", result)
                if result.get("success") and result.get("cookies"):
                    logger.debug("Successfully obtained cookies from addon")
                    return result["cookies"]
                if result.get("mfa_required"):
                    logger.info(
                        "PSEG MFA required - use complete_mfa_login(code) with code from email or SMS"
                    )
                    return MFA_REQUIRED
                logger.error("Addon login failed: %s", result.get("error", "Unknown error"))
                return None
    except Exception as exc:
        logger.error("Failed to get cookies from addon at %s: %s", base_url, exc)
        return None


async def complete_mfa_login(code: str) -> Optional[str]:
    """Complete login after MFA - provide the verification code from your email or SMS."""
    base_url = await get_addon_base_url()
    try:
        logger.debug("Sending MFA code to %s/login/mfa", base_url)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/login/mfa",
                json={"code": code},
                timeout=LOGIN_TIMEOUT,
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success") and result.get("cookies"):
                        logger.debug("MFA successful, cookies obtained")
                        return result["cookies"]
                logger.error("MFA failed: %s", await resp.text())
                return None
    except Exception as exc:
        logger.error("Failed to complete MFA at %s: %s", base_url, exc)
        return None
