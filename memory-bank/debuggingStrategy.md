# Debugging Strategy: Vacasa Home Assistant Integration

## Overview

This document outlines the systematic approach for debugging the Vacasa integration using logs and diagnostic information. The integration is designed with structured logging to enable rapid problem identification and resolution.

## Logging Levels & Patterns

### DEBUG Level (Most Verbose)
Used for detailed operational information:
```
DEBUG: Found calendar entity calendar.vacasa_mountain_view_getaway for unit 12345
DEBUG: Unit 12345 occupied: Guest Booking: John Doe
DEBUG: Unit 12345 not occupied
```

**When to enable**: During setup, troubleshooting entity issues, or investigating state changes.

### INFO Level (Normal Operations)
Used for successful operations and status updates:
```
INFO: Successfully created 3 calendar events for Mountain View Getaway
INFO: Vacasa integration setup completed with 2 properties
```

### WARNING Level (Recoverable Issues)
Used for issues that don't break functionality:
```
WARNING: Calendar entity not found for unit 12345 (tried calendar.vacasa_mountain_view_getaway and calendar.vacasa_calendar_12345)
WARNING: Missing timezone for Mountain View Getaway, using local time
```

### ERROR Level (Serious Issues)
Used for failures that impact functionality:
```
ERROR: Error updating occupancy from calendar for Mountain View Getaway: 'HomeAssistant' object has no attribute 'helpers'
ERROR: Failed to process reservation 67890 for Mountain View Getaway: Invalid date format
```

## Common Debugging Scenarios

### 1. Authentication Issues

**Symptoms**:
- Integration fails to load
- "Authentication failed" errors
- Repeated login attempts

**Log Patterns to Look For**:
```
ERROR: Authentication failed: Invalid credentials
ERROR: Failed to load login page: 403
WARNING: Authentication attempt 2/3 failed: ConnectionTimeout
```

**Diagnostic Steps**:
1. Check if credentials are valid in Vacasa portal
2. Verify network connectivity to Vacasa services
3. Look for CSRF token extraction failures
4. Check for rate limiting (429 errors)

**Resolution Hints**:
- Clear token cache: Use "Clear Cache" service
- Verify username/password in configuration
- Check for Vacasa service outages

### 2. Calendar Entity Issues

**Symptoms**:
- Calendar entities not showing events
- Binary sensors always show "unavailable"
- Events not updating

**Log Patterns to Look For**:
```
WARNING: Calendar entity not found for unit 12345
ERROR: Error getting events for Mountain View Getaway: API timeout
DEBUG: Retrieved 0 reservations for unit 12345
```

**Diagnostic Steps**:
1. Verify calendar entities exist in Home Assistant
2. Check coordinator update status
3. Examine API response data
4. Verify property has reservations in Vacasa portal

### 3. Binary Sensor Issues

**Symptoms**:
- Occupancy sensors don't update
- Always show "off" despite active reservations
- Missing guest information

**Log Patterns to Look For**:
```
WARNING: Calendar entity not found for Mountain View Getaway, occupancy will be unavailable
DEBUG: Calendar state not found for calendar.vacasa_mountain_view_getaway
ERROR: Error updating occupancy from calendar for Mountain View Getaway: ...
```

**Diagnostic Steps**:
1. Verify corresponding calendar entity exists
2. Check calendar entity state in Developer Tools
3. Examine event summary parsing
4. Verify entity registry entries

### 4. Data Parsing Issues

**Symptoms**:
- Events with wrong times
- Missing guest names
- Incorrect reservation types

**Log Patterns to Look For**:
```
WARNING: Error applying timezone America/Los_Angeles: ...
DEBUG: Using default check-in time (4 PM) for Mountain View Getaway
ERROR: Error converting reservation to event: KeyError 'startDate'
```

## Troubleshooting Guide

### Step 1: Enable Debug Logging

Add to Home Assistant configuration.yaml:
```yaml
logger:
  default: info
  logs:
    custom_components.vacasa: debug
```

### Step 2: Identify the Problem Area

