"""The PSEG Long Island integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD
from .psegli import InvalidAuth, PSEGLIClient

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
    
    if not username or not password:
        _LOGGER.error("No username/password provided")
        return False
    
    # Try to get fresh cookies using automated login
    try:
        from .auto_login import get_fresh_cookies
        cookies = await get_fresh_cookies(username, password)
        
        if not cookies:
            _LOGGER.error("Failed to get cookies from automation addon")
            return False
        
        # Convert cookies to cookie string
        cookie_string = "; ".join([f"{name}={value}" for name, value in cookies.items()])
        _LOGGER.info("Obtained fresh cookies, length: %d", len(cookie_string))
        
        # Store cookie in config entry for future use
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "cookie": cookie_string},
        )
        
    except Exception as e:
        _LOGGER.error("Failed to get cookies: %s", e)
        return False
    
    # Use the cookies we just obtained, not from the config entry
    cookie = cookie_string
    
    # Create client
    client = PSEGLIClient(cookie)
    hass.data[DOMAIN][entry.entry_id] = client
    
    # Test connection
    try:
        await client.test_connection()
        _LOGGER.info("PSEG connection test successful")
    except InvalidAuth as e:
        _LOGGER.error("Authentication failed: %s", e)
        raise ConfigEntryAuthFailed("Invalid authentication")
    
    # Create coordinator for automatic updates (like Opower)
    coordinator = PSEGCoordinator(hass, entry, client)
    entry.runtime_data = coordinator
    
    # Listen for config changes (when user updates cookie via options)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Set up automatic updates (like Opower)
    async def async_update_statistics_automatic() -> None:
        """Automatically update statistics with latest PSEG data."""
        try:
            # Get today's data (days_back=0 means yesterday to today)
            _LOGGER.debug("Automatic statistics update: fetching today's data")
            
            # Get fresh data from PSEG
            historical_data = await client.get_usage_data(0)
            
            if "chart_data" in historical_data:
                await _process_chart_data(hass, historical_data["chart_data"])
                
        except Exception as e:
            _LOGGER.error("Failed to update statistics automatically: %s", e)
    
    # Register manual service for backfilling
    async def async_update_statistics_manual(call: Any) -> None:
        """Manually update statistics table with PSEG data (for backfilling)."""
        days_back = call.data.get("days_back", 0)
        _LOGGER.info("Manual statistics update service (days_back: %d)", days_back)
        
        try:
            # Get fresh data from PSEG with the specified days_back
            historical_data = await client.get_usage_data(days_back)
            
            if "chart_data" in historical_data:
                await _process_chart_data(hass, historical_data["chart_data"])
                _LOGGER.info("Manual statistics update completed successfully")
            else:
                _LOGGER.warning("No chart data found in response")
                
        except Exception as e:
            _LOGGER.error("Failed to update statistics manually: %s", e)

    # Register the manual service
    hass.services.async_register(
        DOMAIN,
        "update_statistics",
        async_update_statistics_manual
    )
    
    return True

class PSEGCoordinator(DataUpdateCoordinator):
    """Handle fetching PSEG data and updating statistics (like Opower)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: PSEGLIClient):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="PSEG",
            # Update every 15 minutes to get fresh data
            update_interval=timedelta(minutes=15),
        )
        self.entry = entry
        self.client = client

        @callback
        def _dummy_listener() -> None:
            pass

        # Force the coordinator to periodically update by registering at least one listener.
        # Needed when there are no sensors, so _async_update_data still gets called
        # which is needed for _insert_statistics.
        self.async_add_listener(_dummy_listener)

    async def _async_update_data(self):
        """Fetch data from PSEG and update statistics."""
        try:
            # Get today's data (days_back=0 means just today)
            _LOGGER.debug("Coordinator update: fetching today's data")
            
            # Get fresh data from PSEG
            historical_data = await self.client.get_usage_data(0)
            
            if "chart_data" in historical_data:
                await _process_chart_data(self.hass, historical_data["chart_data"])
                
            return historical_data
                
        except InvalidAuth as e:
            _LOGGER.error("Authentication failed during coordinator update: %s", e)
            # Create a persistent notification to alert the user
            await self.hass.async_create_task(
                self.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "PSEG Integration: Authentication Failed",
                        "message": f"Your PSEG cookie has expired. Please go to Settings > Integrations > PSEG Long Island > Configure to update your cookie.\n\nError: {e}",
                        "notification_id": "psegli_auth_failed",
                    },
                )
            )
            raise UpdateFailed(f"Authentication failed: {e}")
        except Exception as e:
            _LOGGER.error("Failed to update PSEG data: %s", e)
            raise UpdateFailed(f"Failed to update PSEG data: {e}")

