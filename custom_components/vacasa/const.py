"""Constants for the Vacasa integration."""
from datetime import timedelta

DOMAIN = "vacasa"
PLATFORMS = ["calendar", "binary_sensor"]

# Configuration
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REFRESH_INTERVAL = "refresh_interval"
CONF_OWNER_ID = "owner_id"  # Added for manual owner ID entry
CONF_CHECKIN_TIME = "checkin_time"
CONF_CHECKOUT_TIME = "checkout_time"

# Defaults
DEFAULT_REFRESH_INTERVAL = 8  # hours
DEFAULT_TIMEOUT = 30  # seconds
TOKEN_REFRESH_MARGIN = 300  # seconds (5 minutes)
DEFAULT_CHECKIN_TIME = "16:00:00"  # 4 PM
DEFAULT_CHECKOUT_TIME = "10:00:00"  # 10 AM

# API
AUTH_URL = "https://accounts.vacasa.io/login"
AUTH_REDIRECT_URL = "https://accounts.vacasa.io/authorize"
CALENDAR_URL = "https://owners.vacasa.com/calendar"
API_BASE_URL = "https://owner.vacasa.io/api/v1"
TOKEN_CACHE_FILE = ".vacasa_token.json"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Stay types
STAY_TYPE_GUEST = "guest"
STAY_TYPE_OWNER = "owner"
STAY_TYPE_BLOCK = "block"
STAY_TYPE_MAINTENANCE = "maintenance"
STAY_TYPE_OTHER = "other"

# Calendar categories
CATEGORY_GUEST = "guest_booking"
CATEGORY_OWNER = "owner_stay"
CATEGORY_MAINTENANCE = "maintenance"
CATEGORY_BLOCK = "block"
CATEGORY_OTHER = "other"

# Sensor types
SENSOR_OCCUPANCY = "occupancy"

# Services
SERVICE_REFRESH_CALENDARS = "refresh_calendars"
SERVICE_CLEAR_CACHE = "clear_cache"

# Scan interval
SCAN_INTERVAL = timedelta(hours=DEFAULT_REFRESH_INTERVAL)

# Data storage keys
DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
