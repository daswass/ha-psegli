"""The PSEG Long Island integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_COOKIE, CONF_MFA_METHOD
from .psegli import InvalidAuth, PSEGLIClient
from .statistics import async_import_usage, date_windows, directional_points
from .auto_login import get_fresh_cookies, complete_mfa_login, check_addon_health, MFA_REQUIRED

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []

async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the PSEG Long Island component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PSEG Long Island from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Get credentials from config entry
    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)
    cookie = entry.data.get(CONF_COOKIE, "")
    
    if not username or not password:
        _LOGGER.error("No username/password provided")
        return False
    
    # If no cookie available, try to get one from the addon
    mfa_pending = False
    if not cookie:
        _LOGGER.debug("No cookie available, attempting to get fresh cookies from addon...")
        try:
            mfa_method = entry.data.get(CONF_MFA_METHOD, "sms")
            cookies = await get_fresh_cookies(username, password, mfa_method=mfa_method)
            
            if cookies and cookies != MFA_REQUIRED:
                # Cookies are already in string format from addon
                cookie_string = cookies
                cookie = cookie_string  # Update local for rest of setup
                _LOGGER.debug("Successfully obtained fresh cookies from addon")
                
                # Store cookie in config entry for future use
                hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_COOKIE: cookie_string},
                )
            elif cookies == MFA_REQUIRED:
                # Allow setup to complete - user must call enter_mfa_code with the code
                mfa_pending = True
                _LOGGER.info("PSEG requires MFA - setup will complete; call enter_mfa_code with the code")
                channel = "phone" if mfa_method == "sms" else "email"
                await hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "PSEG Integration: MFA Required",
                            "message": f"PSEG sent a verification code to your {channel}. Go to Developer Tools > Actions and call 'PSEG Long Island: Enter MFA Code' with the code.",
                            "notification_id": "psegli_mfa_required",
                        },
                    )
                )
            else:
                _LOGGER.warning("Addon not available or failed to get cookies")
        except Exception as e:
            _LOGGER.warning("Failed to get cookies from addon: %s", e)
    
    # Fail only if we have no cookie and MFA isn't pending (addon unavailable or login failed)
    if not cookie and not mfa_pending:
        _LOGGER.error("No cookie available and addon failed to provide one. Start the addon and try again, or configure a cookie manually.")
        await hass.async_create_task(
            hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "PSEG Integration: Cookie Required",
                    "message": "No authentication cookie available. Ensure the PSEG addon is running, then try again. Or go to Settings > Integrations > PSEG Long Island > Configure to provide a cookie manually.",
                    "notification_id": "psegli_cookie_required",
                },
            )
        )
        return False
    
    # Create client (cookie may be empty if MFA pending - enter_mfa_code will update it)
    client = PSEGLIClient(cookie or "")
    hass.data[DOMAIN][entry.entry_id] = client
    
    # Test connection only when we have a cookie (skip when MFA pending)
    if cookie:
        try:
            await client.test_connection()
            _LOGGER.debug("PSEG connection test successful")
        except InvalidAuth as e:
            _LOGGER.error("Authentication failed: %s", e)
            raise ConfigEntryAuthFailed("Invalid authentication")
    
    # Create coordinator for automatic updates (like Opower)
    coordinator = PSEGCoordinator(hass, entry, client)
    entry.runtime_data = coordinator
    
    # Store coordinator reference in hass.data for proper cleanup
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]['coordinator'] = coordinator
    
    # Listen for config changes (when user updates cookie via options)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Register manual service for backfilling
    async def async_update_statistics_manual(call: Any) -> None:
        """Serialize data fetches and committed cumulative imports."""
        if not hass.is_running:
            _LOGGER.info("Deferring PSEG statistics until Home Assistant is running")
            return
        days_back = call.data.get("days_back", 0)
        exports_only = call.data.get("exports_only", False)
        if isinstance(days_back, bool) or not isinstance(days_back, int) or not 0 <= days_back <= 365:
            raise ValueError("days_back must be an integer from 0 through 365")
        if not isinstance(exports_only, bool):
            raise ValueError("exports_only must be a boolean")
        lock = hass.data[DOMAIN].setdefault("statistics_lock", asyncio.Lock())
        async with lock:
            current_client = hass.data[DOMAIN][entry.entry_id]
            end = datetime.now()
            start = end - timedelta(days=days_back or 1)
            counts = {}
            for window_start, window_end in date_windows(start, end):
                historical_data = await current_client.get_usage_data(
                    start_date=window_start, end_date=window_end
                )
                chart = historical_data.get("chart_data", {})
                if not directional_points(chart, exports_only=exports_only):
                    _LOGGER.info("No matching PSEG data for %s through %s", window_start, window_end)
                    continue
                async with asyncio.timeout(120):
                    imported = await async_import_usage(hass, chart, exports_only=exports_only)
                for statistic_id, count in imported.items():
                    counts[statistic_id] = counts.get(statistic_id, 0) + count
            _LOGGER.info("PSEG statistics committed (days_back=%d): %s", days_back, counts)

    # Register the manual service
    hass.services.async_register(
        DOMAIN,
        "update_statistics",
        async_update_statistics_manual
    )
    
    # Register the cookie refresh service
    async def async_refresh_cookie(call: Any) -> None:
        """Manually refresh the PSEG authentication cookie."""
        _LOGGER.debug("Cookie refresh service called")
        
        try:
            username = entry.data.get(CONF_USERNAME)
            password = entry.data.get(CONF_PASSWORD)
            
            if not username or not password:
                _LOGGER.error("No credentials available for cookie refresh")
                return
            
            _LOGGER.debug("Attempting to refresh cookie via addon...")
            
            # Check if addon is healthy before attempting refresh
            if not await check_addon_health():
                _LOGGER.error("Addon not available or unhealthy, cannot refresh cookie")
                return
            
            # Attempt to get fresh cookies
            mfa_method = entry.data.get(CONF_MFA_METHOD, "sms")
            cookies = await get_fresh_cookies(username, password, mfa_method=mfa_method)
            
            if cookies == MFA_REQUIRED:
                channel = "phone" if mfa_method == "sms" else "email"
                _LOGGER.warning("PSEG requires MFA - check %s for code, then call enter_mfa_code service", channel)
                await hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "PSEG Integration: MFA Required",
                            "message": f"PSEG sent a verification code to your {channel}. Check your {channel}, then go to Developer Tools > Services and call 'PSEG Long Island: Enter MFA Code' with the code. Or go to Settings > Integrations > PSEG Long Island > Configure (⋮) > Options, leave cookie empty, Submit, and enter the code there.",
                            "notification_id": "psegli_mfa_required",
                        },
                    )
                )
            elif cookies:
                # Cookies are already in string format from addon
                cookie_string = cookies
                
                # Get the actual client instance from hass.data
                current_client = hass.data[DOMAIN][entry.entry_id]
                
                # Update the client with new cookie
                current_client.update_cookie(cookie_string)
                
                # Also update the coordinator's client if it exists
                if hasattr(entry, 'runtime_data') and entry.runtime_data:
                    coordinator = entry.runtime_data
                    if hasattr(coordinator, 'client'):
                        coordinator.client.update_cookie(cookie_string)
                        _LOGGER.debug("✅ Updated coordinator client cookie")
                
                _LOGGER.debug("✅ Updated client cookie: %s", cookie_string[:50] + "..." if len(cookie_string) > 50 else cookie_string)
                _LOGGER.debug("✅ Updated client session headers")
                
                # Update the config entry
                hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_COOKIE: cookie_string},
                )
                
                _LOGGER.debug("✅ Updated config entry with new cookie")
                _LOGGER.debug("Successfully refreshed cookie via addon")
                
                # Test the new cookie
                await current_client.test_connection()
                _LOGGER.debug("New cookie validation successful")
                
                # Fetch and save energy data with the new cookie
                try:
                    await async_update_statistics_manual(type("Call", (), {"data": {"days_back": 0}})())
                    _LOGGER.debug("Energy data saved after cookie refresh")
                except Exception as stats_err:
                    _LOGGER.warning("Statistics update after refresh failed: %s", stats_err)
                
                # Create a success notification
                await hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "PSEG Integration: Cookie Refreshed",
                            "message": "Successfully refreshed your PSEG authentication cookie. The integration should now work properly.",
                            "notification_id": "psegli_cookie_refreshed",
                        },
                    )
                )
                
            else:
                _LOGGER.error("Addon failed to provide fresh cookies")
                # Create an error notification
                await hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "PSEG Integration: Cookie Refresh Failed",
                            "message": "Failed to refresh your PSEG authentication cookie. Please check the addon status or provide a cookie manually.",
                            "notification_id": "psegli_cookie_refresh_failed",
                        },
                    )
                )
                
        except Exception as e:
            _LOGGER.error("Failed to refresh cookie: %s", e)
            # Create an error notification
            await hass.async_create_task(
                hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "PSEG Integration: Cookie Refresh Error",
                        "message": f"Error refreshing your PSEG authentication cookie: {e}",
                        "notification_id": "psegli_cookie_refresh_error",
                    },
                )
            )
    
    hass.services.async_register(
        DOMAIN,
        "refresh_cookie",
        async_refresh_cookie
    )
    
    async def async_enter_mfa_code(call: Any) -> None:
        """Complete MFA by entering the verification code from email or SMS."""
        code = call.data.get("code", "").strip()
        if not code:
            _LOGGER.error("No MFA code provided")
            return
        if not await check_addon_health():
            _LOGGER.error("Addon not available - cannot complete MFA")
            return
        cookies = await complete_mfa_login(code)
        if cookies:
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, CONF_COOKIE: cookies},
            )
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                current_client = hass.data[DOMAIN][entry.entry_id]
                current_client.update_cookie(cookies)
                if hasattr(entry, "runtime_data") and entry.runtime_data:
                    coordinator = entry.runtime_data
                    if hasattr(coordinator, "client"):
                        coordinator.client.update_cookie(cookies)
            await hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": "psegli_mfa_required"},
            )
            # Fetch and save energy data now that we have a valid cookie
            try:
                await async_update_statistics_manual(type("Call", (), {"data": {"days_back": 0}})())
                _LOGGER.info("Energy data saved after MFA")
            except Exception as stats_err:
                _LOGGER.warning("Statistics update after MFA failed: %s", stats_err)
            msg = "Successfully completed MFA. Your PSEG integration is now working."
            if entry.entry_id not in hass.data.get(DOMAIN, {}):
                msg += " Reload the integration (Settings > Integrations > PSEG Long Island > Reload) to start using it."
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "PSEG Integration: MFA Complete",
                    "message": msg,
                    "notification_id": "psegli_mfa_complete",
                },
            )
            _LOGGER.info("MFA completed successfully")
        else:
            _LOGGER.error("MFA failed - code may be invalid or session expired")
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "PSEG Integration: MFA Failed",
                    "message": "MFA verification failed. The code may be invalid or expired. Try refresh_cookie again, then enter the new code.",
                    "notification_id": "psegli_mfa_failed",
                },
            )
    
    hass.services.async_register(
        DOMAIN,
        "enter_mfa_code",
        async_enter_mfa_code
    )
    
    # Set up scheduled cookie refresh at XX:00 and XX:30
    async def async_scheduled_cookie_refresh() -> None:
        """Automatically refresh cookies at scheduled times (XX:00 and XX:30).
        Only refreshes when the current cookie is invalid - avoids MFA on every run.
        """
        _LOGGER.debug("Scheduled cookie refresh triggered")
        
        try:
            username = entry.data.get(CONF_USERNAME)
            password = entry.data.get(CONF_PASSWORD)
            cookie = entry.data.get(CONF_COOKIE, "")
            
            if not username or not password:
                _LOGGER.warning("No credentials available for scheduled cookie refresh")
                return
            
            # If we have a cookie, test it first - skip refresh if still valid
            if cookie and entry.entry_id in hass.data.get(DOMAIN, {}):
                current_client = hass.data[DOMAIN][entry.entry_id]
                try:
                    await current_client.test_connection()
                    _LOGGER.debug("Cookie still valid, skipping cookie refresh (no MFA needed)")
                    # Still update statistics - energy data may have new readings
                    try:
                        await async_update_statistics_manual(type("Call", (), {"data": {"days_back": 0}})())
                        _LOGGER.debug("Statistics updated (cookie still valid)")
                    except Exception as stats_err:
                        _LOGGER.warning("Statistics update failed: %s", stats_err)
                    return
                except InvalidAuth:
                    _LOGGER.debug("Cookie expired, proceeding with refresh")
            
            # Check if addon is healthy before attempting refresh
            if not await check_addon_health():
                _LOGGER.warning("Addon not available or unhealthy, skipping scheduled cookie refresh")
                return
            
            # Attempt to get fresh cookies
            mfa_method = entry.data.get(CONF_MFA_METHOD, "sms")
            cookies = await get_fresh_cookies(username, password, mfa_method=mfa_method)
            
            if cookies == MFA_REQUIRED:
                channel = "phone" if mfa_method == "sms" else "email"
                _LOGGER.warning("PSEG requires MFA - check %s, then call enter_mfa_code service", channel)
                await hass.async_create_task(
                    hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "PSEG Integration: MFA Required",
                            "message": f"PSEG sent a verification code to your {channel}. Check your {channel}, then go to Developer Tools > Services and call 'PSEG Long Island: Enter MFA Code' with the code.",
                            "notification_id": "psegli_mfa_required",
                        },
                    )
                )
            elif cookies:
                # Cookies are already in string format from addon
                cookie_string = cookies
                current_client = hass.data[DOMAIN][entry.entry_id]
                
                # Update the client with new cookie
                current_client.update_cookie(cookie_string)
                
                # Also update the coordinator's client if it exists
                if hasattr(entry, 'runtime_data') and entry.runtime_data:
                    coordinator = entry.runtime_data
                    if hasattr(coordinator, 'client'):
                        coordinator.client.update_cookie(cookie_string)
                        _LOGGER.debug("✅ Updated coordinator client cookie")
                
                _LOGGER.debug("✅ Updated client cookie: %s", cookie_string[:50] + "..." if len(cookie_string) > 50 else cookie_string)
                _LOGGER.debug("✅ Updated client session headers")
                
                # Update the config entry
                hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_COOKIE: cookie_string},
                )
                
                _LOGGER.debug("✅ Updated config entry with new cookie")
                _LOGGER.debug("Scheduled cookie refresh completed successfully")
                
                await current_client.test_connection()
                _LOGGER.debug("New cookie validation successful")
                
                _LOGGER.debug("Triggering statistics update with fresh cookies...")
                try:
                    await async_update_statistics_manual(type('Call', (), {'data': {'days_back': 0}})())
                    _LOGGER.debug("Statistics update completed successfully with fresh cookies")
                except Exception as stats_err:
                    _LOGGER.error("Statistics update failed even with fresh cookies: %s", stats_err)
                
            else:
                _LOGGER.warning("Addon failed to provide fresh cookies during scheduled refresh")
                
        except Exception as e:
            _LOGGER.error("Failed to refresh cookie during scheduled refresh: %s", e)
    
    # Use standard Home Assistant approach: refresh cookies at XX:00 and XX:30
    async def refresh_cookies_scheduled():
        """Refresh cookies at scheduled times (XX:00 and XX:30)."""
        while True:
            now = datetime.now()
            
            if now.minute < 30:
                next_refresh = now.replace(minute=30, second=0, microsecond=0)
            else:
                # Next refresh at XX:00 (next hour)
                next_refresh = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            
            wait_seconds = (next_refresh - now).total_seconds()
            _LOGGER.debug("Next scheduled cookie refresh at %s (in %.0f seconds)", 
                         next_refresh.strftime("%H:%M"), wait_seconds)
            
            await asyncio.sleep(wait_seconds)
            
            await async_scheduled_cookie_refresh()
    
    # Start the scheduled cookie refresh task AFTER all services are registered
    # Use a global flag that persists across reloads to prevent multiple tasks
    if 'global_scheduled_task_running' not in hass.data:
        hass.data['global_scheduled_task_running'] = True
        task = entry.async_create_background_task(
            hass, refresh_cookies_scheduled(), "psegli_session_maintenance"
        )
        hass.data['global_scheduled_task'] = task
        _LOGGER.debug("Started global scheduled cookie refresh task")
    else:
        _LOGGER.debug("Global scheduled cookie refresh task already running, skipping duplicate")
    
    return True

class PSEGCoordinator(DataUpdateCoordinator):
    """Handle fetching PSEG data and updating statistics (like Opower)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: PSEGLIClient):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="PSEG",
            # No automatic updates - only manual and scheduled
            update_interval=None,
        )
        self.entry = entry
        self.client = client


    async def _async_update_data(self):
        """Fetch data from PSEG and update statistics."""
        try:
            # This ensures both manual and automatic updates use identical code paths
            await self.hass.services.async_call(
                DOMAIN,
                "update_statistics",
                {"days_back": 0},
                blocking=True
            )
            
            # Return a simple success indicator since the service handles the actual work
            return {"status": "success"}
                
        except InvalidAuth as e:
            _LOGGER.error("Authentication failed during coordinator update: %s", e)
            _LOGGER.debug("Cookie refresh will be attempted at the next scheduled time (XX:00 or XX:30)")
            
            # Create a persistent notification to alert the user
            await self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "PSEG Integration: Authentication Failed",
                        "message": f"Your PSEG cookie has expired. Cookie refresh will be attempted at the next scheduled time (XX:00 or XX:30).\n\nError: {e}",
                        "notification_id": "psegli_auth_failed",
                    },
                )
            )
            raise UpdateFailed(f"Authentication failed: {e}")
        except Exception as e:
            _LOGGER.error("Failed to update PSEG data: %s", e)
            raise UpdateFailed(f"Failed to update PSEG data: {e}")

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for PSEG Long Island."""
    # Don't reload the entire config entry - just update the data
    # This prevents creating multiple scheduled tasks
    _LOGGER.debug("Options updated - no reload needed")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload the coordinator
    if entry.runtime_data:
        await entry.runtime_data.async_shutdown()
    
    # Clean up coordinator reference from hass.data
    if DOMAIN in hass.data and 'coordinator' in hass.data[DOMAIN]:
        del hass.data[DOMAIN]['coordinator']
    
    # Clean up global scheduled task flag if this is the last instance
    if 'global_scheduled_task_running' in hass.data:
        # Check if there are other instances running
        other_instances = [e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id]
        if not other_instances:
            # Cancel the running scheduled task
            if 'global_scheduled_task' in hass.data:
                try:
                    task = hass.data['global_scheduled_task']
                    if not task.done():
                        task.cancel()
                        _LOGGER.debug("Cancelled global scheduled cookie refresh task")
                except Exception as e:
                    _LOGGER.warning("Error cancelling global scheduled task: %s", e)
                del hass.data['global_scheduled_task']
            
            del hass.data['global_scheduled_task_running']
            _LOGGER.debug("Cleaned up global scheduled task flag (last instance)")
    
    # Remove the services
    hass.services.async_remove(DOMAIN, "update_statistics")
    hass.services.async_remove(DOMAIN, "refresh_cookie")
    hass.services.async_remove(DOMAIN, "enter_mfa_code")
    
    return True
