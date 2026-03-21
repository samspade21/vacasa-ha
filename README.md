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
4. Set the refresh interval (default: 8 hours, range: 1–24 hours)
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
  - `current_checkout`: Current checkout date/time (formatted local time)
  - `current_reservation_type`: Current reservation type display name (e.g., "Guest Booking")
  - `next_checkin`: Next check-in date/time (formatted local time)
  - `next_checkout`: Next checkout date/time (formatted local time)
  - `next_guest`: Next guest name
  - `next_reservation_type`: Next reservation type display name (e.g., "Owner Stay")

### Next Stay Sensor
- **Entity ID**: `sensor.vacasa_[property_name]_next_stay`
- **State**: Human-readable description such as `"Guest Booking (today)"`, `"Owner Stay in 5 days"`, `"Guest Booking (currently occupied)"`, or `"No upcoming reservations"`
- **Attributes**:
  - `summary`: Full summary string (e.g., "Guest Booking: John Doe")
  - `reservation_id`: Reservation identifier
  - `checkin_date`: Check-in date/time (ISO format)
  - `checkout_date`: Checkout date/time (ISO format)
  - `checkin_time`: Check-in time only (ISO format)
  - `checkout_time`: Checkout time only (ISO format)
  - `stay_type`: Raw stay type identifier (e.g., `"guest"`, `"owner"`, `"block"`, `"maintenance"`)
  - `stay_category`: Category string with underscores (e.g., `"guest_booking"`, `"owner_stay"`)
  - `guest_name`: Guest or owner name
  - `guest_count`: Number of guests
  - `days_until_checkin`: Days until check-in (upcoming reservations only; `null` if currently occupied)
  - `days_until_checkout`: Days until checkout
  - `stay_duration_nights`: Length of stay in nights
  - `is_current`: `true` if a reservation is currently active
  - `is_upcoming`: `true` if the reservation is in the future

### Property Information Sensors
- **Details**: Rating, location (lat/lon), timezone, address
- **Capacity**: Max occupancy, adults, children, pets
- **Amenities**: Bedrooms (with bed-type breakdown), bathrooms (full/half), hot tub, pet friendly, parking spaces

### Maintenance Sensor
- **Entity ID**: `sensor.vacasa_[property_name]_maintenance_open`
- **State**: Number of open maintenance tickets
- **Attributes**:
  - `status_filter`: Filter applied (e.g., `"open"`)
  - `open_ticket_ids`: List of ticket IDs
  - `tickets`: List of ticket summaries with id, status, title, and updated_at

### Owner Statements Sensor
- **Entity ID**: `sensor.vacasa_statements`
- **State**: Latest statement total amount (in USD)
- **Attributes**:
  - `statement_count`: Total number of statements
  - `latest_statement_id`: ID of the most recent statement
  - `period_start`: Statement period start date
  - `period_end`: Statement period end date
  - `status`: Statement status
  - `total_amount`: Total amount
  - `net_amount`: Net amount
  - `amount_due`: Amount due

## Stay Types

| Display Name | Raw Type | Category Value | Description |
|-------------|----------|----------------|-------------|
| Guest Booking | `guest` | `guest_booking` | Regular guest reservations |
| Owner Stay | `owner` | `owner_stay` | Property owner staying |
| Maintenance | `maintenance` | `maintenance` | Scheduled maintenance |
| Block | `block` | `block` | Property blocks/holds |
| Other | `other` | `other` | Other reservation types |

**Using in Automations**: Use binary sensor attributes `current_reservation_type` or `next_reservation_type` for display names (e.g., `"Guest Booking"`). Use `stay_category` on the next stay sensor for underscore-formatted values (e.g., `"owner_stay"`).

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
      - platform: template
        value_template: >
          {% set days = state_attr('sensor.vacasa_vacation_cabin_next_stay', 'days_until_checkin') %}
          {% set category = state_attr('sensor.vacasa_vacation_cabin_next_stay', 'stay_category') %}
          {{ days is not none and days | int <= 3 and category == 'owner_stay' }}
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

