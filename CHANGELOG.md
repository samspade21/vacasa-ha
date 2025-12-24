# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.3] - 2025-12-24

### Fixed
- Fixed thread safety violations in sensor signal handlers (#91)
- Eliminated RuntimeError when sensors update from coordinator threads
- Replaced direct `async_write_ha_state()` calls with `call_soon_threadsafe()`
- Ensured occupancy and next stay sensors update correctly at check-in time
- Prevented sensor update failures occurring every 2 hours during reservation updates

## [1.7.2] - 2025-12-24

### Fixed
- Fixed options flow initialization to prevent 500 errors when opening Vacasa settings

## [1.7.1] - 2024-12-22

### Fixed
- Calendar boundary refresh now enables real-time sensor updates at exact checkin/checkout times
- Removed blocking coordinator refresh that caused sensors to update hours late

### Security
- Added URL sanitization to prevent token exposure in debug logs
- Added HTML escaping for user-provided display content (XSS protection)
- Improved exception handling with specific exception types
- Added comprehensive JWT parsing documentation

### Changed
- Exception handling now uses specific types instead of broad catches

## [1.7.0] - 2025-12-01

### Fixed
- **CRITICAL**: Fixed premature occupancy state changes during active guest stays (#71)
  - Checkout times now default to 10:00 AM instead of midnight
  - Check-in times now default to 4:00 PM instead of midnight
  - Prevents system from incorrectly showing vacancy 10+ hours before actual checkout
- Fixed occupancy sensor setup and tests (#74)
- Fixed automation examples using non-existent `trigger.calendar_event.category` field (#81)

### Added
- Event-driven updates for reservation sensors (#70)
- Coordinator-based caching for Vacasa units (#72)
- Comprehensive entity attributes documentation in README (#81)
- Stay types reference table with all available categories (#81)

### Changed
- Refactored next stay sensor to use shared reservation state (#79)
- Improved automation examples with three working alternatives (#81)

### Dependencies
- Bumped pre-commit from 4.4.0 to 4.5.0 (#78)
- Bumped mypy from 1.18.2 to 1.19.0 (#80)
- Bumped actions/github-script from 7 to 8 (#77)
- Bumped actions/checkout from 5 to 6 (#76)
- Bumped actions/upload-artifact from 4 to 5 (#75)

## [1.6.0] - 2025-11-14

### Added
- **Upcoming Stay Coverage**: Enhanced [`sensor.py`](custom_components/vacasa/sensor.py) to include coverage for upcoming Vacasa stays with improved visibility into future reservations (PR #65)
- **Test Coverage Expansion**: Added comprehensive tests for cached data utilities in [`test_cached_data.py`](tests/test_cached_data.py) to improve code reliability and maintainability (PR #58)

### Fixed
- **Home Status Sensor Removal**: Removed Home Status sensor due to inaccessible API endpoints that prevented reliable data retrieval (PR #67)
- **Payload Parsing**: Fixed home status sensor payload parsing issues that caused data processing errors (PR #64)
- **Next Stay Calculations**: Corrected next stay sensor day calculation logic and added time information for more accurate stay tracking in [`sensor.py`](custom_components/vacasa/sensor.py) (PR #63)
- **CI Forked PR Checkout**: Resolved GitHub Actions checkout issues for forked pull requests to enable proper CI testing (PR #59)
- **Test Failures**: Fixed GitHub Actions test execution failures to restore CI/CD pipeline reliability (PR #54)

### Changed
- **API Modernization**: Refactored home info aggregation to support new inspection APIs in [`api_client.py`](custom_components/vacasa/api_client.py) (PR #66)
- **Code Cleanup**: Removed unused legacy constants from [`const.py`](custom_components/vacasa/const.py) to reduce technical debt (PR #62)
- **Test Infrastructure**: Restored sensor imports and extended Home Assistant stubs for improved test compatibility (PR #61)
- **Workflow Protection**: Prevented workflow autofixes from modifying CI workflow files to maintain deployment integrity (PR #56)
- **Error Messaging**: Adjusted Vacasa API fallback error message for clearer user communication (PR #55)

### Technical Improvements
- **Dependency Updates**: Updated multiple GitHub Actions and Python dependencies for improved security and compatibility:
  - actions/checkout: 4 → 5 (PR #46)
  - actions/setup-python: 5 → 6 (PR #47)
  - github/codeql-action: 3 → 4 (PR #48)
  - codecov/codecov-action: 3 → 5 (PR #50)
  - actions/stale: 7 → 10 (PR #52)
  - colorlog: 6.8.2 → 6.10.1 (PR #51)
  - mypy: 1.3.0 → 1.18.2 (PR #53)
  - pre-commit: 3.0.0 → 4.4.0 (PR #49)

This release focuses on API modernization, improved test coverage, and critical bug fixes while maintaining compatibility with the latest Home Assistant platform updates.

## [1.5.0] - 2025-11-12

### Added
- **Next Stay Sensor**: New [`VacasaNextStaySensor`](custom_components/vacasa/sensor.py) for tracking upcoming and current reservations
  - Displays next upcoming or current reservation with human-readable state messages
  - Comprehensive attributes: check-in/check-out dates, stay type, guest information
  - Computed values: days until check-in/check-out, stay duration nights
  - Supports guest, owner, maintenance, and block stay classifications
  - PR #32, #33, #34
- **API Throttling**: Implemented sensor update throttling to respect coordinator refresh interval
  - Prevents excessive API calls for multiple sensors
  - All API-backed sensors now coordinate updates efficiently

### Fixed
- **Critical Entity Registration Fix**: Added entity_id validation before state writes to prevent AttributeError during initialization (PR #38)
- **JSON Parsing Enhancement**: Handle charset in API content-type headers (`application/json; charset=utf-8`) with fallback parsing and diagnostic logging
- **Missing Import Fix**: Added missing `random` import in [`cached_data.py`](custom_components/vacasa/cached_data.py) required for retry jitter calculations
- **Occupancy Sensor Alignment**: Fixed occupancy sensor to stay properly aligned with reservation data (PR #37)
- **Token Handling**: Resolved token access issues and cleaned up cache imports (PR #35)

### Security
- **CodeQL Alert #5 Fix**: Resolved false positive "Statement has no effect" alert by explicitly assigning await result to unused variable, maintaining proper async behavior while satisfying static analysis

### Improved
- **API Resilience**: Enhanced API client with better error handling, retry logic, and rich sensor support (PR #25)
- **Blocking I/O Performance**: Refactored blocking I/O helpers for improved performance (PR #28)
- **Sensor Setup Efficiency**: Streamlined sensor platform setup, reducing code by 99 lines (PR #27)
- **Configuration Simplification**: Removed unused stay_type_mapping and API version configuration options

### Changed
- **Dependency Updates**: Updated project dependencies to latest versions (PR #26, #30)
- **Code Quality**: Fixed linting errors for improved CI/CD compliance
- **Coordinator Integration**: Statement sensor now uses coordinator updates for better consistency
- **Diagnostic Logging**: Enhanced logging for VacasaNextStaySensor troubleshooting

### Technical Improvements
- All sensors now properly coordinate with data update coordinator
- Enhanced error recovery and diagnostic capabilities
- Improved code maintainability and reduced technical debt
- Better separation of concerns in sensor architecture

This release introduces the highly-requested next stay sensor feature while delivering critical bug fixes for production stability and enhanced API resilience.

## [1.4.2] - 2025-08-19

### Testing
- **Release Pipeline Validation**: End-to-end testing of the completely rebuilt release automation system
- **Consolidated Workflow Verification**: Validating that the single `auto-release.yml` workflow performs all release functions correctly
- **VERSION Detection Testing**: Confirming the fixed multi-commit VERSION detection logic works properly
- **Release Creation Testing**: Verifying automated tag creation, HACS validation, and GitHub release generation
- **Changelog Extraction Testing**: Ensuring the fixed Python f-string bug in changelog processing is resolved

### Validation Objectives
- **Complete Pipeline Testing**: From VERSION detection through GitHub release creation
- **Error Resolution Confirmation**: Verifying all previous GITHUB_TOKEN and changelog extraction issues are resolved
- **Release Format Standards**: Ensuring continued compatibility with v1.3.2 release format expectations
- **Automation Reliability**: Confirming the streamlined single-workflow approach provides consistent results

This release specifically tests the comprehensive release automation fixes implemented in v1.4.1 to validate the complete tag → release pipeline is now fully operational and reliable.

## [1.4.1] - 2025-08-19

### Fixed
- **Critical Release Pipeline Fix**: Fixed broken release workflow that prevented automatic GitHub releases from being created after tag creation
- **Changelog Extraction Bug**: Corrected Python f-string formatting error in auto-tag workflow that caused "name 'VERSION' is not defined" error
- **Workflow Triggering Issue**: Resolved GITHUB_TOKEN limitation that prevented workflow-to-workflow triggering by consolidating auto-tag and release workflows

### Changed
- **Streamlined Release Process**: Consolidated separate auto-tag and release workflows into single `auto-release.yml` workflow to eliminate cross-workflow triggering issues
- **Enhanced Error Handling**: Improved changelog extraction with proper Python variable substitution and fallback error handling
- **Optimized Workflow Structure**: Reduced from 2 separate workflows to 1 consolidated workflow for more reliable release automation

### Technical Improvements
- **Single Workflow Architecture**: Auto-tag and release creation now happen in one atomic workflow execution, preventing GitHub security limitations
- **Proper Variable Handling**: Fixed Python f-string usage in changelog extraction to prevent runtime errors
- **Comprehensive Release Creation**: Automated tag creation, HACS validation, release archive generation, and GitHub release publication in one seamless process
- **Maintained Release Quality**: Preserved v1.3.2 release format standards with proper changelog extraction and professional presentation

### Developer Experience
- **Reliable Automation**: Release pipeline now works consistently without manual intervention
- **Clear Error Reporting**: Enhanced workflow summaries provide detailed feedback on release creation process
- **Simplified Maintenance**: Single workflow file reduces complexity and potential points of failure

## [1.4.0] - 2025-08-18

### Added
- **Enhanced Test Coverage Support**: Added pytest coverage plugin to test requirements to align with standard Home Assistant testing workflows and provide comprehensive test coverage reporting
- **Home Assistant Interface Stubs**: Implemented stub interfaces for Home Assistant's calendar and coordinator components, enabling custom integration tests to import required entities without dependency errors

### Improved
- **Test Reliability**: Updated calendar tests with explicit timezone handling and precise reservation timing to eliminate naive/aware datetime conflicts and ensure consistent test results
- **Testing Configuration**: Simplified pytest configuration by removing strict coverage gating while retaining essential testing markers and flags for improved developer experience

### Technical Improvements
- **Development Workflow**: Enhanced testing infrastructure supports both local development and CI/CD pipelines with proper Home Assistant compatibility
- **Test Isolation**: Stubbed interfaces provide clean separation between integration code and Home Assistant core dependencies during testing
- **Configuration Optimization**: Streamlined pytest setup reduces complexity while maintaining comprehensive test execution capabilities

This release focuses on improving the development and testing experience, making the integration more maintainable and compatible with standard Home Assistant development practices.

## [1.3.2] - 2025-08-18

### Security
- **Fixed URL Sanitization Vulnerability**: Enhanced hostname validation in [`api_client.py`](custom_components/vacasa/api_client.py:665) to prevent URL manipulation attacks by using proper hostname parsing instead of substring matching
- **Fixed Exception Handling**: Corrected potential TypeError in [`cached_data.py`](custom_components/vacasa/cached_data.py:329) where None could be raised instead of a proper exception

### Technical Improvements
- **CodeQL Compliance**: Addressed all security findings from GitHub CodeQL code scanning
- **Defensive Programming**: Added null checks and proper exception handling to prevent runtime errors
- **Security Best Practices**: Implemented proper hostname validation to prevent bypass attacks using malicious URLs

This release addresses GitHub security findings identified by CodeQL code scanning while maintaining full backward compatibility and functionality.

## [1.3.1] - 2025-08-18

### Added
- **Streamlined Automated Release System**: Complete deployment automation with clean separation of responsibilities
- **One-Command Deployment**: Simple `./new-prod-release.sh` script creates release PR, GitHub Actions handle the rest automatically
- **Auto-Tagging Workflow**: Automatic git tag creation when release PRs merge to main branch
- **Comprehensive Deployment Documentation**: Detailed guides with troubleshooting and workflow architecture

### Improved
- **Developer Experience**: Reduced 15+ manual deployment steps to single command execution
- **Deployment Safety**: Clear separation between script (PR creation) and GitHub Actions (automation)
- **Documentation Quality**: Complete deployment guide with workflow diagrams and best practices
- **Release Reliability**: Eliminated duplicate validation logic and potential conflicts between components

### Changed
- **Release Workflow**: Simplified from 253 to 99 lines by removing redundant validation and update jobs
- **File Organization**: Renamed original `new-prod-release.sh` to `deploy-to-homeassistant.sh` for clarity
- **Workflow Architecture**: Clean handoff points between manual and automated steps

### Technical Improvements
- **Zero Overlap Design**: Each component has single, distinct responsibility
- **Enhanced Error Handling**: Clear error messages and actionable guidance at each step
- **Performance Optimization**: Faster deployment with reduced complexity and redundancy
- **Maintenance Reduction**: 60% reduction in workflow complexity for easier long-term maintenance

This release introduces enterprise-grade deployment automation while maintaining the reliability and quality improvements from v1.3.0.

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
- **Automated Deployment**: Enhanced `new-prod-release.sh` script with automatic Home Assistant restart and improved error handling
- **Comprehensive Documentation**: Added detailed debugging and troubleshooting section with step-by-step debug logging instructions

### Improved
- **Binary Sensor Reliability**: Enhanced entity discovery with retry mechanism and exponential backoff to handle timing issues during startup
- **Entity Synchronization**: Better coordination between calendar and binary sensor platforms with improved initialization timing
- **Developer Experience**: New development tools (`logs.sh`, `new-prod-release.sh`) with SSH-based remote access and real-time monitoring
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

## [1.0.0] - 2025-05-19

### Added
- Initial release
- Calendar integration for Vacasa properties
- Occupancy sensors for each property
- Configurable check-in/check-out times
- Support for different reservation types (guest, owner, maintenance, block)
- Automatic data refresh
- Services for manual refresh and cache clearing
