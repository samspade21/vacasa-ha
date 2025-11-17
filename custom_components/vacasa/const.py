"""Constants for the Vacasa integration."""

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
DEFAULT_API_VERSION = "v1"
API_BASE_TEMPLATE = "https://owner.vacasa.io/api/{version}"
DEFAULT_CLIENT_ID = "KOIkAJP9XW7ZpTXwRa0B7O4qMuXSQ3p4BKFfTPhr"
SUPPORTED_API_VERSIONS = ("v3", "v2", "v1")

# Performance optimization settings
DEFAULT_CACHE_TTL = 3600  # seconds (1 hour) for property data
DEFAULT_MAX_CONNECTIONS = 10
DEFAULT_KEEPALIVE_TIMEOUT = 30  # seconds
DEFAULT_CONN_TIMEOUT = 30  # seconds
DEFAULT_READ_TIMEOUT = 30  # seconds
DEFAULT_JITTER_MAX = 1.0  # seconds
PROPERTY_CACHE_FILE = ".vacasa_property_cache.json"

# API
AUTH_URL = "https://accounts.vacasa.io/login"
TOKEN_CACHE_FILE = ".vacasa_token.json"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
RETRY_BACKOFF_MULTIPLIER = 2

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

# Centralized mappings
STAY_TYPE_TO_CATEGORY = {
    STAY_TYPE_GUEST: CATEGORY_GUEST,
    STAY_TYPE_OWNER: CATEGORY_OWNER,
    STAY_TYPE_BLOCK: CATEGORY_BLOCK,
    STAY_TYPE_MAINTENANCE: CATEGORY_MAINTENANCE,
    STAY_TYPE_OTHER: CATEGORY_OTHER,
}

STAY_TYPE_TO_NAME = {
    STAY_TYPE_GUEST: "Guest Booking",
    STAY_TYPE_OWNER: "Owner Stay",
    STAY_TYPE_BLOCK: "Block",
    STAY_TYPE_MAINTENANCE: "Maintenance",
    STAY_TYPE_OTHER: "Other",
}

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
SENSOR_MAINTENANCE_OPEN = "maintenance_open"
SENSOR_STATEMENTS_TOTAL = "statements_total"
SENSOR_NEXT_STAY = "next_stay"

# Services
SERVICE_REFRESH_DATA = "refresh_data"
SERVICE_CLEAR_CACHE = "clear_cache"

# Dispatcher signals
SIGNAL_RESERVATION_BOUNDARY = "vacasa_reservation_boundary"
SIGNAL_RESERVATION_STATE = "vacasa_reservation_state"
