# Vacasa Properties Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/releases)
[![License](https://img.shields.io/github/license/samspade21/vacasa-ha.svg?style=flat-square)](LICENSE)

A comprehensive Home Assistant integration for Vacasa vacation rental properties that provides calendars, occupancy sensors, and detailed property information, enabling powerful smart home automation based on reservation status and property characteristics.

**Version: 1.0.1**

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

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
