# Vacasa Calendar Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub Release](https://img.shields.io/github/release/yourusername/vacasa-ha.svg)](https://github.com/yourusername/vacasa-ha/releases)
[![GitHub License](https://img.shields.io/github/license/yourusername/vacasa-ha.svg)](https://github.com/yourusername/vacasa-ha/blob/main/LICENSE)

A Home Assistant integration that creates calendars for Vacasa vacation rental properties, enabling smart home automation based on reservation status.

## Features

- Creates one Home Assistant calendar per Vacasa property
- Categorizes reservations by stay type (guest bookings, owner stays, maintenance)
- Enables standard Home Assistant calendar-based automations
- Securely stores and manages authentication credentials
- Automatically refreshes calendar data periodically

## Installation

### HACS Installation (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL `https://github.com/yourusername/vacasa-ha`
   - Select "Integration" as the category
   - Click "Add"
3. Search for "Vacasa" in HACS and install it
4. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/yourusername/vacasa-ha/releases).
2. Unzip the release and copy the `custom_components/vacasa` directory to your Home Assistant's `custom_components` directory.
3. Restart Home Assistant.

## Configuration

The integration can be configured through the Home Assistant UI:

1. Go to **Configuration** > **Integrations** > **Add Integration**.
2. Search for "Vacasa" and select it.
3. Enter your Vacasa username (email) and password.
4. Set the refresh interval (default: 8 hours).
5. Click "Submit" to complete the setup.

The integration will automatically discover all your Vacasa properties and create a calendar entity for each one.

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
      - platform: calendar
        event: end
        entity_id: calendar.vacasa_vacation_cabin
    condition:
      - condition: template
        value_template: "{{ trigger.calendar_event.category == 'guest_booking' }}"
      - condition: template
        value_template: >
          {% set next_event = state_attr('calendar.vacasa_vacation_cabin', 'next_event') %}
          {{ next_event is none or (as_timestamp(next_event.start) - as_timestamp(now())) > 86400 }}
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: 60
```

### Special Setup for Owner Stays

```yaml
automation:
  - alias: "Special Setup for Owner Stays"
    trigger:
      - platform: calendar
        event: start
        entity_id: calendar.vacasa_vacation_cabin
    condition:
      - condition: template
        value_template: "{{ trigger.calendar_event.category == 'owner_stay' }}"
    action:
      - service: scene.turn_on
        target:
          entity_id: scene.owner_welcome
```

## Troubleshooting

### Authentication Issues

If you encounter authentication issues:

1. Go to **Configuration** > **Integrations** > **Vacasa**
2. Click "Configure" and verify your credentials
3. Use the `vacasa.clear_cache` service to clear any cached tokens

### Calendar Not Updating

If your calendar isn't updating:

1. Use the `vacasa.refresh_calendars` service to force a refresh
2. Check the Home Assistant logs for any error messages
3. Verify that your Vacasa account has access to the properties

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with or endorsed by Vacasa. The Vacasa API is not officially documented and may change without notice.
