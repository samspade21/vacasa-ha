# Vacasa Properties Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/releases)
[![License](https://img.shields.io/github/license/samspade21/vacasa-ha.svg?style=flat-square)](LICENSE)

[![Validate](https://github.com/samspade21/vacasa-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/samspade21/vacasa-ha/actions/workflows/validate.yml)
[![Dependencies](https://github.com/samspade21/vacasa-ha/actions/workflows/dependencies.yml/badge.svg)](https://github.com/samspade21/vacasa-ha/actions/workflows/dependencies.yml)
[![codecov](https://codecov.io/gh/samspade21/vacasa-ha/branch/main/graph/badge.svg)](https://codecov.io/gh/samspade21/vacasa-ha)

[![GitHub issues](https://img.shields.io/github/issues/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/pulls)
[![GitHub stars](https://img.shields.io/github/stars/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/network)

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2025.1+-blue.svg)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A comprehensive Home Assistant integration for Vacasa vacation rental properties that provides calendars, occupancy sensors, and detailed property information, enabling powerful smart home automation based on reservation status and property characteristics.

## Features

- Creates one Home Assistant calendar per Vacasa property
- Provides binary sensors for property occupancy status
- Creates detailed property information sensors (rating, location, amenities, etc.)
- Uses property-specific check-in/check-out times and timezone information
- Categorizes reservations by stay type (guest bookings, owner stays, maintenance)
- Enables powerful Home Assistant automations based on property data
- Securely stores and manages authentication credentials
- Automatically refreshes data periodically

## Use Cases

- **Energy Management**: Adjust thermostats based on occupancy (e.g., 70°F during guest stays, 60°F when vacant)
- **Welcome Automation**: Turn on lights and adjust settings when guests check in
- **Maintenance Preparation**: Prepare the property differently for maintenance visits
- **Owner Stay Customization**: Apply different settings when the owner is staying
- **Occupancy-Based Control**: Trigger automations based on whether the property is currently occupied

## Installation

### HACS Installation (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL `https://github.com/samspade21/vacasa-ha`
   - Select "Integration" as the category
   - Click "Add"
3. Search for "Vacasa" in HACS and install it
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/vacasa` directory to your Home Assistant configuration directory.
2. Restart Home Assistant.
3. Go to Configuration > Integrations > Add Integration.
4. Search for "Vacasa" and follow the configuration steps.

## Configuration

The integration can be configured through the Home Assistant UI:

1. Go to **Configuration** > **Integrations** > **Add Integration**.
2. Search for "Vacasa" and select it.
3. Enter your Vacasa username (email) and password.
4. Set the refresh interval (default: 8 hours).
5. Click "Submit" to complete the setup.

The integration will automatically discover all your Vacasa properties and create entities for each one.

## Entities Created

For each Vacasa property, the integration creates:

### Calendar Entity

- Entity ID: `calendar.vacasa_[property_name]`
- Shows all reservations with their check-in and check-out times
- Categorizes reservations by type (guest, owner, maintenance, etc.)
- Includes detailed information in event descriptions

### Occupancy Sensor

- Entity ID: `binary_sensor.vacasa_[property_name]_occupancy`
- State: `on` when the property is currently occupied, `off` when vacant
- Attributes:
  - `current_guest`: Name of the current guest (if applicable)
  - `current_checkout`: Date and time of the current guest's check-out
  - `current_reservation_type`: Type of the current reservation
  - `next_checkin`: Date and time of the next check-in
  - `next_checkout`: Date and time of the next check-out
  - `next_guest`: Name of the next guest (if applicable)
  - `next_reservation_type`: Type of the next reservation

### Property Information Sensors

#### Property Details
- **Rating**: Star rating of the property (e.g., 5★)
- **Location**: Latitude/longitude coordinates with attributes for mapping
- **Timezone**: Property's timezone (e.g., "America/Los_Angeles")
- **Address**: Formatted property address with detailed attributes

#### Capacity Information
- **Max Occupancy**: Maximum total occupants allowed
- **Max Adults**: Maximum number of adults allowed
- **Max Children**: Maximum number of children allowed
- **Max Pets**: Maximum number of pets allowed

#### Amenities
- **Bedrooms**: Number of bedrooms with attributes for bed types
- **Bathrooms**: Number of bathrooms (full + half) with detailed attributes
- **Hot Tub**: Whether the property has a hot tub ("Yes"/"No")
- **Pet Friendly**: Whether the property allows pets ("Yes"/"No")
- **Parking**: Number of parking spaces with detailed attributes

## Calendar Categories

The integration categorizes reservations into the following types:

- **Guest Booking**: Reservations made by guests
- **Owner Stay**: Reservations made by the property owner
- **Maintenance**: Maintenance visits
- **Block**: Other types of blocks (e.g., seasonal holds)
- **Other**: Any other type of reservation

These categories can be used in automations to trigger different actions based on the type of reservation.

## Services

The integration provides the following services:

- `vacasa.refresh_data`: Refresh all Vacasa data including calendars, sensors, and property information
- `vacasa.clear_cache`: Clear cached data and tokens

## Automation Examples

### Adjust Temperature for Guest Arrival

```yaml
automation:
  - alias: "Adjust Temperature for Guest Arrival"
    trigger:
      - platform: calendar
        event: start
        entity_id: calendar.vacasa_vacation_cabin
    condition:
      - condition: template
        value_template: "{{ trigger.calendar_event.category == 'guest_booking' }}"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 70
```

### Turn Down Heat When Vacant

```yaml
automation:
  - alias: "Turn Down Heat When Vacant"
    trigger:
      - platform: state
        entity_id: binary_sensor.vacasa_vacation_cabin_occupancy
        from: "on"
        to: "off"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 60
```

### Prepare for Next Guest

```yaml
automation:
  - alias: "Prepare for Next Guest"
    trigger:
      - platform: state
        entity_id: binary_sensor.vacasa_vacation_cabin_occupancy
        from: "on"
        to: "off"
    condition:
      - condition: template
        value_template: >
          {% set next_checkin = state_attr('binary_sensor.vacasa_vacation_cabin_occupancy', 'next_checkin') %}
          {% set hours_until_checkin = ((as_timestamp(next_checkin) - as_timestamp(now())) / 3600) | round(1) %}
          {{ next_checkin is not none and hours_until_checkin < 24 and hours_until_checkin > 0 }}
    action:
      - service: script.prepare_for_guests
```

### Adjust Hot Tub Settings Based on Property Amenities

```yaml
automation:
  - alias: "Configure Hot Tub if Available"
    trigger:
      - platform: homeassistant
        event: start
      - platform: state
        entity_id: sensor.vacasa_vacation_cabin_hot_tub
    condition:
      - condition: state
        entity_id: sensor.vacasa_vacation_cabin_hot_tub
        state: "Yes"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.hot_tub_power
      - service: climate.set_temperature
        target:
          entity_id: climate.hot_tub
        data:
          temperature: 102
      - service: notify.mobile_app
        data:
          title: "Hot Tub Ready"
          message: "The hot tub at {{ states('sensor.vacasa_vacation_cabin_address') }} is now ready for use."
```

### Display Property Information on Dashboard

```yaml
# Example Lovelace card configuration
type: entities
title: Vacation Property Details
entities:
  - entity: sensor.vacasa_vacation_cabin_rating
  - entity: sensor.vacasa_vacation_cabin_bedrooms
  - entity: sensor.vacasa_vacation_cabin_bathrooms
  - entity: sensor.vacasa_vacation_cabin_max_occupancy
  - entity: sensor.vacasa_vacation_cabin_hot_tub
  - entity: sensor.vacasa_vacation_cabin_pet_friendly
  - entity: sensor.vacasa_vacation_cabin_timezone
footer:
  type: graph
  entity: binary_sensor.vacasa_vacation_cabin_occupancy
  hours_to_show: 168
```

## Troubleshooting

### Common Issues

#### Authentication Problems

**Issue**: Integration fails to authenticate with Vacasa
- **Symptoms**: "Invalid credentials" error, entities show as unavailable
- **Solutions**:
  1. Verify your Vacasa username (email) and password are correct
  2. Try logging into the Vacasa owner portal directly to confirm credentials
  3. Check if your account has two-factor authentication enabled (currently not supported)
  4. Ensure your account has access to properties (owner or manager permissions)

**Issue**: Authentication tokens expire frequently
- **Symptoms**: Entities become unavailable after working initially
- **Solutions**:
  1. Enable debug logging to see token refresh attempts
  2. Check network connectivity between Home Assistant and Vacasa servers
  3. Restart the integration via Configuration > Integrations

#### Entity Issues

**Issue**: Calendar entities show no events
- **Symptoms**: Calendar appears empty despite having reservations
- **Solutions**:
  1. Check the date range - calendars show events from 30 days ago to 365 days ahead
  2. Verify the property has actual reservations in the Vacasa portal
  3. Use the `vacasa.refresh_data` service to force a data refresh
  4. Check logs for API errors or rate limiting

**Issue**: Occupancy sensors show incorrect status
- **Symptoms**: Binary sensor shows "off" when property should be occupied
- **Solutions**:
  1. Check if calendar events exist for the current period
  2. Verify check-in/check-out times are configured correctly
  3. Review the occupancy sensor attributes for debugging information
  4. Ensure your Home Assistant timezone matches the property timezone

**Issue**: Property information sensors missing or incorrect
- **Symptoms**: Some property sensors don't appear or show wrong values
- **Solutions**:
  1. Check if the property information is complete in the Vacasa portal
  2. Use `vacasa.refresh_data` to reload property information
  3. Verify the integration has the latest property data from Vacasa

#### Performance Issues

**Issue**: Integration loads slowly or times out
- **Symptoms**: Long startup times, frequent "unavailable" states
- **Solutions**:
  1. Increase the refresh interval to reduce API calls
  2. Check your internet connection and DNS resolution
  3. Monitor Home Assistant logs for network errors
  4. Consider using the performance optimization settings in configuration

#### Configuration Issues

**Issue**: Can't update credentials in options flow
- **Symptoms**: Changes to username/password don't take effect
- **Solutions**:
  1. Ensure you're using the integration's options flow (not reconfiguring)
  2. Restart Home Assistant after credential changes
  3. Clear the integration cache using `vacasa.clear_cache` service
  4. If still failing, remove and re-add the integration

### Debug Logging

To enable detailed debug logging for troubleshooting:

1. Add the following to your `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.vacasa: debug
```

2. Restart Home Assistant

3. Check the logs for detailed information about API calls, authentication, and data processing

### Useful Debug Information

When reporting issues, please include:

- Home Assistant version
- Integration version
- Relevant log entries with debug logging enabled
- Entity states and attributes
- Configuration details (without passwords)
- Steps to reproduce the issue

### Performance Optimization

For better performance with multiple properties:

1. **Adjust Refresh Interval**: Increase the refresh interval in integration options
2. **Monitor API Usage**: Watch for rate limiting in logs
3. **Use Efficient Automations**: Prefer state-based triggers over frequent polling
4. **Enable Caching**: Use the built-in property data caching (enabled by default)

### Network Troubleshooting

If you're experiencing network-related issues:

1. **Check Connectivity**: Ensure Home Assistant can reach Vacasa servers
2. **DNS Resolution**: Verify DNS is working correctly
3. **Firewall**: Check for firewall rules blocking outbound HTTPS traffic
4. **Proxy Settings**: If using a proxy, ensure it's configured correctly

### Getting Help

If you're still experiencing issues:

1. **Search Existing Issues**: Check the [GitHub issues](https://github.com/samspade21/vacasa-ha/issues)
2. **Enable Debug Logging**: Follow the debug logging instructions above
3. **Create an Issue**: Use the bug report template with detailed information
4. **Community Support**: Join discussions in the repository

## Development

### Prerequisites

- Python 3.9 or higher
- Home Assistant development environment
- Pre-commit

### Setup Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/samspade21/vacasa-ha.git
   cd vacasa-ha
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
pytest
```

### Automated Release Deployment

For maintainers, this project includes a fully automated release deployment process that handles the entire workflow from development branch to production release.

#### Quick Release

```bash
# 1. Update VERSION file and manifest.json with new version
# 2. Update CHANGELOG.md with release notes
# 3. Commit changes to development branch
# 4. Run automated deployment
./deploy.sh
```

The script automatically:
- ✅ Validates environment and version consistency
- ✅ Runs all tests and quality checks
- ✅ Pushes development branch and waits for CI/CD validation
- ✅ Creates and merges pull request to main branch
- ✅ Triggers GitHub release workflow
- ✅ Monitors release completion and verifies success
- ✅ Updates main branch with release artifacts

#### Prerequisites for Release Deployment

- **GitHub CLI**: `brew install gh` (macOS) or equivalent
- **Authentication**: `gh auth login`
- **Clean Development Branch**: All changes committed
- **Version Consistency**: VERSION file and manifest.json updated
- **Changelog Updated**: CHANGELOG.md contains release notes

#### Release Process Documentation

For detailed instructions, troubleshooting, and advanced configuration options, see:
**📖 [Complete Deployment Guide](DEPLOYMENT.md)**

The deployment guide covers:
- Step-by-step setup instructions
- Version management best practices
- CI/CD workflow integration
- Troubleshooting common issues
- Manual deployment procedures
- Rollback processes

## Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or helping with testing, your contributions help make this integration better for everyone.

### Ways to Contribute

- **Bug Reports**: Help us identify and fix issues
- **Feature Requests**: Suggest new functionality or improvements
- **Code Contributions**: Submit bug fixes, new features, or optimizations
- **Documentation**: Improve README, add examples, or clarify instructions
- **Testing**: Test with different configurations and report findings
- **Translations**: Help translate the integration to other languages

### Before Contributing

1. **Search Existing Issues**: Check if your bug/feature has already been reported
2. **Review Documentation**: Make sure you understand the project structure and goals
3. **Test Your Changes**: Ensure your changes work as expected
4. **Follow Code Standards**: Maintain consistency with existing code style

### Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/yourusername/vacasa-ha.git
   cd vacasa-ha
   ```

2. **Create Development Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Pre-commit Hooks**:
   ```bash
   pre-commit install
   ```

4. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Code Standards

- **Python Style**: Follow PEP 8 and use the existing code style
- **Type Hints**: Add type hints to new functions and methods
- **Documentation**: Add docstrings to new functions and classes
- **Error Handling**: Implement proper exception handling
- **Async/Await**: Use async patterns for I/O operations
- **Logging**: Use appropriate logging levels (debug, info, warning, error)

### Testing Guidelines

1. **Unit Tests**: Add tests for new functionality
2. **Integration Tests**: Test with Home Assistant when possible
3. **Manual Testing**: Test with real Vacasa accounts when feasible
4. **Edge Cases**: Consider error conditions and edge cases

### Submitting Changes

1. **Create Quality Commits**:
   ```bash
   git add .
   git commit -m "feat: add new occupancy prediction feature"
   ```

2. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request**: Use the provided PR template and fill out all sections

### Pull Request Guidelines

- **Clear Description**: Explain what your changes do and why
- **Reference Issues**: Link to related issues with "Fixes #123" or "Closes #456"
- **Test Results**: Include information about testing performed
- **Breaking Changes**: Clearly document any breaking changes
- **Documentation**: Update README or other docs as needed

### Commit Message Format

We use conventional commits for better release automation:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add property timezone detection
fix: resolve calendar event timezone issues
docs: update troubleshooting guide
```

### Review Process

1. **Automated Checks**: All PRs must pass CI/CD checks
2. **Code Review**: Maintainers will review your code
3. **Testing**: Changes may be tested with live Vacasa accounts
4. **Documentation**: Ensure documentation is updated as needed

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a welcoming environment

### Getting Help

- **Questions**: Open a discussion or ask in an issue
- **Development Help**: Reach out to maintainers
- **Feature Discussion**: Create a feature request issue first

### Recognition

Contributors are recognized in:
- Release notes for their contributions
- README contributors section (if added)
- Git commit history

Thank you for contributing to the Vacasa Home Assistant integration! 🎉

## For Developers

This project uses Cline Memory Bank for comprehensive documentation and context management. The memory bank provides a structured way to maintain project knowledge and ensure consistent development across time.

### Memory Bank Overview

The memory bank is a collection of markdown files that document different aspects of the project. It serves as a knowledge repository that helps developers understand the project's architecture, design decisions, and implementation details.

- **Documentation**: [Cline Memory Bank Documentation](https://docs.cline.bot/prompting/cline-memory-bank)
- **Purpose**: Maintains project context across development sessions
- **Benefits**: Easier onboarding, consistent development, and better knowledge retention

### Memory Bank Structure

The project's memory bank contains the following files:

- [Project Brief](memory-bank/projectbrief.md) - Core requirements and goals
- [Product Context](memory-bank/productContext.md) - Why this project exists and how it should work
- [Active Context](memory-bank/activeContext.md) - Current work focus and recent changes
- [System Patterns](memory-bank/systemPatterns.md) - Architecture and design patterns
- [Tech Context](memory-bank/techContext.md) - Technologies, dependencies, and technical details
- [Progress](memory-bank/progress.md) - Current status, completed features, and next steps

### Working with Cline

[Cline](https://docs.cline.bot/) is an AI assistant designed to work with codebases and maintain context across development sessions. To use Cline with this project:

1. **Setup Cline**: Follow the [installation instructions](https://docs.cline.bot/getting-started/installation)
2. **Read the Memory Bank**: Cline will automatically read the memory bank files to understand the project
3. **Update Documentation**: When making significant changes, update the relevant memory bank files

### Development Workflow

When working on this project with Cline:

1. **Start with Context**: Begin by reviewing the memory bank files to understand the current state
2. **Implement Changes**: Make your code changes with Cline's assistance
3. **Update Documentation**: Update the memory bank files to reflect your changes
4. **Commit Changes**: Include both code and documentation changes in your commits

This approach ensures that project knowledge is maintained and accessible to all contributors.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with or endorsed by Vacasa. The Vacasa API is not officially documented and may change without notice.