**Authentication Problems**:
- Look for: `auth`, `token`, `login` in logs
- Focus on: Initial setup, credential validation

**Data Retrieval Problems**:
- Look for: `get_units`, `get_reservations`, `API error` in logs
- Focus on: Network issues, API responses

**Entity Problems**:
- Look for: `entity`, `calendar`, `binary_sensor` in logs
- Focus on: Entity creation, state updates

**Timezone/Date Problems**:
- Look for: `timezone`, `datetime`, `parse_datetime` in logs
- Focus on: Date formatting, timezone conversion

### Step 3: Common Log Analysis Patterns

**Successful Operation Flow**:
```
DEBUG: Found 2 Vacasa units for binary sensors
DEBUG: Found calendar entity calendar.vacasa_mountain_view_getaway for unit 12345
DEBUG: Unit 12345 occupied: Guest Booking: John Doe
INFO: Successfully updated occupancy for Mountain View Getaway
```

**Failed Operation Flow**:
```
DEBUG: Found 2 Vacasa units for binary sensors
WARNING: Calendar entity not found for unit 12345 (tried calendar.vacasa_mountain_view_getaway and calendar.vacasa_calendar_12345)
ERROR: Error updating occupancy from calendar for Mountain View Getaway: Calendar entity not found
```

### Step 4: Entity Verification

Check in Home Assistant Developer Tools > States:
- Calendar entities: `calendar.vacasa_*`
- Binary sensors: `binary_sensor.vacasa_*_occupancy`
- Property sensors: `sensor.vacasa_*_*`

### Step 5: Service Testing

Use Developer Tools > Services to test:
- `vacasa.refresh_data` - Force data refresh
- `vacasa.clear_cache` - Clear authentication cache

## Sensitive Data Handling

### What Gets Logged (Safe)
- Unit IDs (numeric identifiers)
- Property names (public information)
- Reservation dates and times
- Entity IDs and states
- API response structure (without sensitive data)

### What Doesn't Get Logged (Secure)
- Usernames and passwords
- Authentication tokens
- Guest full names (only first names in some contexts)
- Personal contact information
- Payment or booking details

### Log Sanitization
The integration automatically sanitizes logs:
- Tokens are truncated: `Token: abc123...`
- Passwords are never logged
- Guest names are limited to summary format: `Guest Booking: John D.`

## Remote Debugging Commands

### SSH Log Access (if available)
```bash
# View recent Vacasa logs
tail -f /config/home-assistant.log | grep -i vacasa

# Search for specific errors
grep -i "vacasa.*error" /config/home-assistant.log | tail -20

# Check entity states
cat /config/.storage/core.entity_registry | jq '.data.entities[] | select(.platform=="vacasa")'
```

### Integration Restart
```bash
# Restart Home Assistant (if needed)
ha core restart

# Or reload just the integration
# Use Developer Tools > YAML > Integrations
```

## Common Error Resolution

### "HomeAssistant object has no attribute 'helpers'"
- **Cause**: Incorrect entity registry access pattern
- **Fix**: Update to proper `entity_registry.async_get(hass)` pattern
- **Prevention**: Use centralized const imports

### "Calendar entity not found"
- **Cause**: Entity ID mismatch between calendar and binary sensor
- **Fix**: Check calendar entity names in Developer Tools
- **Prevention**: Use predictable naming patterns

### "Authentication failed"
- **Cause**: Invalid credentials or expired session
- **Fix**: Reconfigure integration or clear cache
- **Prevention**: Implement proper token refresh

### "Blocking call to open"
- **Cause**: Synchronous file operations in async context
- **Fix**: Use `hass.async_add_executor_job()` for file operations
- **Prevention**: Always use async patterns in Home Assistant

## Escalation Criteria

Contact developer support when:
1. Authentication works but no data is retrieved
2. Calendar entities exist but never update
3. Logs show successful API calls but empty responses
4. Timezone handling produces incorrect dates consistently
5. Memory leaks or performance degradation over time

Include in support request:
- Home Assistant version
- Integration version
- Relevant log excerpts (sanitized)
- Entity states from Developer Tools
- Number of properties and typical reservation volume
