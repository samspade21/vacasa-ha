# Technical Context: Vacasa Home Assistant Integration

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary programming language
- **Home Assistant**: Smart home platform (core version 2023.5.0 or newer)
- **aiohttp**: Async HTTP client for API communication
- **asyncio**: Asynchronous I/O framework

### Home Assistant Components
- **Calendar Platform**: Base platform for calendar integration
- **Config Flow**: UI-based configuration system
- **Entity Component**: Base for creating calendar entities

### External APIs
- **Vacasa API**: Proprietary API for accessing reservation data
  - Authentication endpoint: `https://accounts.vacasa.io/login`
  - API base URL: `https://owner.vacasa.io/api/v1`

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
- Default refresh interval: 4 hours
- Implement exponential backoff for retries

### Caching Strategy
- Token cached to file with secure permissions
- Property data cached in memory
- Reservation data refreshed on schedule

### Resource Usage
- Minimal memory footprint
- Low CPU usage
- Network requests only when needed

## Security Considerations

### Credential Storage
- Credentials stored in Home Assistant secrets
- No hardcoded credentials in code
- Minimal permission scope requested

### Token Storage
- Token stored with 0600 permissions
- Token refreshed automatically
- Token validated before use

### Error Handling
- Secure error messages (no credential leakage)
- Graceful handling of authentication failures
- Logging without sensitive information
