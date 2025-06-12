# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-06-12

### Added
- **Calendar-Based Occupancy Detection**: Binary sensors now derive occupancy status directly from calendar entities instead of API calls for more real-time updates
- **Enhanced Debugging Tools**: New `logs.sh` script provides comprehensive log viewing with multiple filtering options (recent, live, debug, errors, calendar-specific)
- **Environment-Based Configuration**: New `.env` file support for secure server configuration in deployment and logging scripts
- **Automated Deployment**: Enhanced `deploy.sh` script with automatic Home Assistant restart and improved error handling
- **Comprehensive Documentation**: Added detailed debugging and troubleshooting section with step-by-step debug logging instructions

### Improved
- **Binary Sensor Reliability**: Enhanced entity discovery with retry mechanism and exponential backoff to handle timing issues during startup
- **Entity Synchronization**: Better coordination between calendar and binary sensor platforms with improved initialization timing
- **Developer Experience**: New development tools (`logs.sh`, `deploy.sh`) with SSH-based remote access and real-time monitoring
- **Error Handling**: More robust error handling with clear diagnostic messages and automatic recovery mechanisms
- **Logging Quality**: Enhanced debug logging with better context and clearer explanations of normal vs. problematic behavior

### Changed
- **Occupancy Detection Method**: Switched from API-based to calendar-entity-based occupancy detection for improved responsiveness
- **Log Message Levels**: Reduced startup timing messages from WARNING to DEBUG level to eliminate noise in default logs
- **Deployment Process**: Streamlined deployment with automatic restart and environment-based configuration
- **Documentation Structure**: Reorganized README with dedicated debugging section and enhanced development workflow instructions

### Security
- **Configuration Management**: Moved hardcoded server details to environment variables and `.env` files
- **Git Security**: Added `.env` files to `.gitignore` to prevent credential exposure
- **Best Practices**: Implemented secure configuration patterns for development and deployment scripts

### Developer Experience
- **Remote Log Access**: SSH-based log viewing with real-time monitoring capabilities
- **Automated Deployment**: One-command deployment with automatic restart and validation
- **Environment Templates**: `.env.example` template for easy setup with clear documentation
- **Enhanced Debugging**: Multiple log filtering options and search capabilities for efficient troubleshooting

## [1.0.3] - 2025-05-29

### Fixed
- **Critical Bug Fix**: Fixed occupancy sensor logic to correctly show "occupied" during the entire reservation period, including at check-out time
- **Critical Bug Fix**: Removed coordinator dependency from binary sensors to prevent "unavailable" states during data refresh
- **Property Sensors Fix**: Removed coordinator inheritance from property information sensors to prevent "unavailable" states
- **Config Flow Deprecation**: Fixed deprecated config_entry assignment warning for future Home Assistant compatibility
- **Timezone Handling**: Replaced pytz with zoneinfo to fix timezone parsing issues and eliminate blocking calls
- **Default Times**: Added proper default check-in (4 PM) and check-out (10 AM) times when specific times are not available
- **State Persistence**: All sensors now maintain their state during temporary API issues instead of becoming unavailable

### Changed
- Binary sensors now listen to coordinator updates without inheriting from CoordinatorEntity (respects user-configured refresh interval)
- Improved timezone handling with proper localization using Python's zoneinfo module
- Enhanced debug logging with better datetime comparison information
- Occupancy comparison logic now uses `<=` for check-out time to include the exact check-out moment
- All data refresh now follows the user-configured refresh interval instead of separate timers

### Improved
- Better error handling for temporary API failures
- More robust state management during network issues
- Enhanced debug logging for troubleshooting occupancy issues
- Reduced blocking operations in timezone handling

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
- Manifest.json key order to follow Home Assistant requirements (domain, name, then alphabetical)

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