**Calendar shows no events**: Check date range (60 days past to 365 days future). Use `vacasa.refresh_data` service to force refresh.

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

# Install dependencies (creates .venv automatically)
uv sync --group dev --group test

# Install pre-commit hooks
uv run pre-commit install
```

### Running Tests

```bash
uv run pytest
```

### Code Standards

- Follow PEP 8 style guidelines
- Add type hints to functions
- Include docstrings for new code
- Use async/await for I/O operations
- Implement proper error handling
- Use appropriate logging levels

### Release Process for Maintainers

This project uses an automated release process. A single script handles version bumping, PR creation, CI gating, and merging.

#### Quick Release Steps

```bash
# 1. Add a changelog entry for the new version
#    - Update CHANGELOG.md with a ## [X.Y.Z] - YYYY-MM-DD section

# 2. Run the release script from the main branch
./new-prod-release.sh 1.9.0

# The script handles everything else automatically:
# - Bumps VERSION and manifest.json
# - Creates a temporary branch bump/version-X.Y.Z
# - Opens a PR to main with changelog notes
# - Waits for CI checks to pass
# - Squash-merges the PR and deletes the temp branch
# - Pulls latest main locally
```

After the PR merges, GitHub Actions automatically:
1. 🤖 Detects the VERSION change and reads the new version
2. 🏷️ Creates an annotated git tag (e.g., v1.9.0)
3. 📦 Triggers the release workflow
4. 🚀 Creates a GitHub release with changelog and assets
5. 📢 Notifies HACS for distribution

#### Prerequisites

- **GitHub CLI**: `brew install gh` (macOS) or `sudo apt install gh` (Linux)
- **Authentication**: Run `gh auth login` before first use
- **Main branch**: Must be on `main` with a clean working directory (uncommitted CHANGELOG.md edits are allowed)
- **Changelog Entry**: CHANGELOG.md must contain a `## [X.Y.Z]` section for the new version

#### What the Script Does

The `new-prod-release.sh <version>` script:
1. ✅ Validates prerequisites (git, gh CLI authentication, must be on `main` branch)
2. ✅ Pulls latest `main` and verifies the tag doesn't already exist
3. ✅ Checks CHANGELOG.md for a `## [X.Y.Z]` entry
4. ✅ Writes the new version to `VERSION` and `custom_components/vacasa/manifest.json`
5. ✅ Creates branch `bump/version-X.Y.Z`, commits, and pushes
6. ✅ Opens a PR to `main` with the changelog section as the PR body
7. ✅ Waits for all CI checks to pass (`--fail-fast`)
8. ✅ Squash-merges the PR and deletes the remote branch
9. ✅ Returns `main` to the latest commit locally

#### Troubleshooting

**Issue: "GitHub CLI is not authenticated"**
```bash
gh auth login
gh auth status
```

**Issue: "Must be on main branch"**
```bash
git checkout main
git pull origin main
```

**Issue: "Unexpected uncommitted changes"**
```bash
git status
git add .
git commit -m "chore: cleanup before release"
```

**Issue: "CHANGELOG.md has no entry for [X.Y.Z]"**
```bash
# Add a section to CHANGELOG.md:
# ## [X.Y.Z] - $(date +%Y-%m-%d)
# ### Changed
# - ...
```

**Issue: "Tag vX.Y.Z already exists"**
```bash
gh release list   # verify the release exists
# If you need to re-release, delete the tag first:
git push origin :refs/tags/vX.Y.Z
git tag -d vX.Y.Z
```

**Issue: "PR already exists"**
```bash
gh pr list
gh pr close <pr-number>  # Close old PR if needed
./new-prod-release.sh X.Y.Z  # Try again
```

#### Version Management Best Practices

- **Semantic Versioning**: Use MAJOR.MINOR.PATCH format
- **Changelog Format**: Follow Keep a Changelog format with date
- **Testing**: Test changes thoroughly before running the release script

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
