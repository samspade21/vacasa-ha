# System Patterns: Vacasa Home Assistant Integration

## Architecture Overview

The Vacasa Home Assistant Integration follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│                Home Assistant                   │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│               Calendar Platform                 │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│               Vacasa API Client                 │
└───────────────────────┬─────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────┐
│                  Vacasa API                     │
└─────────────────────────────────────────────────┘
```

### Component Responsibilities

1. **Calendar Platform**
   - Implements Home Assistant's calendar platform interface
   - Creates calendar entities for each Vacasa property
   - Handles event creation and updates
   - Manages refresh scheduling

2. **Vacasa API Client**
   - Handles authentication with Vacasa
   - Manages token caching and refresh
   - Provides methods to fetch properties and reservations
   - Categorizes reservations by stay type

3. **Configuration Flow**
   - Provides UI for setting up the integration
   - Validates credentials
   - Discovers available properties
   - Stores configuration securely

## Key Design Patterns

### 1. Startup Coordination Pattern
Enhanced coordination between different entity types to ensure proper initialization order:

```python
# Binary sensors wait for calendar entity availability
async def _update_occupancy_from_calendar(self):
    calendar_entity_id = self._get_calendar_entity_id()
    calendar_state = self.hass.states.get(calendar_entity_id)

    if calendar_state is None:
        # Calendar not ready yet - schedule retry
        self._schedule_retry()
        return

    # Process calendar state now that it's available
```

### 2. Event-Driven Recovery Pattern
Automatic retry mechanisms when dependencies are temporarily unavailable:

```python
def _schedule_retry(self):
    """Schedule retry when calendar entity is not available."""
    if self._retry_count < MAX_RETRIES:
        delay = min(30 * (2 ** self._retry_count), 300)  # Exponential backoff
        self.hass.loop.call_later(delay, self._retry_update)
        self._retry_count += 1
```

### 3. Platform Dependency Pattern
Explicit declaration of platform dependencies to ensure proper startup order:

```python
# In manifest.json
{
    "dependencies": ["calendar"],
    "after_dependencies": ["calendar"]
}

# In component initialization
PLATFORMS = ["calendar", "binary_sensor", "sensor"]
# Calendar platform loads first, then dependent platforms
```

### 4. Async/Await Pattern
The integration uses Python's async/await pattern throughout to ensure compatibility with Home Assistant's event loop:

```python
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Async setup code

async def async_get_events(self, hass, start_date, end_date):
    # Async event retrieval
```

### 5. Repository Pattern
The Vacasa API client acts as a repository, abstracting the data access layer:

```python
class VacasaClient:
    async def get_units(self) -> List[Dict[str, Any]]:
        # Fetch units from API

    async def get_categorized_reservations(self, unit_id, start_date, end_date):
        # Fetch and categorize reservations
```

### 6. Caching Pattern
Token and data caching to minimize API calls:

```python
def _save_token_to_cache(self) -> None:
    # Save token to persistent storage

def _load_token_from_cache(self) -> bool:
    # Load token from persistent storage
```

### 7. Current Event Detection Pattern
Corrected logic for detecting current vs future events:

```python
def _is_current_event(self, event_start: datetime, event_end: datetime) -> bool:
    """Determine if an event is currently active."""
    now = datetime.now(event_start.tzinfo)

    # Event is current if we're between start and end times
    # Use <= for end time to include checkout day until checkout time
    return event_start <= now <= event_end
```

### 8. Retry Pattern with Exponential Backoff
Robust error handling with retry logic and jitter:

```python
async def authenticate(self) -> str:
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Authentication logic
        except Exception:
            # Exponential backoff with jitter
            delay = min(30 * (2 ** retry_count), 300)
            jitter = random.uniform(0, delay * 0.1)
            await asyncio.sleep(delay + jitter)
            retry_count += 1
