# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-08-18

### Added
- **Enhanced Startup Coordination**: Binary sensors now properly wait for calendar entities to be available before initial state updates, eliminating timing-dependent initialization issues
- **Event-Driven Recovery Mechanisms**: Automatic retry logic when calendar entities are temporarily unavailable, providing self-healing capabilities for robust operation
- **Platform Dependencies**: Explicit dependency declarations ensure proper startup order between calendar and binary sensor platforms
- **Modern Python Tooling**: Complete migration to ruff-pre-commit for faster, more efficient linting and formatting with Rust-based performance benefits

### Fixed
- **Critical Occupancy Detection Reliability**: Resolved race conditions between calendar and binary sensor initialization that could cause incorrect occupancy states during startup
- **Current Event Detection Logic**: Corrected calendar logic for accurately identifying active reservations happening right now vs future events
- **Timing Dependency Issues**: Eliminated startup timing problems through enhanced coordination between entity platforms
- **Binary Sensor State Consistency**: Fixed edge cases where occupancy sensors could show incorrect states due to calendar entity unavailability

### Improved
- **Production-Ready Logging**: Clean, maintainable debug output with reduced noise and clearer status messages suitable for long-term operation
- **Robust State Management**: Binary sensors now gracefully handle calendar entity state transitions and temporary unavailability
- **Error Recovery**: Enhanced automatic recovery mechanisms for handling temporary platform or network issues
- **Startup Reliability**: Consistent entity initialization that works reliably without manual intervention across different Home Assistant configurations
- **Development Workflow**: Consolidated all linting and formatting configuration in pyproject.toml with modern ruff tooling

### Changed
- **Linting Toolchain**: Migrated from black, flake8, and isort to unified ruff-pre-commit for faster development workflows
- **Configuration Management**: Consolidated all code quality tools configuration in pyproject.toml while maintaining mypy for type checking
- **Binary Sensor Architecture**: Enhanced entity coordination patterns for more reliable occupancy detection
- **Calendar State Logic**: Improved current event identification algorithm for accurate real-time occupancy status
- **Pre-commit Hooks**: Updated both development and CI environments to use consistent ruff-based tooling

### Technical Improvements
- **Platform Coordination**: Added explicit platform dependencies in [`binary_sensor.py`](custom_components/vacasa/binary_sensor.py) and [`calendar.py`](custom_components/vacasa/calendar.py)
- **State Recovery**: Implemented event-driven recovery patterns for handling temporary entity unavailability
- **Startup Sequencing**: Enhanced initialization order management to prevent race conditions
- **Configuration Consolidation**: Moved all linting/formatting settings from setup.cfg to pyproject.toml for modern Python project structure
- **CI/CD Consistency**: Aligned pre-commit configuration across development and continuous integration environments

### Developer Experience
- **Faster Tooling**: Ruff provides significantly faster linting and formatting compared to previous toolchain
- **Simplified Configuration**: Single configuration file (pyproject.toml) for all code quality tools except type checking
- **Enhanced Debugging**: Improved diagnostic logging for troubleshooting occupancy detection and entity coordination issues
- **Maintainable Codebase**: Cleaner logging patterns and error handling suitable for production environments

This release represents a major stability milestone, resolving all known timing and reliability issues while modernizing the development toolchain. The integration now provides consistent, reliable occupancy detection that works seamlessly across different Home Assistant installations and configurations.

## [1.2.1] - 2025-07-29

### Fixed
- **Critical Occupancy Detection Fix**: Resolved missing calendar entity state property that prevented binary sensors from detecting occupancy status correctly
- **Calendar State Integration**: Added missing `state` property to VacasaCalendar class that returns "on" when current event exists, "off" otherwise
- **Binary Sensor Accuracy**: Occupancy sensors now properly read calendar entity state and correctly show "occupied" during active reservations

### Improved
- **Enhanced Logging**: Added comprehensive debug logging for calendar state changes and event detection with detailed timestamps
- **Coordinator Integration**: Enhanced calendar entity coordinator update handlers to ensure proper state refresh during data updates
- **Debugging Visibility**: Improved diagnostic information for troubleshooting occupancy detection issues

### Technical Details
- Fixed missing `@property state` method in [`VacasaCalendar`](custom_components/vacasa/calendar.py) class
- Binary sensor logic correctly checks `calendar_state.state == "on"` but calendar entity was never setting this critical property
- Added coordinator update event handlers to ensure calendar state refreshes properly during data coordinator updates
- Enhanced event detection logging shows current vs future event identification for better debugging

