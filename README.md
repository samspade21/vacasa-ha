# Vacasa Properties Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/releases)
[![Dependencies](https://github.com/samspade21/vacasa-ha/actions/workflows/dependencies.yml/badge.svg)](https://github.com/samspade21/vacasa-ha/actions/workflows/dependencies.yml)

A Home Assistant integration for Vacasa vacation rental properties that provides calendars, occupancy sensors, and detailed property information for powerful smart home automation.

## Features

- Calendar entity for each Vacasa property showing all reservations
- Binary sensors for property occupancy status
- Property information sensors (rating, location, amenities, capacity)
- Property-specific check-in/check-out times and timezone handling
- Categorized reservations by stay type (guest, owner, maintenance, block)
- Automatic data refresh with configurable intervals
- Services for manual refresh and cache clearing

## Installation

### HACS Installation (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in Home Assistant
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations > ⋮ > Custom repositories
   - URL: `https://github.com/samspade21/vacasa-ha`
   - Category: Integration
3. Search for "Vacasa" in HACS and install
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/vacasa` directory to your Home Assistant configuration directory
2. Restart Home Assistant
3. Go to Configuration > Integrations > Add Integration
4. Search for "Vacasa" and follow the configuration steps

## Configuration

Configure through the Home Assistant UI:

1. Go to **Configuration** > **Integrations** > **Add Integration**
2. Search for "Vacasa"
3. Enter your Vacasa username (email) and password
4. Set the refresh interval (default: 8 hours)
5. Click "Submit"

The integration will automatically discover all your properties and create entities.

## Entities Created

### Calendar Entity
- **Entity ID**: `calendar.vacasa_[property_name]`
- Shows all reservations with check-in/check-out times
- Categorized by reservation type

### Occupancy Sensor (Binary Sensor)
- **Entity ID**: `binary_sensor.vacasa_[property_name]_occupancy`
- **State**: `on` when occupied, `off` when vacant
- **Attributes**:
  - `current_guest`: Current guest name
  - `current_checkout`: Current checkout date/time (ISO format)
  - `current_reservation_type`: Current reservation type
  - `next_checkin`: Next check-in date/time (ISO format)
  - `next_checkout`: Next checkout date/time (ISO format)
  - `next_guest`: Next guest name
  - `next_reservation_type`: Next reservation type

### Next Stay Sensor
- **Entity ID**: `sensor.vacasa_[property_name]_next_stay`
- **State**: Days until next check-in
- **Attributes**:
  - `stay_type`: Display name (e.g., "Guest Booking")
  - `stay_category`: Lowercase with underscores (e.g., "guest_booking")
  - `guest_name`: Next guest name
  - `checkin_date`: Check-in date/time (ISO format)
  - `checkout_date`: Checkout date/time (ISO format)

### Property Information Sensors
- **Details**: Rating, location (lat/lon), timezone, address
- **Capacity**: Max occupancy, adults, children, pets
- **Amenities**: Bedrooms, bathrooms, hot tub, pet friendly, parking

## Stay Types

| Display Name | Category Value | Description |
|-------------|----------------|-------------|
| Guest Booking | `guest_booking` | Regular guest reservations |
| Owner Stay | `owner_stay` | Property owner staying |
| Maintenance | `maintenance` | Scheduled maintenance |
| Block | `block` | Property blocks/holds |
| Other | `other` | Other reservation types |

**Using in Automations**: Use binary sensor attributes `current_reservation_type` or `next_reservation_type` for most reliable automation triggers.

## Services

- **`vacasa.refresh_data`**: Manually refresh all Vacasa data
- **`vacasa.clear_cache`**: Clear cached data and tokens

## Automation Examples

### Adjust Temperature Based on Occupancy

```yaml
automation:
  - alias: "Set Climate Based on Occupancy"
    trigger:
      - platform: state
        entity_id: binary_sensor.vacasa_vacation_cabin_occupancy
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

        # Default - economy mode when vacant
        default:
          - service: climate.set_temperature
            target:
              entity_id: climate.living_room
            data:
              temperature: 60
```

### Prepare for Guest Arrival

```yaml
automation:
  - alias: "Prepare for Next Guest"
    trigger:
      - platform: state
        entity_id: binary_sensor.vacasa_vacation_cabin_occupancy
        to: "off"
    condition:
      - condition: template
        value_template: >
          {% set next_checkin = state_attr('binary_sensor.vacasa_vacation_cabin_occupancy', 'next_checkin') %}
          {% set hours_until = ((as_timestamp(next_checkin) - as_timestamp(now())) / 3600) | round(1) %}
          {{ next_checkin is not none and hours_until < 24 and hours_until > 0 }}
    action:
      - service: script.prepare_for_guests
      - service: notify.mobile_app
        data:
          message: "Preparing for guest arrival in {{ hours_until }} hours"
```

### React to Upcoming Owner Stay

```yaml
automation:
  - alias: "Prepare for Owner Stay"
    trigger:
      - platform: numeric_state
        entity_id: sensor.vacasa_vacation_cabin_next_stay
        below: 3
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.vacasa_vacation_cabin_next_stay', 'stay_category') == 'owner_stay' }}
    action:
      - service: script.prepare_for_owner
```

## Troubleshooting

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.vacasa: debug
```

### Common Issues

**Authentication fails**: Verify credentials in Vacasa owner portal. Two-factor authentication is not currently supported.

**Calendar shows no events**: Check date range (30 days past to 365 days future). Use `vacasa.refresh_data` service to force refresh.

**Occupancy sensor incorrect**: Verify check-in/check-out times in calendar. Ensure Home Assistant timezone matches property timezone.

**Entities unavailable**: Check debug logs for API errors. Try restarting the integration via Configuration > Integrations.

### Getting Help

1. Search [GitHub issues](https://github.com/samspade21/vacasa-ha/issues)
2. Enable debug logging and review logs
3. Create an issue with detailed information:
   - Home Assistant version
   - Integration version
   - Relevant log entries
   - Steps to reproduce

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/samspade21/vacasa-ha.git
cd vacasa-ha

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
pytest
```

### Code Standards

- Follow PEP 8 style guidelines
- Add type hints to functions
- Include docstrings for new code
- Use async/await for I/O operations
- Implement proper error handling
- Use appropriate logging levels

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

Contributions are welcome! Please:

1. Fork the repository and create a feature branch
2. Follow existing code style and standards
3. Add tests for new functionality
4. Update documentation as needed
5. Create a pull request with clear description

### Commit Message Format

Use conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test updates
- `chore:` - Maintenance tasks

See [CHANGELOG.md](CHANGELOG.md) for release history and detailed changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with or endorsed by Vacasa. The Vacasa API is not officially documented and may change without notice.
