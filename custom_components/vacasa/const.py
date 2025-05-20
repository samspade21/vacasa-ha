"""Constants for the Vacasa integration."""
from datetime import timedelta

DOMAIN = "vacasa"
PLATFORMS = ["calendar", "binary_sensor", "sensor"]

# Configuration
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REFRESH_INTERVAL = "refresh_interval"

# Defaults
DEFAULT_REFRESH_INTERVAL = 8  # hours
DEFAULT_TIMEOUT = 30  # seconds
TOKEN_REFRESH_MARGIN = 300  # seconds (5 minutes)

# API
AUTH_URL = "https://accounts.vacasa.io/login"
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
SENSOR_RATING = "rating"
SENSOR_MAX_OCCUPANCY = "max_occupancy"
SENSOR_MAX_ADULTS = "max_adults"
SENSOR_MAX_CHILDREN = "max_children"
SENSOR_MAX_PETS = "max_pets"
SENSOR_BEDROOMS = "bedrooms"
SENSOR_BATHROOMS = "bathrooms"
SENSOR_HOT_TUB = "hot_tub"
SENSOR_PET_FRIENDLY = "pet_friendly"
SENSOR_TIMEZONE = "timezone"
SENSOR_LOCATION = "location"
SENSOR_PARKING = "parking"
SENSOR_ADDRESS = "address"

# Services
SERVICE_REFRESH_DATA = "refresh_data"
SERVICE_CLEAR_CACHE = "clear_cache"

# Scan interval
SCAN_INTERVAL = timedelta(hours=DEFAULT_REFRESH_INTERVAL)

# Data storage keys
DATA_CLIENT = "client"
DATA_COORDINATOR = "coordinator"
