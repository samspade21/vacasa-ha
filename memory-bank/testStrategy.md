# Test Strategy: Vacasa Home Assistant Integration

**Current Status**: As of v1.3.0, the integration is production-ready with enhanced reliability. Testing strategy now focuses on maintaining stability and preventing regressions.

## Core Testing Philosophy

1. **Focus on Critical Paths**: Test the most important functionality first
2. **Minimize API Dependencies**: Use mocks to avoid hitting the real Vacasa API
3. **Keep It Simple**: Start with basic tests and expand as needed
4. **Automate Where Possible**: Use GitHub Actions for continuous testing
5. **Regression Prevention**: Ensure new changes don't break the enhanced reliability features
6. **Edge Case Coverage**: Test startup coordination and recovery mechanism scenarios

## Test Levels

### 1. Unit Tests

**API Client Tests**
- Test authentication flow with mocked responses
- Test token refresh logic
- Test reservation categorization logic
- Test error handling and retries

**Example approach:**
```python
def test_categorize_reservations():
    # Arrange: Create sample reservation data
    sample_data = [{"attributes": {"startDate": "2023-01-01", "ownerHold": {"holdType": "Owner"}}}]

    # Act: Run the categorization function
    categorized = categorize_reservations(sample_data)

    # Assert: Verify the reservation is in the correct category
    assert len(categorized["owner"]) == 1
    assert len(categorized["guest"]) == 0
```

### 2. Component Tests

**Calendar Entity Tests**
- Test event creation from reservation data
- Test calendar state updates
- Test property information formatting

**Binary Sensor Tests**
- Test occupancy detection logic
- Test state transitions based on reservation data

**Example approach:**
```python
async def test_calendar_event_creation():
    # Arrange: Set up mock reservation data
    mock_reservation = {
        "id": "12345",
        "attributes": {
            "startDate": "2023-01-01",
            "endDate": "2023-01-05",
            "firstName": "John",
            "lastName": "Doe"
        }
    }

    # Act: Create calendar event
    event = create_calendar_event(mock_reservation, "16:00:00", "10:00:00")

    # Assert: Verify event properties
    assert event["summary"] == "John Doe (Guest)"
    assert "2023-01-01T16:00:00" in event["start"]["dateTime"]
    assert "2023-01-05T10:00:00" in event["end"]["dateTime"]
```

### 3. Integration Tests

**Configuration Flow Tests**
- Test successful configuration with valid credentials
- Test error handling with invalid credentials

**Service Tests**
- Test refresh_data service
- Test manual data update triggers

**Example approach:**
```python
async def test_setup_with_valid_credentials(hass):
    # Arrange: Prepare configuration with mock credentials
    config = {
        "username": "test@example.com",
        "password": "valid_password"
    }

    # Act: Set up the integration
    result = await async_setup_entry(hass, config)

    # Assert: Verify successful setup
    assert result is True
    assert DOMAIN in hass.data
```

## Test Implementation Strategy

1. **Start Small**: Begin with 5-10 critical tests covering core functionality
2. **Use Fixtures**: Create reusable test fixtures for common test scenarios
3. **Mock External Dependencies**: Create mock responses for all API calls
4. **Parameterize Tests**: Use pytest's parameterize for testing multiple scenarios

## Test Data Strategy

1. **Static Test Data**: Create JSON files with sample API responses
2. **Scenario-Based Data**: Create data sets for different scenarios:
   - Empty property list
   - Single property with no reservations
   - Property with guest reservations
   - Property with owner reservations
   - Property with mixed reservation types

## Continuous Integration

1. **GitHub Actions Workflow**:
   - Run tests on pull requests and main branch
   - Test on Python 3.9, 3.10, and 3.11
   - Generate test coverage report

2. **Pre-commit Hooks**:
   - Run simple tests before commit
   - Ensure code quality with linting and formatting

## Manual Testing Checklist

For features that are difficult to test automatically:

1. **Authentication Flow**:
   - Verify login with valid credentials
   - Verify error handling with invalid credentials
   - Verify token refresh

2. **Calendar Integration**:
   - Verify calendar entities appear in Home Assistant
   - Verify events display correctly
   - Verify event details are accurate

3. **Binary Sensors**:
   - Verify occupancy sensors reflect current state
   - Verify state changes with reservation changes

## Current Test Implementation Status

**Current Focus**: Maintaining stability of the production-ready integration with emphasis on regression prevention.

### Phase 1: Core API Client Tests ✅ **STABLE**
1. Authentication flow with mock responses - **Production Ready**
2. Token extraction and refresh - **Enhanced with retry mechanisms**
3. Property data retrieval - **Optimized with intelligent caching**
4. Reservation categorization - **Working reliably**

### Phase 2: Entity Tests ✅ **ENHANCED**
1. Calendar event creation - **Current event detection corrected**
2. Binary sensor state determination - **Startup coordination working**
3. Property information formatting - **Reliable and consistent**

### Phase 3: Integration Tests ✅ **PRODUCTION READY**
1. Configuration flow - **User-friendly and robust**
2. Entity registration - **Platform dependencies working**
3. Service calls - **Enhanced error handling**

### Phase 4: Reliability Tests (New - v1.3.0)
1. **Startup Coordination Tests**: Verify binary sensors wait for calendar availability
2. **Recovery Mechanism Tests**: Test event-driven recovery when dependencies unavailable
3. **Current Event Detection Tests**: Ensure accurate detection of active vs future reservations
4. **Production Logging Tests**: Verify clean, maintainable log output

**Current Status**: The integration is stable and production-ready. Future testing focuses on preventing regressions and covering edge cases for the enhanced reliability features.
