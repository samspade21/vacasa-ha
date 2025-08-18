# Technical Context: Vacasa Home Assistant Integration

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary programming language
- **Home Assistant**: Smart home platform (core version 2023.5.0 or newer)
- **aiohttp**: Async HTTP client for API communication
- **asyncio**: Asynchronous I/O framework

### Home Assistant Components
- **Calendar Platform**: Base platform for calendar integration
- **Binary Sensor Platform**: Platform for occupancy status sensors
- **Sensor Platform**: Platform for property information sensors
- **Config Flow**: UI-based configuration system
- **Entity Component**: Base for creating calendar and sensor entities
- **Platform Dependencies**: Explicit dependency management for proper startup sequencing
- **Entity Registry**: Integration with Home Assistant's entity management system

### External APIs
- **Vacasa API**: Proprietary API for accessing reservation data
  - Authentication endpoint: `https://accounts.vacasa.io/login`
  - API base URL: `https://owner.vacasa.io/api/v1`
  - **Status**: Stable integration with robust error handling and retry mechanisms
  - **Current State**: Production-ready with enhanced reliability features

## Development Environment

### Required Tools
- **Python 3.9+**: For development and testing
- **Home Assistant Development Environment**: For testing the integration
- **Git**: For version control
- **Pre-commit**: For code quality checks

### Recommended Tools
- **Visual Studio Code**: With Python and Home Assistant extensions
- **Postman/Insomnia**: For API testing
- **Docker**: For running Home Assistant test instances

## Dependencies

### Runtime Dependencies
- **aiohttp**: For async HTTP requests
- **voluptuous**: For config validation (provided by Home Assistant)
- **homeassistant**: Core Home Assistant package

### Development Dependencies
- **pytest**: For unit testing
- **pytest-asyncio**: For testing async code
- **pytest-homeassistant-custom-component**: For mocking Home Assistant
- **pre-commit**: For code quality checks
- **black**: For code formatting
- **flake8**: For linting
- **mypy**: For type checking

## Authentication Flow

The Vacasa API uses OAuth 2.0 with some custom behavior:

1. **Initial Authentication**:
   - HTTP POST to login endpoint with username/password
   - Follow redirects to obtain access token
   - Extract token from URL fragment

2. **Token Management**:
   - JWT token with expiration (typically 10 minutes)
   - Token stored securely with appropriate permissions
   - Automatic refresh before expiration

3. **API Authorization**:
   - Bearer token authentication
   - Additional headers required for API calls

## Data Structures

### Vacasa API Responses

#### Units (Properties)
```json
{
  "data": [
    {
      "id": "123456",
      "type": "unit",
      "attributes": {
        "name": "Vacation Cabin",
        "code": "EXMP01",
        "address": {
          "city": "Mountain Town",
          "state": "CO"
        }
      }
    }
  ]
}
```

#### Reservations
```json
{
  "data": [
    {
      "id": "12345678",
      "type": "reservations",
      "attributes": {
        "startDate": "2024-08-15",
        "endDate": "2024-08-18",
        "firstName": "Guest",
        "lastName": "Name",
        "ownerHold": null
      }
    }
  ]
}
```

### Home Assistant Calendar Events
```python
{
    "uid": "reservation_12345678",
    "summary": "Guest Booking: Guest Name",
    "start": {"dateTime": "2024-08-15T16:00:00-07:00"},
    "end": {"dateTime": "2024-08-18T10:00:00-07:00"},
    "location": "Vacation Cabin",
    "description": "Guest booking",
    "recurrence_id": None,
}
```

## File Structure

```
custom_components/vacasa/
├── __init__.py           # Component initialization
├── calendar.py           # Calendar platform implementation
├── config_flow.py        # Configuration flow
├── const.py              # Constants
├── manifest.json         # Component metadata
├── strings.json          # Localization strings
└── vacasa_client.py      # API client
```

## Configuration

### Integration Configuration
```yaml
# Example configuration.yaml entry
vacasa:
  username: !secret vacasa_username
  password: !secret vacasa_password
```

### Secrets Management
```yaml
# Example secrets.yaml entry
vacasa_username: "example@email.com"
vacasa_password: "ExamplePassword123!"
```

## Home Assistant Integration Points

### Calendar Platform
The integration implements the Home Assistant Calendar platform, which provides:
- Calendar entities in the UI
- Event data for automations
- Standard calendar operations

### Configuration Flow
The integration uses Home Assistant's Config Flow for setup:
- Step-by-step configuration
- Credential validation
- Property discovery

### Services
The integration registers custom services:
- `vacasa.refresh_calendars`: Force refresh of calendar data
- `vacasa.clear_cache`: Clear cached data and tokens

## Performance Considerations

### API Rate Limiting
- Vacasa API may have rate limits
- Default refresh interval: 4 hours (configurable)
- Exponential backoff with jitter implemented for network resilience
- Connection pooling optimization for better HTTP performance

### Caching Strategy
- Token cached to file with secure permissions (0600)
- Property data cached with TTL-based intelligent caching
- Reservation data refreshed on coordinated schedule
- Memory management optimization to reduce redundant operations

### Resource Usage
- Minimal memory footprint with efficient state tracking
- Low CPU usage with optimized refresh patterns
- Network requests only when needed with connection reuse
- Clean logging patterns to reduce I/O overhead

### Startup Coordination
- Enhanced platform dependency management
- Staggered entity initialization (calendar → binary_sensor → sensor)
- Event-driven recovery mechanisms for temporary unavailability
- Graceful handling of Home Assistant startup timing variations

## Security Considerations

### Credential Storage
- Credentials stored in Home Assistant secrets
- No hardcoded credentials in code
- Minimal permission scope requested

### Token Storage
- Token stored with 0600 permissions for security
- Token refreshed automatically with proactive renewal
- Token validated before use with integrity checks
- Cache file operations use async patterns for Home Assistant compliance

### Error Handling
- Secure error messages without credential or token leakage
- Graceful handling of authentication failures with retry logic
- Logging without sensitive information (sanitized output)
- Production-ready error recovery with exponential backoff
- Clean error reporting for troubleshooting without exposing internals

### Integration Reliability
- Enhanced startup coordination between entity types
- Event-driven recovery when dependencies are temporarily unavailable
- Robust state management with graceful degradation
- Proper platform dependency declarations in manifest
- Current event detection with corrected datetime logic
