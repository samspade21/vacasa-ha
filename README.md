# Vacasa Properties Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/releases)

[![Validate](https://github.com/samspade21/vacasa-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/samspade21/vacasa-ha/actions/workflows/validate.yml)
[![Dependencies](https://github.com/samspade21/vacasa-ha/actions/workflows/dependencies.yml/badge.svg)](https://github.com/samspade21/vacasa-ha/actions/workflows/dependencies.yml)
[![codecov](https://codecov.io/gh/samspade21/vacasa-ha/branch/main/graph/badge.svg)](https://codecov.io/gh/samspade21/vacasa-ha)

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

### Occupancy Sensor (Binary Sensor)

- Entity ID: `binary_sensor.vacasa_[property_name]_occupancy`
- State: `on` when the property is currently occupied, `off` when vacant
- **Attributes** (use these in automations):
  - `current_guest`: Name of the current guest (if applicable)
  - `current_checkout`: Date and time of the current guest's check-out (ISO format)
  - `current_reservation_type`: Type of current reservation (e.g., "Guest Booking", "Owner Stay", "Maintenance")
  - `next_checkin`: Date and time of the next check-in (ISO format)
  - `next_checkout`: Date and time of the next check-out (ISO format)
  - `next_guest`: Name of the next guest (if applicable)
  - `next_reservation_type`: Type of next reservation (e.g., "Guest Booking", "Owner Stay")

### Next Stay Sensor

- Entity ID: `sensor.vacasa_[property_name]_next_stay`
- State: Number of days until the next check-in
- **Attributes** (use these in automations):
  - `stay_type`: Type of the upcoming stay (e.g., "Guest Booking", "Owner Stay", "Maintenance")
  - `stay_category`: Categorized stay type in lowercase with underscores (e.g., "guest_booking", "owner_stay", "maintenance")
  - `guest_name`: Name of the next guest (if applicable)
  - `checkin_date`: Check-in date and time (ISO format)
  - `checkout_date`: Check-out date and time (ISO format)

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

## Stay Types and Categories

The integration categorizes reservations into the following types. These are available through entity attributes and can be used in automations:

| Display Name | Category Value | Binary Sensor Attribute | Next Stay Attribute | Description |
|-------------|----------------|------------------------|---------------------|-------------|
| **Guest Booking** | `guest_booking` | `Guest Booking` | `guest_booking` | Regular guest reservations |
| **Owner Stay** | `owner_stay` | `Owner Stay` | `owner_stay` | When the property owner is staying |
| **Maintenance** | `maintenance` | `Maintenance` | `maintenance` | Scheduled maintenance visits |
| **Block** | `block` | `Block` | `block` | Property blocks (seasonal holds, etc.) |
| **Other** | `other` | `Other` | `other` | Any other type of reservation |

### Using Stay Types in Automations

Stay types are accessible through different attributes depending on which entity you use:

- **Binary Sensor attributes**: Use `current_reservation_type` or `next_reservation_type` (returns display names like "Guest Booking")
- **Next Stay Sensor attributes**: Use `stay_type` (display name) or `stay_category` (lowercase with underscores like "guest_booking")
- **Calendar event descriptions**: Parse the description field which contains the type information (e.g., "Guest booking from...")

**Recommendation**: Use binary sensor attributes (`current_reservation_type` or `next_reservation_type`) for most automations as they are the most straightforward and reliable.

## Services

The integration provides the following services:

- `vacasa.refresh_data`: Refresh all Vacasa data including calendars, sensors, and property information
- `vacasa.clear_cache`: Clear cached data and tokens

## Automation Examples

**Important Note**: Calendar events do NOT have a `category` attribute. Use the methods shown below to check reservation types in automations.

### Option 1: Using Binary Sensor Attributes (Recommended)

This is the most straightforward and reliable method for checking reservation types.

```yaml
automation:
  - alias: "Adjust Temperature for Guest Arrival"
    trigger:
      - platform: state
        entity_id: binary_sensor.vacasa_vacation_cabin_occupancy
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.vacasa_vacation_cabin_occupancy', 'current_reservation_type') == 'Guest Booking' }}
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 70
      - service: notify.mobile_app
        data:
          title: "Guest Arrival"
          message: "Guests have checked in. Temperature set to 70°F."
```

### Option 2: Using Next Stay Sensor Attributes

Use the next stay sensor when you need to react to upcoming reservations before they start.

```yaml
automation:
  - alias: "Prepare for Upcoming Owner Stay"
    trigger:
      - platform: state
        entity_id: sensor.vacasa_vacation_cabin_next_stay
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.vacasa_vacation_cabin_next_stay', 'stay_category') == 'owner_stay' }}
      - condition: template
        value_template: >
          {{ states('sensor.vacasa_vacation_cabin_next_stay') | int <= 2 }}
    action:
      - service: script.prepare_for_owner
      - service: notify.mobile_app
        data:
          title: "Owner Stay Approaching"
          message: "Owner stay begins in {{ states('sensor.vacasa_vacation_cabin_next_stay') }} days."
```

### Option 3: Using Calendar Event Description

Parse the event description when using calendar triggers. Note: This is less reliable than using sensor attributes.

```yaml
automation:
  - alias: "Notify on Maintenance Arrival"
    trigger:
      - platform: calendar
        event: start
        entity_id: calendar.vacasa_vacation_cabin
    condition:
      - condition: template
        value_template: >
          {{ 'Maintenance' in trigger.calendar_event.description }}
    action:
      - service: notify.mobile_app
        data:
          title: "Maintenance Arrival"
          message: "Maintenance crew has arrived at the property."
```

### Differentiate Between Guest Types

Use the reservation type to apply different settings for guests vs. owners vs. maintenance:

```yaml
automation:
  - alias: "Set Climate Based on Reservation Type"
    trigger:
      - platform: state
        entity_id: binary_sensor.vacasa_vacation_cabin_occupancy
        to: "on"
    action:
      - choose:
          # Guest booking - comfortable temperature
          - conditions:
              - condition: template
                value_template: >
                  {{ state_attr('binary_sensor.vacasa_vacation_cabin_occupancy', 'current_reservation_type') == 'Guest Booking' }}
            sequence:
              - service: climate.set_temperature
                target:
                  entity_id: climate.living_room
                data:
                  temperature: 70
              - service: switch.turn_on
                entity_id: switch.guest_mode

          # Owner stay - preferred settings
          - conditions:
              - condition: template
                value_template: >
                  {{ state_attr('binary_sensor.vacasa_vacation_cabin_occupancy', 'current_reservation_type') == 'Owner Stay' }}
            sequence:
              - service: climate.set_temperature
                target:
                  entity_id: climate.living_room
                data:
                  temperature: 68
              - service: switch.turn_on
                entity_id: switch.owner_mode

          # Maintenance - minimal settings
          - conditions:
              - condition: template
                value_template: >
                  {{ state_attr('binary_sensor.vacasa_vacation_cabin_occupancy', 'current_reservation_type') == 'Maintenance' }}
            sequence:
              - service: climate.set_temperature
                target:
                  entity_id: climate.living_room
                data:
                  temperature: 65
              - service: light.turn_on
                entity_id: light.workshop
        default:
          # Other types - economy mode
          - service: climate.set_temperature
            target:
              entity_id: climate.living_room
            data:
              temperature: 62
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
pip install -r requirements-test.txt
pytest
```

### Release Process for Maintainers

This project uses an automated release process with clear separation between manual preparation and automated deployment.

#### Quick Release Steps

```bash
# 1. Prepare release on main branch
#    - Update VERSION file with new version (e.g., "1.7.1")
#    - Update custom_components/vacasa/manifest.json version field
#    - Update CHANGELOG.md with release notes
#    - Commit all changes: git commit -m "chore: prepare release v1.7.1"

# 2. Run the release script
./new-prod-release.sh

# 3. Review and merge the PR
#    - Script creates PR from development to main
#    - Review PR and ensure CI checks pass
#    - Merge when ready

# 4. Automatic release creation
#    - GitHub Actions automatically creates git tag
#    - Release workflow creates GitHub release with assets
#    - HACS is notified for distribution
```

#### Prerequisites

- **GitHub CLI**: `brew install gh` (macOS) or `sudo apt install gh` (Linux)
- **Authentication**: Run `gh auth login` before first use
- **Clean Working Directory**: All changes must be committed
- **Version Consistency**: VERSION file and manifest.json must match
- **Changelog Entry**: CHANGELOG.md must contain new version section

#### What the Script Does

The `new-prod-release.sh` script:
1. ✅ Validates prerequisites (git, gh CLI authentication)
2. ✅ Verifies you're on development branch with clean working directory
3. ✅ Checks version consistency across VERSION, manifest.json, and CHANGELOG.md
4. ✅ Pushes development branch to GitHub
5. ✅ Creates pull request from development to main
6. ✅ Displays PR information and next steps

After PR merge, GitHub Actions automatically:
1. 🤖 Detects release merge and reads version from VERSION file
2. 🏷️ Creates annotated git tag (e.g., v1.7.1)
3. 📦 Triggers release workflow
4. 🚀 Creates GitHub release with changelog and assets
5. 📢 Notifies HACS for distribution

#### Troubleshooting

**Issue: "GitHub CLI is not authenticated"**
```bash
gh auth login
gh auth status
```

**Issue: "Working directory is not clean"**
```bash
git status
git add .
git commit -m "chore: cleanup before release"
```

**Issue: "Version mismatch"**
```bash
# Check versions
cat VERSION
grep version custom_components/vacasa/manifest.json
grep "## \[" CHANGELOG.md | head -1

# Update all files to match
echo "1.7.1" > VERSION
# Edit manifest.json manually
# Ensure CHANGELOG.md has [1.7.1] entry
```

**Issue: "PR already exists"**
```bash
gh pr list
gh pr close <pr-number>  # Close old PR if needed
./new-prod-release.sh    # Try again
```

**Issue: "Auto-tag workflow didn't trigger"**
- Check commit message contains "Release v" or "prepare release v"
- Manually create tag if needed:
  ```bash
  git checkout main
  git pull origin main
  git tag -a v1.7.1 -m "Release v1.7.1"
  git push origin v1.7.1
  ```

#### Version Management Best Practices

- **Semantic Versioning**: Use MAJOR.MINOR.PATCH format
- **Consistency**: Always update VERSION, manifest.json, and CHANGELOG.md together
- **Changelog Format**: Follow Keep a Changelog format with date
- **Branch Hygiene**: Keep development branch in sync with main after releases
- **Testing**: Test changes thoroughly before creating release PR

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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with or endorsed by Vacasa. The Vacasa API is not officially documented and may change without notice.
