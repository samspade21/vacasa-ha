# Project Brief: Vacasa Home Assistant Integration

## Overview
The Vacasa Home Assistant Integration is a custom component that creates Home Assistant calendars for Vacasa vacation rental properties. It enables homeowners to automate their smart home based on reservation status, enhancing both guest experience and energy efficiency.

## Core Goals
1. Create one Home Assistant calendar per Vacasa property
2. Provide real-time reservation data categorized by stay type (guest, owner, maintenance)
3. Enable standard Home Assistant calendar-based automations
4. Securely store and manage authentication credentials

## Target Users
- Vacasa property owners who use Home Assistant for home automation
- Users who want to automate their vacation rental based on occupancy status

## Key Features
- **Secure Authentication**: Store Vacasa credentials securely using Home Assistant best practices
- **Multiple Property Support**: Create separate calendars for each property with reliable occupancy sensors
- **Stay Type Categorization**: Distinguish between guest bookings, owner stays, and maintenance visits
- **Automatic Refresh**: Update calendar data periodically (default: every 4 hours) with intelligent caching
- **Token Management**: Handle authentication token caching and refresh with robust retry mechanisms
- **Reliable Occupancy Detection**: Enhanced startup coordination and event-driven recovery for consistent operation
- **Current Event Awareness**: Accurately detect what's happening now vs future events for precise automation
- **Production-Ready Logging**: Clean, maintainable status output for long-term operation

## Use Cases
1. **Energy Management**: Adjust thermostats based on occupancy (e.g., 70°F during guest stays, 60°F when vacant)
2. **Welcome Automation**: Turn on lights and adjust settings when guests check in
3. **Maintenance Preparation**: Prepare the property differently for maintenance visits
4. **Owner Stay Customization**: Apply different settings when the owner is staying

## Technical Requirements
- Pure HTTP-based authentication (no browser automation)
- Async-compatible for Home Assistant integration with enhanced startup coordination
- Minimal dependencies with intelligent caching and connection pooling
- Secure credential storage with production-ready error handling
- Efficient token caching and management with automatic retry mechanisms
- Platform dependency management for reliable entity initialization
- Event-driven recovery patterns for handling temporary unavailability
- Clean logging patterns suitable for production environments

## Success Criteria
- Reliable calendar data that matches the Vacasa owner portal with accurate current event detection
- Seamless integration with Home Assistant calendar automations and occupancy-based triggers
- Minimal configuration required from users with automatic error recovery
- Secure handling of authentication credentials with robust token management
- Consistent occupancy detection that works reliably without manual intervention
- Production-ready operation with clean logging and maintainable code
- Enhanced startup coordination preventing timing-related issues
