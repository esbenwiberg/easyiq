# Aula + EasyIQ Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/esbenwiberg/easyiq.svg)](https://github.com/esbenwiberg/easyiq/releases)
[![License](https://img.shields.io/github/license/esbenwiberg/easyiq.svg)](LICENSE)

A Home Assistant custom integration for Aula + EasyIQ school management system, providing access to student schedules, homework assignments, and presence information.

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
- `sensor.easyiq_[child_name]` - Main child sensor with weekly schedule overview
- `sensor.easyiq_[child_name]_weekplan` - Detailed weekplan sensor with event data

### Binary Sensors
- `binary_sensor.easyiq_[child_name]_present` - Presence status (ON = present at school, OFF = not present)
- `binary_sensor.easyiq_messages` - Unread messages indicator (ON = has unread messages)

### Calendar Entities
- `calendar.easyiq_[child_name]_weekplan` - School schedule calendar with all events
- `calendar.easyiq_[child_name]_homework` - Homework assignments calendar with due dates

### Attributes

Each sensor provides detailed attributes:

**Main Child Sensor:**
- `child_id`: Unique child identifier
- `child_name`: Child's name
- `week`: Current week description
- `events_count`: Number of scheduled events
- `html_content`: Formatted schedule HTML
- `event_1_subject`, `event_1_time`, `event_1_activities`: First event details
- (up to 5 events with subject, time, and activities)

**Weekplan Sensor:**
- `child_id`: Unique child identifier
- `child_name`: Child's name
- `weekplan_summary`: Detailed weekplan data with events array

**Presence Binary Sensor:**
- `status`: Current status text (e.g., "HENTET/GÅET", "KOMMET/TIL STEDE")
- `status_code`: Numeric status code (0-8)
- `status_description`: English description of status
- `check_in_time`: Actual arrival time (e.g., "07:59:02")
- `check_out_time`: Actual departure time (e.g., "15:07:12")
- `entry_time`: Planned arrival time (e.g., "07:30:00")
- `exit_time`: Planned departure time (e.g., "15:00:00")
- `comment`: Additional notes (e.g., "Selvbestemmer 1400-1500")
- `exit_with`: Who picked up the child (e.g., "Mormor")
- `child_name`: Name of the child
- `last_updated`: When the data was last updated

**Message Binary Sensor:**
- `unread_count`: Number of unread messages
- `subject`: Subject of latest message
- `text`: Content of latest message
- `sender`: Sender of latest message
- `coordinator_available`: Integration status
- `last_update_success`: Last update status

## Usage Examples

### Automation: Notify when child arrives at school

```yaml
automation:
  - alias: "Child arrived at school"
    trigger:
      - platform: state
        entity_id: binary_sensor.easyiq_child_present
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.easyiq_child_present', 'status_code') == 3 }}
    action:
      - service: notify.mobile_app
        data:
          title: "School Arrival"
          message: >
            {{ state_attr('binary_sensor.easyiq_child_present', 'child_name') }}
            arrived at school at {{ state_attr('binary_sensor.easyiq_child_present', 'check_in_time') }}
```

### Automation: Notify when child is picked up

```yaml
automation:
  - alias: "Child picked up from school"
    trigger:
      - platform: state
        entity_id: binary_sensor.easyiq_child_present
        to: "off"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.easyiq_child_present', 'status_code') == 8 }}
    action:
      - service: notify.mobile_app
        data:
          title: "School Pickup"
          message: >
            {{ state_attr('binary_sensor.easyiq_child_present', 'child_name') }}
            was picked up at {{ state_attr('binary_sensor.easyiq_child_present', 'check_out_time') }}
            {% if state_attr('binary_sensor.easyiq_child_present', 'exit_with') %}
            by {{ state_attr('binary_sensor.easyiq_child_present', 'exit_with') }}
            {% endif %}
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
  - entity: binary_sensor.easyiq_child_present
    name: Status
    attribute: status
  - entity: binary_sensor.easyiq_child_present
    name: Arrived
    attribute: check_in_time
  - entity: binary_sensor.easyiq_child_present
    name: Left
    attribute: check_out_time
  - entity: binary_sensor.easyiq_child_present
    name: Comment
    attribute: comment
```

### Dashboard: Danish-style presence card

```yaml
type: markdown
content: |
  ## Fremmøde Status
  
  **{{ state_attr('binary_sensor.easyiq_child_present', 'child_name') }}:**
  - Status: {{ state_attr('binary_sensor.easyiq_child_present', 'status') }}
  - Kom: kl. {{ state_attr('binary_sensor.easyiq_child_present', 'check_in_time') }}
  - Gik: kl. {{ state_attr('binary_sensor.easyiq_child_present', 'check_out_time') }}
  - Send hjem: kl. {{ state_attr('binary_sensor.easyiq_child_present', 'exit_time') }}
  {% if state_attr('binary_sensor.easyiq_child_present', 'comment') %}
  - Bemærkninger: {{ state_attr('binary_sensor.easyiq_child_present', 'comment') }}
  {% endif %}
  {% if state_attr('binary_sensor.easyiq_child_present', 'exit_with') %}
  - Hentet af: {{ state_attr('binary_sensor.easyiq_child_present', 'exit_with') }}
  {% endif %}
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

This integration uses multiple Aula API endpoints:

### Calendar Data
- **EasyIQ CalendarGetWeekplanEvents**: Weekly schedule data (itemType 9) and homework assignments (itemType 4)
- Event details including subjects, times, and descriptions

### Presence Data
- **presence.getDailyOverview**: Real-time presence information including:
  - Current status (KOMMET/TIL STEDE, HENTET/GÅET, etc.)
  - Check-in and check-out times
  - Planned entry and exit times
  - Comments and pickup information

The integration authenticates using your Aula credentials and retrieves data through the official Aula API.

## Detailed Examples

For comprehensive usage examples covering all entities and features:
- **[Complete Usage Examples](docs/complete_usage_examples.md)** - All entities with 50+ practical examples
- **[Presence Usage Examples](docs/presence_usage_examples.md)** - Detailed presence feature guide

### Quick Reference
- **Weekplan Sensors**: Schedule data, event counts, HTML content
- **Calendar Entities**: School events, homework assignments with Home Assistant calendar integration
- **Presence Binary Sensors**: Real-time attendance with Danish status labels
- **Message Binary Sensors**: Unread message notifications with content preview

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
