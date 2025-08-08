"""Constants for the PSEG Long Island integration."""

DOMAIN = "psegli"

# Defaults
DEFAULT_NAME = "PSEG Long Island"
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# Configuration
CONF_COOKIE = "cookie"
CONF_COOKIE_SECRET = "cookie_secret"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Sensor names
SENSOR_TOTAL_ENERGY = "total_energy"
SENSOR_DAILY_USAGE = "daily_usage"
SENSOR_WEEKLY_USAGE = "weekly_usage"
SENSOR_CURRENT_USAGE = "current_usage"
SENSOR_OFF_PEAK_USAGE = "off_peak_usage"
SENSOR_ON_PEAK_USAGE = "on_peak_usage"
SENSOR_TEMPERATURE = "temperature"

# Sensor attributes
ATTR_LAST_UPDATE = "last_update"
ATTR_COMPARISON = "comparison"
ATTR_DESCRIPTION = "description" 