async def _process_chart_data(hass: HomeAssistant, chart_data: dict[str, Any]) -> None:
    """Process chart data and update statistics."""
    # Create timezone once to avoid blocking calls
    from datetime import timezone
    import pytz
    
    # Move timezone creation to executor to avoid blocking call
    local_tz = await hass.async_add_executor_job(pytz.timezone, 'America/New_York')
    
    for series_name, series_data in chart_data.items():
        try:
            _LOGGER.debug("Series %s data type: %s", series_name, type(series_data))
            _LOGGER.debug("Series %s keys: %s", series_name, list(series_data.keys()) if isinstance(series_data, dict) else "not a dict")
            
            valid_points = series_data.get("valid_points", [])
            _LOGGER.debug("Valid points type: %s, length: %s", type(valid_points), len(valid_points) if hasattr(valid_points, '__len__') else "no length")
            
            # Handle case where valid_points might be a string (defensive programming)
            if isinstance(valid_points, str):
                _LOGGER.warning("Valid points is a string, attempting to parse: %s", valid_points[:100])
                try:
                    import json
                    valid_points = json.loads(valid_points)
                    _LOGGER.info("Successfully parsed valid_points from string")
                except Exception as e:
                    _LOGGER.error("Failed to parse valid_points string: %s", e)
                    continue
            
            if not valid_points or not isinstance(valid_points, list):
                _LOGGER.warning("Valid points is not a list: %s", type(valid_points))
                continue
            
            _LOGGER.info("Processing series %s with %d data points", series_name, len(valid_points))
            _LOGGER.debug("First few valid_points: %s", valid_points[:3] if valid_points else "None")
            
            # Debug: Check the structure of the first point
            if valid_points:
                first_point = valid_points[0]
                _LOGGER.debug("First point type: %s, keys: %s", type(first_point), list(first_point.keys()) if isinstance(first_point, dict) else "not a dict")
            
            # Determine which statistic this series maps to (using proper format)
            if "Off-Peak" in series_name:
                statistic_id = "psegli:off_peak_usage"  # Use proper format like Opower
            elif "On-Peak" in series_name:
                statistic_id = "psegli:on_peak_usage"   # Use proper format like Opower
            else:
                continue  # Skip non-peak series
            
            # Prepare statistics data for HA's API
            # For energy consumption, we need both hourly values and cumulative totals (like Opower)
            statistics = []
            cumulative_total = 0.0
            
            try:
                for i, point in enumerate(valid_points):
                    try:
                        _LOGGER.debug("Processing point %d: type=%s, value=%s", i, type(point), point)
                        
                        if isinstance(point, dict) and "timestamp" in point and "value" in point:
                            timestamp = point["timestamp"]
                            value = point["value"]
                            
                            _LOGGER.debug("Point %d: timestamp=%s, value=%s", i, timestamp, value)
                            
                            # Ensure timestamp is at the top of the hour (Statistics API requirement)
                            # Round down to the nearest hour
                            if hasattr(timestamp, 'replace'):
                                # If it's a datetime object, round to hour
                                start_time = timestamp.replace(minute=0, second=0, microsecond=0)
                            else:
                                # If it's a timestamp, convert to datetime first
                                start_time = datetime.fromtimestamp(timestamp)
                                start_time = start_time.replace(minute=0, second=0, microsecond=0)
                            
                            # Make timezone-aware (Statistics API requirement)
                            if start_time.tzinfo is None:
                                start_time = local_tz.localize(start_time)
                            
                            # For energy consumption, we need to ensure positive values
                            # and proper formatting for Home Assistant's Statistics API
                            energy_value = max(0.0, float(value))  # Ensure non-negative
                            
                            # For energy consumption, use both hourly value and cumulative total (like Opower)
                            cumulative_total += energy_value
                            
                            # Statistics API expects specific format for energy consumption (like Opower)
                            statistics.append({
                                "start": start_time,
                                "state": energy_value,      # Hourly consumption value
                                "sum": cumulative_total,    # Cumulative total
                                "mean": energy_value,       # Average for this hour (hourly consumption)
                                "min": energy_value,        # Min for this hour
                                "max": energy_value,        # Max for this hour
                            })
                        else:
                            _LOGGER.warning("Skipping invalid point %d: %s", i, point)
                    except Exception as e:
                        _LOGGER.error("Error processing point %d (%s): %s", i, point, e)
                        continue
            except Exception as e:
                _LOGGER.error("Error in enumerate loop for series %s: %s", series_name, e)
                continue
            
            # Use HA's Statistics API to update
            from homeassistant.components.recorder.statistics import async_add_external_statistics
            
            try:
                _LOGGER.debug("Calling async_add_external_statistics with %d statistics entries", len(statistics))
                if statistics:
                    _LOGGER.debug("First statistics entry: %s", statistics[0])
                
                # Create metadata for the statistic (like Opower)
                metadata = {
                    "statistic_id": statistic_id,  # Use proper format
                    "source": "psegli",  # Use domain as source
                    "unit_of_measurement": "kWh",
                    "has_mean": True,
                    "has_sum": True,
                    "name": f"PSEG {series_name}",
                }
                
                _LOGGER.debug("Using metadata: %s", metadata)
                
                # Check if the function is callable
                if not callable(async_add_external_statistics):
                    _LOGGER.error("async_add_external_statistics is not callable: %s", type(async_add_external_statistics))
                    continue
                
                result = async_add_external_statistics(
                    hass,
                    metadata,
                    statistics
                )
                
                # Check if result is awaitable
                if hasattr(result, '__await__'):
                    await result
                    _LOGGER.info("Successfully updated statistics for %s", statistic_id)
                else:
                    _LOGGER.info("Statistics update completed (non-awaitable result) for %s", statistic_id)
                    
            except Exception as e:
                _LOGGER.error("Error calling async_add_external_statistics for %s: %s", statistic_id, e)
        except Exception as e:
            _LOGGER.error("Error processing series %s: %s", series_name, e)
            continue


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options for PSEG Long Island."""
    # Reload the config entry when options change (when user updates cookie)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload the coordinator
    if entry.runtime_data:
        await entry.runtime_data.async_shutdown()
    
    # Remove the service
    hass.services.async_remove(DOMAIN, "update_statistics")
    
    return True 