## [1.2.0] - 2025-07-10

### Added
- **Modern Architecture Patterns**: Complete modernization using latest Home Assistant integration best practices from context7 MCP
- **Runtime Data Pattern**: Implemented `ConfigEntry.runtime_data` for improved data management and type safety
- **Enhanced Type Safety**: Full type hint modernization with Python 3.10+ syntax throughout codebase
- **CoordinatorEntity Pattern**: Updated all entity platforms to use modern `CoordinatorEntity[VacasaDataUpdateCoordinator]` patterns
- **Dataclass Structure**: Organized runtime data with `@dataclass VacasaData` for better code organization

### Fixed
- **Critical Bug Fix**: Resolved 500 "Internal Server Error" when clicking Configure button in Home Assistant UI
- **Config Flow Serialization**: Fixed `TypeError: issubclass() arg 1 must be a class` by implementing proper voluptuous validator patterns
- **Schema Validation**: Corrected config flow schema to work with Home Assistant's frontend serialization
- **Code Quality Issues**: Fixed all flake8 linting errors (unused imports, unused variables)

### Improved
- **Integration Architecture**: Modernized all core files with latest Home Assistant patterns
- **Entity Management**: Enhanced entity initialization and coordinator integration
- **Error Handling**: Better validation and user feedback in configuration flows
- **Code Quality**: 100% pre-commit hook compliance (black, flake8, isort, mypy)
- **Test Coverage**: All 55 tests passing with comprehensive API client coverage
- **HACS Compliance**: Achieved A+ grade (100% compliant) for HACS submission
- **Documentation**: Updated translations and removed outdated configuration field references

### Changed
- **API Client Modernization**: Updated all type hints to modern syntax (`list[dict[str, Any]]`)
- **Entity Platforms**: Migrated binary sensor, calendar, and sensor platforms to use runtime data patterns
- **Configuration Management**: Simplified config flow with manual validation for better compatibility
- **Caching Strategy**: Enhanced cached data management with modern async patterns

### Technical Improvements
- **Type Aliases**: Introduced `VacasaConfigEntry = ConfigEntry[VacasaData]` for better type safety
- **Generic Typing**: Full implementation of generic coordinator typing across all entities
- **Modern Imports**: Updated import statements to use latest Home Assistant patterns
- **Async Patterns**: Enhanced asynchronous programming practices throughout

### Developer Experience
- **Code Standards**: All code now passes strict linting and formatting requirements
- **Testing**: Comprehensive test suite with 100% success rate
- **Documentation**: Clean, modern codebase ready for future Home Assistant versions
- **Quality Gates**: Pre-commit hooks ensure continued code quality

## [1.1.3] - 2025-07-08

### Fixed
- **Critical Bug Fix**: Fixed calendar entity current event detection to properly show occupancy during active stays
- **Occupancy Detection**: Calendar now correctly identifies and reports current events (happening right now) instead of only future events
- **Binary Sensor Accuracy**: Occupancy sensors now properly show "occupied" when there's an active reservation

### Technical Details
- Enhanced `async_get_next_event()` method in calendar.py to prioritize current events over future events
- Added proper event time range checking (start <= now < end) for current event detection
- Improved debug logging for current vs. future event identification

## [1.1.2] - 2025-01-07

### Added
- **Enhanced Options Flow**: Users can now update Vacasa credentials (username/password) directly in the integration configuration without deleting and recreating the integration
- **Automatic Configuration Reload**: All configuration changes now trigger automatic integration reload for immediate effect

### Improved
- **User Experience**: Enhanced validation and error handling for credential updates with clear user guidance
- **Configuration Management**: Streamlined options flow logic ensures consistent reload behavior for all setting changes
- **Translations**: Updated user interface text with helpful descriptions for credential management

### Fixed
- **Configuration Persistence**: Resolved issue where configuration changes required manual integration reload to take effect

## [1.1.1] - 2025-06-16

### Changed
- HACS publication requirements now fully met
- Home Assistant Brands submission approved and published
- All GitHub validation actions passing
- Integration ready for official HACS publication

### Documentation
- Updated for HACS compliance and community distribution
- Integration now eligible for inclusion in HACS default repositories

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
