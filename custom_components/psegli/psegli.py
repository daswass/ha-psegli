"""PSEG Long Island client."""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

from .const import ATTR_COMPARISON, ATTR_DESCRIPTION, ATTR_LAST_UPDATE
from .exceptions import InvalidAuth

_LOGGER = logging.getLogger(__name__)


class PSEGLIClient:
    """PSEG Long Island API client."""

    def __init__(self, cookie: str) -> None:
        """Initialize the client."""
        self.cookie = cookie
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": cookie,
            "Referer": "https://mysmartenergy.psegliny.com/Dashboard",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.8",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Gpc": "1"
        })

    def update_cookie(self, new_cookie: str) -> None:
        """Update the cookie in this client instance."""
        self.cookie = new_cookie
        self.session.headers.update({"Cookie": new_cookie})
        _LOGGER.debug("Updated client cookie to: %s", new_cookie[:50] + "..." if len(new_cookie) > 50 else new_cookie)

    def _test_connection_sync(self) -> bool:
        """Test the connection to PSEG (synchronous)."""
        try:
            response = self.session.get("https://mysmartenergy.psegliny.com/Dashboard")
            response.raise_for_status()
            
            # Check if we're redirected to login page
            if "login" in response.url.lower() or "signin" in response.url.lower():
                _LOGGER.error("Cookie rejected - redirected to login page")
                raise InvalidAuth("Cookie rejected - redirected to login page")
            
            _LOGGER.info("PSEG connection test successful")
            return True
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to connect to PSEG: %s", err)
            raise InvalidAuth("Invalid authentication") from err

    async def test_connection(self) -> bool:
        """Test the connection to PSEG (async wrapper)."""
        try:
            loop = asyncio.get_running_loop()
            with ThreadPoolExecutor() as executor:
                return await loop.run_in_executor(executor, self._test_connection_sync)
        except RuntimeError:
            # Fallback for when there's no running loop
            return self._test_connection_sync()

    def _get_dashboard_page(self) -> tuple[str, str]:
        """Get the Dashboard page and extract RequestVerificationToken."""
        _LOGGER.info("Getting RequestVerificationToken from Dashboard page...")
        dashboard_response = self.session.get("https://mysmartenergy.psegliny.com/Dashboard")
        if dashboard_response.status_code != 200:
            raise InvalidAuth("Failed to get Dashboard page")
        
        # Extract the token from the page
        import re
        token_match = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', dashboard_response.text)
        if token_match:
            request_token = token_match.group(1)
            _LOGGER.debug("Found RequestVerificationToken: %s...", request_token[:20])
        else:
            _LOGGER.error("Could not find RequestVerificationToken on /Dashboard")
            raise InvalidAuth("Could not find RequestVerificationToken on /Dashboard")
        
        return dashboard_response.text, request_token

    def _setup_chart_context(self, request_token: str, start_date: datetime, end_date: datetime) -> None:
        """Set up the Chart context with hourly granularity."""
        chart_setup_url = "https://mysmartenergy.psegliny.com/Dashboard/Chart"
        chart_setup_data = {
            "__RequestVerificationToken": request_token,
            "UsageInterval": "5",  # 5 = Hourly granularity
            "UsageType": "1",
            "jsTargetName": "StorageType",
            "EnableHoverChart": "true",
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
            "IsRangeOpen": "False",
            "MaintainMaxDate": "true",
            "SelectedViaDateRange": "False",
            "ChartComparison": "1",
            "ChartComparison2": "0",
            "ChartComparison3": "0",
            "ChartComparison4": "0"
        }
        
        _LOGGER.info("Making Chart/ setup request with hourly granularity (start: %s, end: %s)", 
                    start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        _LOGGER.debug("Chart setup data: %s", chart_setup_data)
        
        chart_setup_response = self.session.post(chart_setup_url, data=chart_setup_data)
        chart_setup_response.raise_for_status()
        
        # Check for redirect response in Chart/ request - if it redirects, the request failed
        try:
            chart_setup_json = json.loads(chart_setup_response.text)
            if "AjaxResults" in chart_setup_json and chart_setup_json["AjaxResults"]:
                for result in chart_setup_json["AjaxResults"]:
                    if result.get("Action") == "Redirect":
                        _LOGGER.error("Chart setup request FAILED - redirected to: %s", result.get('Value'))
                        _LOGGER.error("This means the hourly context was not set - cannot proceed to get hourly data")
                        raise InvalidAuth("Chart setup request failed - hourly context not established")
        except json.JSONDecodeError:
            _LOGGER.error("Chart setup response is not JSON - request failed")
            raise InvalidAuth("Chart setup response is not JSON - request failed")

    def _get_chart_data(self) -> dict[str, Any]:
        """Get the actual chart data from PSEG."""
        chart_data_url = "https://mysmartenergy.psegliny.com/Dashboard/ChartData"
        chart_data_params = {
            "_": int(datetime.now().timestamp() * 1000)  # Cache buster
        }
        
        _LOGGER.info("Making ChartData/ request to get hourly data")
        chart_response = self.session.get(chart_data_url, params=chart_data_params)
        chart_response.raise_for_status()
        
        # Debug: Log the response content
        _LOGGER.debug("ChartData response status: %s", chart_response.status_code)
        _LOGGER.debug("ChartData response headers: %s", dict(chart_response.headers))
        _LOGGER.debug("ChartData response content (first 500 chars): %s", chart_response.text[:500])
        
        chart_data = json.loads(chart_response.text)
        return chart_data

    def _get_usage_data_sync(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, days_back: int = 0) -> Dict[str, Any]:
        """Get usage data from PSEG (synchronous)."""
        try:
            # First check if our cookie is still valid
            self._test_connection_sync()
            
            # Calculate date range based on days_back parameter
            if days_back == 0:
                # Yesterday to today (accounting for data lag)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=1)
            else:
                # days_back days ago to now
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
            
            _LOGGER.info("Date calculation: days_back=%d, start_date=%s, end_date=%s", 
                        days_back, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            
            # Step 1: Get Dashboard page and extract token
            _, request_token = self._get_dashboard_page()
            
            # Step 2: Set up Chart context
            self._setup_chart_context(request_token, start_date, end_date)
            
            # Step 3: Get actual chart data
            chart_data = self._get_chart_data()
            
            # Create a minimal widget data structure since we're not fetching it
            widget_data = {"AjaxResults": []}

            return self._parse_data(widget_data, chart_data)

        except requests.exceptions.RequestException as err:
            _LOGGER.error("Failed to get usage data: %s", err)
            raise InvalidAuth("Failed to get usage data") from err
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to parse JSON response: %s", err)
            # This usually indicates an expired cookie (server returns HTML login page instead of JSON)
            _LOGGER.error("This error typically indicates an expired authentication cookie. Please update your cookie in the PSEG integration configuration.")
            raise InvalidAuth("Authentication cookie has expired - please update your cookie") from err

    async def get_usage_data(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, days_back: int = 0) -> Dict[str, Any]:
        """Get usage data from PSEG (async wrapper)."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self._get_usage_data_sync, start_date, end_date, days_back)

    def _parse_data(self, widget_data: Dict[str, Any], chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the widget and chart data."""
        result = {
            "widgets": {},
            "chart_data": {},
            "last_update": datetime.now().isoformat()
        }

        # Parse widget data
        for result_item in widget_data.get("AjaxResults", []):
            if result_item.get("Action") == "Prepend" and "usageWidget" in result_item.get("Value", ""):
                html_content = result_item.get("Value", "")
                soup = BeautifulSoup(html_content, "html.parser")
                
                usage_widgets = soup.find_all("div", class_="usageWidget")
                for widget in usage_widgets:
                    usage_h2 = widget.find("h2")
                    if usage_h2:
                        usage_value = usage_h2.get_text(strip=True)
                        
                        description_div = widget.find("div", class_="widgetDescription")
                        description = description_div.get_text(strip=True) if description_div else ""
                        
                        range_alert = widget.find("div", class_="rangeAlert")
                        comparison = range_alert.get_text(strip=True) if range_alert else ""
                        
                        # Extract numeric value
                        try:
                            numeric_value = float(usage_value.replace("kWh", "").strip())
                        except ValueError:
                            numeric_value = 0.0
                        
                        result["widgets"][description] = {
                            "value": numeric_value,
                            "raw_value": usage_value,
                            "description": description,
                            "comparison": comparison,
                        }

        # Parse chart data
        if "Data" in chart_data and "series" in chart_data["Data"]:
            for series in chart_data["Data"]["series"]:
                series_name = series.get("name", "Unknown")
                data_points = series.get("data", [])
                
                _LOGGER.debug("Processing series: %s with %d data points", series_name, len(data_points))
                
                valid_points = []
                for i, point in enumerate(data_points):
                    if isinstance(point, dict) and "x" in point and "y" in point:
                        # Object format: hourly data with proper structure
                        timestamp = point["x"] / 1000
                        value = point["y"]
                        # Replace None values with 0 to ensure continuous data flow
                        if value is None:
                            value = 0
                        # Timestamps need to be shifted by +4 hours to align with actual peak hours
                        # Raw timestamp shows 11:00 AM but should be 3:00 PM for peak hours
                        shifted_timestamp = timestamp + (4 * 3600)  # Add 4 hours
                        local_time = datetime.fromtimestamp(shifted_timestamp)
                        valid_points.append({
                            "timestamp": local_time,
                            "value": value
                        })
                        _LOGGER.debug("Point %d: timestamp=%s, value=%s", i, local_time, value)
                    elif isinstance(point, list) and len(point) >= 2:
                        # Array format: appears to be daily summaries, not hourly data
                        # Skip this format when we're looking for hourly consumption data
                        continue
                
                if valid_points:
                    latest_point = max(valid_points, key=lambda x: x["timestamp"])
                    values = [p["value"] for p in valid_points]
                    
                    # Debug logging
                    _LOGGER.debug("Series %s: %d valid points, values: %s", 
                                 series_name, len(valid_points), values[:5])
                    
                    result["chart_data"][series_name] = {
                        "latest_value": latest_point["value"],
                        "latest_timestamp": latest_point["timestamp"].isoformat(),
                        "min_value": min(values) if values else 0,
                        "max_value": max(values) if values else 0,
                        "avg_value": sum(values) / len(values) if values else 0,
                        "data_points": len(valid_points),
                        "valid_points": valid_points  # Include the actual data points
                    }

        return result 

 