# Debugging Strategy: Vacasa Home Assistant Integration

## Overview

This document outlines the systematic approach for debugging the Vacasa integration using logs and diagnostic information. The integration is designed with structured logging to enable rapid problem identification and resolution.

**Current Status**: As of v1.3.0, major timing and reliability issues have been resolved. The integration is now production-ready with enhanced startup coordination, event-driven recovery mechanisms, and corrected calendar logic. This document is maintained for reference and for handling any future edge cases that may emerge.

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

### 1. Authentication Issues (RARE - Well Handled)

**Symptoms**:
- Integration fails to load
- "Authentication failed" errors
- Repeated login attempts

**Current Status**: ✅ **STABLE** - Authentication is well-handled with robust retry mechanisms

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
- **Note**: Most authentication issues self-resolve with the enhanced retry mechanisms

### 2. Calendar Entity Issues (RESOLVED - v1.3.0)

**Previous Symptoms**:
- Calendar entities not showing events
- Binary sensors always show "unavailable"
- Events not updating

**Current Status**: ✅ **RESOLVED** - Enhanced startup coordination ensures proper entity availability

**Historical Log Patterns** (now rare):
```
WARNING: Calendar entity not found for unit 12345
ERROR: Error getting events for Mountain View Getaway: API timeout
DEBUG: Retrieved 0 reservations for unit 12345
```

**Current Behavior**:
- Calendar entities initialize properly with platform dependencies
- Binary sensors wait for calendar availability with automatic retry
- Events update reliably with corrected current event detection logic
- If issues occur, they typically self-resolve with event-driven recovery mechanisms

### 3. Binary Sensor Issues (RESOLVED - v1.3.0)

**Previous Symptoms**:
- Occupancy sensors don't update
- Always show "off" despite active reservations
- Missing guest information

**Current Status**: ✅ **FULLY RESOLVED** - Binary sensor timing and coordination issues eliminated

**Historical Log Patterns** (now very rare):
```
WARNING: Calendar entity not found for Mountain View Getaway, occupancy will be unavailable
DEBUG: Calendar state not found for calendar.vacasa_mountain_view_getaway
ERROR: Error updating occupancy from calendar for Mountain View Getaway: ...
```

**Current Behavior**:
- Binary sensors coordinate properly with calendar entities via platform dependencies
- Occupancy detection works reliably with enhanced startup coordination
- Event-driven recovery handles any temporary unavailability automatically
- Current event detection logic correctly identifies active reservations
- Guest information parsing works consistently

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

### Step 1: Enable Debug Logging (if needed)

Add to Home Assistant configuration.yaml:
```yaml
logger:
  default: info
  logs:
    custom_components.vacasa: debug
```

**Note**: With v1.3.0 improvements, debug logging is typically only needed for edge cases or new issues.

### Step 2: Identify the Problem Area

**Authentication Problems** (rare):
- Look for: `auth`, `token`, `login` in logs
- Focus on: Initial setup, credential validation
- **Status**: Well-handled with automatic retry mechanisms

**Data Retrieval Problems** (rare):
- Look for: `get_units`, `get_reservations`, `API error` in logs
- Focus on: Network issues, API responses
- **Status**: Robust error handling with exponential backoff

**Entity Problems** (resolved):
- Look for: `entity`, `calendar`, `binary_sensor` in logs
- Focus on: Entity creation, state updates
- **Status**: Enhanced startup coordination eliminates most issues

**Timezone/Date Problems** (resolved):
- Look for: `timezone`, `datetime`, `parse_datetime` in logs
- Focus on: Date formatting, timezone conversion
- **Status**: Current event detection logic corrected and working reliably

### Step 3: Common Log Analysis Patterns (v1.3.0)

**Typical Successful Operation Flow** (now standard):
```
DEBUG: Found 2 Vacasa units for binary sensors
DEBUG: Found calendar entity calendar.vacasa_mountain_view_getaway for unit 12345
DEBUG: Unit 12345 occupied: Guest Booking: John Doe
INFO: Successfully updated occupancy for Mountain View Getaway
```

**Historical Failed Operation Flow** (now rare with enhanced coordination):
```
DEBUG: Found 2 Vacasa units for binary sensors
WARNING: Calendar entity not found for unit 12345, scheduling retry
DEBUG: Retrying occupancy update for unit 12345 (attempt 1/3)
DEBUG: Found calendar entity calendar.vacasa_mountain_view_getaway for unit 12345
DEBUG: Unit 12345 occupied: Guest Booking: John Doe
INFO: Successfully updated occupancy for Mountain View Getaway after retry
```

**Current Behavior**: The integration now handles temporary unavailability gracefully with automatic retries and event-driven recovery.

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

## Common Error Resolution (Historical Reference)

**Note**: Most of these issues have been resolved in v1.3.0. This section is maintained for reference.

### "HomeAssistant object has no attribute 'helpers'" (RESOLVED)
- **Status**: ✅ **FIXED** - Proper entity registry access patterns implemented
- **Previous Cause**: Incorrect entity registry access pattern
- **Current State**: Uses centralized const imports and proper async patterns

### "Calendar entity not found" (RESOLVED)
- **Status**: ✅ **FIXED** - Enhanced startup coordination eliminates timing issues
- **Previous Cause**: Entity ID mismatch between calendar and binary sensor during startup
- **Current State**: Platform dependencies and event-driven recovery handle this automatically

### "Authentication failed" (WELL HANDLED)
- **Status**: ✅ **ROBUST** - Enhanced retry mechanisms handle transient failures
- **Cause**: Invalid credentials or expired session (still possible but rare)
- **Current Handling**: Automatic retry with exponential backoff, clear cache service available

### "Blocking call to open" (RESOLVED)
- **Status**: ✅ **FIXED** - All file operations now use proper async patterns
- **Previous Cause**: Synchronous file operations in async context
- **Current State**: Uses `hass.async_add_executor_job()` for all file operations

## Current Status & Escalation Criteria

**Integration Status**: ✅ **PRODUCTION READY** - v1.3.0 is stable with all major issues resolved

**Escalation Now Rarely Needed** - Contact developer support only for:
1. **New/Unknown Issues**: Problems not covered by the enhanced recovery mechanisms
2. **Vacasa API Changes**: If Vacasa makes breaking changes to their API structure
3. **Performance Issues**: Unexpected memory leaks or performance degradation (should be rare)
4. **Home Assistant Compatibility**: Issues with new Home Assistant versions

**Most Common Historical Issues Are Now Resolved**:
- ✅ Authentication reliability - enhanced with retry mechanisms
- ✅ Calendar entity coordination - resolved with startup coordination
- ✅ Binary sensor timing - resolved with event-driven recovery
- ✅ Current event detection - resolved with corrected logic
- ✅ Timezone handling - working correctly

**Include in Support Request** (if needed):
- Home Assistant version
- Integration version (should be v1.3.0 or later)
- Relevant log excerpts (sanitized)
- Entity states from Developer Tools
- Number of properties and typical reservation volume
- **New**: Description of why the enhanced recovery mechanisms didn't handle the issue
