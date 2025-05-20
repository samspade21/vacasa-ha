# Vacasa Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/samspade21/vacasa-ha.svg?style=flat-square)](https://github.com/samspade21/vacasa-ha/releases)
[![License](https://img.shields.io/github/license/samspade21/vacasa-ha.svg?style=flat-square)](LICENSE)

A Home Assistant integration that creates calendars and occupancy sensors for Vacasa vacation rental properties, enabling smart home automation based on reservation status.

**Version: 1.0.0**

## Features

- Creates one Home Assistant calendar per Vacasa property
- Provides binary sensors for property occupancy status
- Categorizes reservations by stay type (guest bookings, owner stays, maintenance)
- Supports configurable check-in/check-out times
- Enables standard Home Assistant calendar-based automations
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
5. (Optional) Configure default check-in time (default: 16:00:00 / 4 PM).
6. (Optional) Configure default check-out time (default: 10:00:00 / 10 AM).
7. Click "Submit" to complete the setup.

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

## Calendar Categories

The integration categorizes reservations into the following types:

- **Guest Booking**: Reservations made by guests
- **Owner Stay**: Reservations made by the property owner
- **Maintenance**: Maintenance visits
- **Block**: Other types of blocks (e.g., seasonal holds)
- **Other**: Any other type of reservation

These categories can be used in automations to trigger different actions based on the type of reservation.

## Check-in/Check-out Times

The integration supports configurable check-in and check-out times:

- Default check-in time: 4:00 PM (16:00:00)
- Default check-out time: 10:00 AM (10:00:00)

These times are used when:
1. The API doesn't provide specific times for a reservation
2. The API provides placeholder times (like midnight or noon)

You can customize these defaults during setup or in the integration options.

## Services

The integration provides the following services:

- `vacasa.refresh_calendars`: Force refresh of calendar data
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

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with or endorsed by Vacasa. The Vacasa API is not officially documented and may change without notice.
