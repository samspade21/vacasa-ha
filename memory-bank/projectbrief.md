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
- **Multiple Property Support**: Create separate calendars for each property
- **Stay Type Categorization**: Distinguish between guest bookings, owner stays, and maintenance visits
- **Automatic Refresh**: Update calendar data periodically (default: every 4 hours)
- **Token Management**: Handle authentication token caching and refresh

## Use Cases
1. **Energy Management**: Adjust thermostats based on occupancy (e.g., 70°F during guest stays, 60°F when vacant)
2. **Welcome Automation**: Turn on lights and adjust settings when guests check in
3. **Maintenance Preparation**: Prepare the property differently for maintenance visits
4. **Owner Stay Customization**: Apply different settings when the owner is staying

## Technical Requirements
- Pure HTTP-based authentication (no browser automation)
- Async-compatible for Home Assistant integration
- Minimal dependencies
- Secure credential storage
- Efficient token caching and management

## Success Criteria
- Reliable calendar data that matches the Vacasa owner portal
- Seamless integration with Home Assistant calendar automations
- Minimal configuration required from users
- Secure handling of authentication credentials