```

### 9. Factory Pattern
Calendar entity creation using a factory approach:

```python
def _create_calendar_entities(self, units):
    # Create calendar entities for each unit
    return [VacasaCalendar(self.client, unit) for unit in units]
```

### 10. Clean Logging Pattern
Production-ready logging with structured, maintainable output:

```python
# Clean, informative debug messages
_LOGGER.debug("Unit %s occupied: %s", unit_id, guest_info)
_LOGGER.debug("Unit %s not occupied", unit_id)

# Error logging without sensitive information
_LOGGER.error("Error updating occupancy for %s: %s",
              property_name, str(error))

# Avoid noisy repetitive logs in production
if self._last_state != new_state:
    _LOGGER.info("Occupancy changed for %s: %s", property_name, new_state)
    self._last_state = new_state
```

## Data Flow

1. **Authentication Flow**
   ```
   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
   │ Get     │     │ Submit  │     │ Follow  │     │ Extract │
   │ Login   │ ──► │ Login   │ ──► │ Auth    │ ──► │ Token   │
   │ Page    │     │ Form    │     │ Redirect│     │         │
   └─────────┘     └─────────┘     └─────────┘     └─────────┘
   ```

2. **Calendar Data Flow**
   ```
   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
   │ Fetch   │     │ Fetch   │     │Categorize│    │ Create  │
   │ Units   │ ──► │Reservat-│ ──► │  Stays   │ ──►│ Calendar│
   │         │     │ ions    │     │          │    │ Events  │
   └─────────┘     └─────────┘     └─────────┘     └─────────┘
   ```

## Security Patterns

1. **Credential Storage**
   - Credentials stored in Home Assistant's secrets manager
   - No hardcoded credentials in code

2. **Token Management**
   - Tokens stored with appropriate file permissions
   - Automatic token refresh before expiration
   - Token validation before use

3. **Error Handling**
   - Graceful handling of authentication failures
   - Appropriate error messages without exposing sensitive information

## Integration Patterns

1. **Home Assistant Calendar Platform**
   - Implements the calendar platform interface
   - Provides standard calendar functionality
   - Supports filtering and event categorization
   - Corrected current event detection logic

2. **Binary Sensor Coordination**
   - Waits for calendar entity availability before initialization
   - Event-driven updates based on calendar state changes
   - Graceful handling of calendar entity unavailability
   - Automatic retry with exponential backoff

3. **Platform Dependencies**
   - Explicit dependency declaration in manifest
   - Controlled startup sequence (calendar → binary_sensor → sensor)
   - Prevents race conditions during Home Assistant startup

4. **Configuration Flow**
   - Step-by-step configuration with validation
   - Discovery of available properties
   - Clear error messages for troubleshooting
   - Automatic reload for configuration changes

5. **Service Registration**
   - Register services for manual refresh
   - Provide feedback on service calls
   - Clear cache functionality for troubleshooting

6. **Robust State Management**
   - Graceful handling of entity state transitions
   - Recovery from temporary unavailability
   - Clean state tracking without memory leaks

## Testing Patterns

1. **Unit Testing**
   - Mock API responses for predictable testing
   - Test each component in isolation
   - Use pytest-homeassistant-custom-component for mocking Home Assistant

2. **Integration Testing**
   - Test the integration with Home Assistant
   - Verify calendar functionality
   - Test across multiple Python versions (3.9, 3.10, 3.11)

3. **Authentication Testing**
   - Test token refresh and error handling
   - Verify secure credential storage

## CI/CD Patterns

1. **GitHub Actions Workflows**
   - Validate workflow for code quality and testing
   - Release workflow for packaging and distribution
   - Dependency caching for faster builds
   - Matrix testing across Python versions

2. **HACS Compliance**
   - Root-level hacs.json file
   - Proper manifest.json configuration
   - GitHub topics for discoverability
   - Logo and documentation standards

3. **Pre-commit Integration**
   - Automated code formatting with Black
   - Linting with Flake8
   - Type checking with MyPy
   - Consistent code style enforcement
