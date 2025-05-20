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

### 1. Async/Await Pattern
The integration uses Python's async/await pattern throughout to ensure compatibility with Home Assistant's event loop:

```python
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    # Async setup code

async def async_get_events(self, hass, start_date, end_date):
    # Async event retrieval
```

### 2. Repository Pattern
The Vacasa API client acts as a repository, abstracting the data access layer:

```python
class VacasaClient:
    async def get_units(self) -> List[Dict[str, Any]]:
        # Fetch units from API

    async def get_categorized_reservations(self, unit_id, start_date, end_date):
        # Fetch and categorize reservations
```

### 3. Caching Pattern
Token and data caching to minimize API calls:

```python
def _save_token_to_cache(self) -> None:
    # Save token to persistent storage

def _load_token_from_cache(self) -> bool:
    # Load token from persistent storage
```

### 4. Retry Pattern
Robust error handling with retry logic:

```python
async def authenticate(self) -> str:
    # Implement retry logic
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Authentication logic
        except Exception:
            # Handle error and retry
```

### 5. Factory Pattern
Calendar entity creation using a factory approach:

```python
def _create_calendar_entities(self, units):
    # Create calendar entities for each unit
    return [VacasaCalendar(self.client, unit) for unit in units]
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

2. **Configuration Flow**
   - Step-by-step configuration with validation
   - Discovery of available properties
   - Clear error messages for troubleshooting

3. **Service Registration**
   - Register services for manual refresh
   - Provide feedback on service calls

## Testing Patterns

1. **Unit Testing**
   - Mock API responses for predictable testing
   - Test each component in isolation

2. **Integration Testing**
   - Test the integration with Home Assistant
   - Verify calendar functionality

3. **Authentication Testing**
   - Test token refresh and error handling
   - Verify secure credential storage
