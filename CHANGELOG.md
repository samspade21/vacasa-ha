# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-05-20

### Added
- New GitHub workflow files:
  - hassfest.yaml for validating with Home Assistant hassfest
  - linting.yaml with matrix testing for Python 3.9, 3.10, and 3.11
  - stale.yaml for managing stale issues and PRs
- Comprehensive test strategy documentation

### Changed
- Updated development dependencies with specific versions
- Replaced test dependencies with linting and code quality tools
- Simplified GitHub workflow files
- Standardized line length to 88 characters across all configuration files
- Updated Python version to 3.9 in GitHub workflows
- Improved pre-commit configuration

### Removed
- Unused test files and configuration
- Redundant API data module
- Unnecessary pytest configuration
- Icon field from manifest.json (not allowed in current Home Assistant schema)

### Fixed
- Alignment between configuration files (pyproject.toml, setup.cfg)
- GitHub workflow inconsistencies
- Translations format for state attributes to comply with Home Assistant standards

## [1.0.1] - 2025-05-20

### Added
- Property information sensors for each Vacasa property:
  - Rating sensor (star rating)
  - Location sensor (latitude/longitude)
  - Timezone sensor
  - Max occupancy, adults, children, and pets sensors
  - Bedroom and bathroom count sensors
  - Hot tub and pet-friendly status sensors
  - Parking information sensor
  - Address sensor

### Changed
- Renamed refresh_calendars service to refresh_data to better reflect its purpose
- Now using property-specific check-in/check-out times from the API instead of global configuration
- Improved timezone handling for more accurate calendar events
- Enhanced authentication flow for better reliability

### Removed
- Check-in/check-out time configuration options (now using property-specific times from API)
- Property code sensor (redundant information)
- Unused constants and imports

### Fixed
- Import error with SENSOR_PROPERTY_TYPE constant
- Calendar event time display issues
- Authentication flow complexity

### Improved
- Simplified token handling
- Reduced technical debt
- Streamlined authentication process
- Added SSH log access documentation to memory bank

## [1.0.0] - 2025-05-19

### Added
- Initial release
- Calendar integration for Vacasa properties
- Occupancy sensors for each property
- Configurable check-in/check-out times
- Support for different reservation types (guest, owner, maintenance, block)
- Automatic data refresh
- Services for manual refresh and cache clearing
