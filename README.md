# EasyIQ Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/esbenwiberg/easyiq.svg)]([https://github.com/esbenwiberg/easyiq/releases/tag/v0.2.0]))
[![License](https://img.shields.io/github/license/esbenwiberg/easyiq.svg)](LICENSE)

A Home Assistant custom integration for EasyIQ school management system, providing access to student schedules, homework assignments, and presence information.

## Features

- 📅 **Weekly Schedule (Weekplan)**: View your child's weekly school schedule as sensor data
- 📚 **Homework Assignments**: Track homework assignments with descriptions and due dates
- 👤 **Presence Status**: Monitor your child's attendance status
- 📊 **Calendar Integration**: School events appear in Home Assistant calendar
- 🌍 **Multi-language**: English interface with Danish school data support

## Screenshots

![EasyIQ Integration](docs/images/easyiq-overview.png)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL: `https://github.com/esbenwiberg/easyiq`
6. Select "Integration" as the category
7. Click "Add"
8. Find "EasyIQ" in the integration list and install it
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/esbenwiberg/easyiq/releases)
2. Extract the `custom_components/easyiq` folder to your Home Assistant `custom_components` directory
3. Restart Home Assistant

## Quick Start

### For End Users
1. Install via HACS (see Installation section below)
2. Add integration through Home Assistant UI
3. Enter your Aula credentials

### For Developers
Want to contribute or test locally? See **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** for complete instructions on:
- Installing Home Assistant for development
- Getting the localhost:8123 interface working
- Setting up the development environment
- Testing and debugging the integration

## Configuration

### Through the UI (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "EasyIQ"
4. Enter your Aula credentials:
   - **Username**: Your Aula username
   - **Password**: Your Aula password
5. Select which features to enable:
   - School Schedule
   - Weekly Plan (Weekplan)
   - Homework (Lektier)
   - Presence Status

### Manual Configuration (YAML)

Add to your `configuration.yaml`:

```yaml
easyiq:
  username: your_aula_username
  password: your_aula_password
  school_schedule: true
  weekplan: true
  homework: true
  presence: true
```

## Entities Created

For each child in your account, the integration creates:

### Sensors
- `sensor.easyiq_[child_name]_weekplan` - Weekly schedule information
- `sensor.easyiq_[child_name]_presence` - Current presence status

### Calendar
- `calendar.easyiq_[child_name]_schedule` - School events and schedule

### Attributes

Each sensor provides detailed attributes:

**Weekplan Sensor:**
- `week`: Current week number
- `events_count`: Number of scheduled events
- `html_content`: Formatted schedule HTML
- `event_1_subject`, `event_1_time`, etc.: Individual event details

**Presence Sensor:**
- `status_code`: Numeric status code
- `status_text`: Human-readable status
- `location`: Current location (if available)
- `arrival_time`: Check-in time
- `departure_time`: Check-out time

## Usage Examples

### Automation: Notify when child arrives at school

```yaml
automation:
  - alias: "Child arrived at school"
    trigger:
      - platform: state
        entity_id: sensor.easyiq_child_presence
        to: "KOMMET/TIL STEDE"
    action:
      - service: notify.mobile_app
        data:
          message: "{{ trigger.to_state.attributes.child_name }} has arrived at school"
```

### Lovelace Card: Display weekly schedule

```yaml
type: entities
title: This Week's Schedule
entities:
  - entity: sensor.easyiq_child_weekplan
    type: attribute
    attribute: html_content
```

### Template: Next school event

```yaml
sensor:
  - platform: template
    sensors:
      next_school_event:
        friendly_name: "Next School Event"
        value_template: >
          {% set events = state_attr('sensor.easyiq_child_weekplan', 'events') %}
          {% if events %}
            {{ events[0].courses }} at {{ events[0].start }}
          {% else %}
            No upcoming events
          {% endif %}
```

### Advanced Automation: Homework reminder

```yaml
automation:
  - alias: "Homework due tomorrow"
    trigger:
      - platform: time
        at: "19:00:00"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('sensor.easyiq_child_weekplan', 'homework_due_tomorrow') | length > 0 }}
    action:
      - service: notify.family
        data:
          message: "Homework due tomorrow: {{ state_attr('sensor.easyiq_child_weekplan', 'homework_due_tomorrow') | join(', ') }}"
```

### Automation: School pickup reminder

```yaml
automation:
  - alias: "School pickup reminder"
    trigger:
      - platform: template
        value_template: >
          {{ (as_timestamp(now()) - as_timestamp(state_attr('sensor.easyiq_child_weekplan', 'last_event_end'))) < 1800 }}
    action:
      - service: notify.mobile_app
        data:
          message: "School ends soon - pickup time!"
```

### Dashboard: Today's schedule card

```yaml
type: markdown
content: |
  ## Today's Schedule
  {% set events = state_attr('sensor.easyiq_child_weekplan', 'events') %}
  {% for event in events if event.date == now().strftime('%Y-%m-%d') %}
  - **{{ event.start }}**: {{ event.courses }}
  {% endfor %}
```

### Dashboard: Weekly overview card

```yaml
type: custom:auto-entities
card:
  type: entities
  title: This Week's Events
filter:
  include:
    - entity_id: sensor.easyiq_*_weekplan
      options:
        type: custom:multiple-entity-row
        entity: sensor.easyiq_child_weekplan
        name: "{{ state_attr(config.entity, 'child_name') }}"
        secondary_info: "{{ state_attr(config.entity, 'events_count') }} events"
```

### Dashboard: Presence tracking card

```yaml
type: glance
title: School Attendance
entities:
  - entity: sensor.easyiq_child_presence
    name: Status
  - entity: sensor.easyiq_child_presence
    name: Location
    attribute: location
  - entity: sensor.easyiq_child_presence
    name: Arrival
    attribute: arrival_time
```

### Template: Homework summary sensor

```yaml
sensor:
  - platform: template
    sensors:
      homework_summary:
        friendly_name: "Homework Summary"
        value_template: >
          {% set homework = state_attr('sensor.easyiq_child_weekplan', 'homework') %}
          {% if homework %}
            {{ homework | length }} assignments due
          {% else %}
            No homework
          {% endif %}
        attribute_templates:
          due_today: >
            {% set homework = state_attr('sensor.easyiq_child_weekplan', 'homework') %}
            {{ homework | selectattr('due_date', 'eq', now().strftime('%Y-%m-%d')) | list | length }}
          due_tomorrow: >
            {% set homework = state_attr('sensor.easyiq_child_weekplan', 'homework') %}
            {% set tomorrow = (now() + timedelta(days=1)).strftime('%Y-%m-%d') %}
            {{ homework | selectattr('due_date', 'eq', tomorrow) | list | length }}
```

## Troubleshooting

### Common Issues

**Authentication Failed**
- Verify your Aula username and password are correct
- Check if your account has access to EasyIQ features
- Ensure your institution uses EasyIQ (not all Danish schools do)

**No Data Retrieved**
- Confirm your children are enrolled in classes using EasyIQ
- Check the Home Assistant logs for detailed error messages
- Verify your institution's EasyIQ setup is active

**Integration Not Loading**
- Restart Home Assistant after installation
- Check `custom_components/easyiq` folder structure is correct
- Review Home Assistant logs for import errors

### Debug Logging

Add to your `configuration.yaml` for detailed logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.easyiq: debug
```

### Test Script

Run the included test script to verify your credentials:

```bash
cd /config/custom_components/easyiq
python scripts/test_client.py
```

## API Information

This integration uses the EasyIQ CalendarGetWeekplanEvents API endpoint, which provides:
- Weekly schedule data (itemType 9)
- Homework assignments (itemType 4)
- Event details including subjects, times, and descriptions

The integration authenticates using your Aula credentials and retrieves data through the EasyIQ portal.

## Supported Institutions

This integration works with Danish schools that use:
- Aula as their primary communication platform
- EasyIQ for schedule and homework management

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Development

### Setup Development Environment

```bash
git clone https://github.com/esbenwiberg/easyiq.git
cd easyiq-ha
pip install -r requirements-dev.txt
```

### Testing

```bash
# Test the client
python scripts/test_client.py

# Run with debug logging
python -c "import logging; logging.basicConfig(level=logging.DEBUG); exec(open('scripts/test_client.py').read())"
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not officially affiliated with EasyIQ or Aula. It's a community-developed integration that interfaces with publicly available APIs.

## Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/esbenwiberg/easyiq/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/esbenwiberg/easyiq/discussions)
- 📖 **Documentation**: [Wiki](https://github.com/esbenwiberg/easyiq/wiki)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
