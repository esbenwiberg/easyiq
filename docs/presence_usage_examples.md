# EasyIQ Presence Feature - Usage Examples

The EasyIQ integration provides comprehensive presence tracking for your children at school using the Aula presence API. Here are practical examples of how to use this feature.

## Available Presence Data

For each child, the integration creates a binary sensor: `binary_sensor.easyiq_[child_name]_present`

### Binary Sensor States
- **ON**: Child is present at school (status codes 3, 4, 5)
- **OFF**: Child is not present at school (status codes 0, 1, 2, 8)

### Available Attributes
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

### Status Codes
- `0`: IKKE KOMMET (Not arrived)
- `1`: SYG (Sick)
- `2`: FERIE/FRI (Holiday/Free)
- `3`: KOMMET/TIL STEDE (Arrived/Present)
- `4`: PÅ TUR (On trip)
- `5`: SOVER (Sleeping)
- `8`: HENTET/GÅET (Picked up/Gone)

## Dashboard Examples

### Simple Presence Card
```yaml
type: entities
title: School Presence
entities:
  - entity: binary_sensor.easyiq_avi_emilie_present
    name: Avi Emilie
    secondary_info: last-updated
  - entity: binary_sensor.easyiq_max_emil_present
    name: Max Emil
    secondary_info: last-updated
```

### Detailed Presence Information
```yaml
type: glance
title: Today's School Status
entities:
  - entity: binary_sensor.easyiq_avi_emilie_present
    name: Avi Status
    attribute: status
  - entity: binary_sensor.easyiq_avi_emilie_present
    name: Arrived
    attribute: check_in_time
  - entity: binary_sensor.easyiq_avi_emilie_present
    name: Left
    attribute: check_out_time
  - entity: binary_sensor.easyiq_avi_emilie_present
    name: Comment
    attribute: comment
```

### Presence Timeline Card
```yaml
type: markdown
content: |
  ## Today's School Timeline
  
  **Avi Emilie:**
  - Status: {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'status') }}
  - Kom: kl. {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'check_in_time') }}
  - Gik: kl. {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'check_out_time') }}
  - Send hjem: kl. {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'exit_time') }}
  {% if state_attr('binary_sensor.easyiq_avi_emilie_present', 'comment') %}
  - Bemærkninger: {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'comment') }}
  {% endif %}
  {% if state_attr('binary_sensor.easyiq_avi_emilie_present', 'exit_with') %}
  - Hentet af: {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'exit_with') }}
  {% endif %}
```

## Automation Examples

### Arrival Notification
```yaml
automation:
  - alias: "Child arrived at school"
    trigger:
      - platform: state
        entity_id: binary_sensor.easyiq_avi_emilie_present
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'status_code') == 3 }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "School Arrival"
          message: >
            {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'child_name') }} 
            arrived at school at {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'check_in_time') }}
```

### Pickup Notification
```yaml
automation:
  - alias: "Child picked up from school"
    trigger:
      - platform: state
        entity_id: binary_sensor.easyiq_avi_emilie_present
        to: "off"
    condition:
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'status_code') == 8 }}
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "School Pickup"
          message: >
            {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'child_name') }} 
            was picked up at {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'check_out_time') }}
            {% if state_attr('binary_sensor.easyiq_avi_emilie_present', 'exit_with') %}
            by {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'exit_with') }}
            {% endif %}
```

### Late Arrival Alert
```yaml
automation:
  - alias: "Late arrival alert"
    trigger:
      - platform: time
        at: "08:30:00"  # 30 minutes after school starts
    condition:
      - condition: state
        entity_id: binary_sensor.easyiq_avi_emilie_present
        state: "off"
      - condition: template
        value_template: >
          {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'status_code') == 0 }}
    action:
      - service: notify.family
        data:
          title: "Late for School"
          message: >
            {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'child_name') }} 
            hasn't arrived at school yet (status: {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'status') }})
```

### Sick Day Notification
```yaml
automation:
  - alias: "Child is sick"
    trigger:
      - platform: state
        entity_id: binary_sensor.easyiq_avi_emilie_present
        attribute: status_code
        to: 1
    action:
      - service: notify.family
        data:
          title: "Sick Day"
          message: >
            {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'child_name') }} 
            is marked as sick today
```

## Template Sensors

### Presence Summary Sensor
```yaml
sensor:
  - platform: template
    sensors:
      school_presence_summary:
        friendly_name: "School Presence Summary"
        value_template: >
          {% set children = [
            'binary_sensor.easyiq_avi_emilie_present',
            'binary_sensor.easyiq_max_emil_present'
          ] %}
          {% set present = children | select('is_state', 'on') | list | length %}
          {% set total = children | length %}
          {{ present }}/{{ total }} children at school
        attribute_templates:
          details: >
            {% set children = [
              ('Avi Emilie', 'binary_sensor.easyiq_avi_emilie_present'),
              ('Max Emil', 'binary_sensor.easyiq_max_emil_present')
            ] %}
            {% set details = [] %}
            {% for name, entity in children %}
              {% set status = state_attr(entity, 'status') %}
              {% set details = details + [name + ': ' + status] %}
            {% endfor %}
            {{ details | join(', ') }}
```

### Next Pickup Time Sensor
```yaml
sensor:
  - platform: template
    sensors:
      next_pickup_time:
        friendly_name: "Next Pickup Time"
        value_template: >
          {% set children = [
            'binary_sensor.easyiq_avi_emilie_present',
            'binary_sensor.easyiq_max_emil_present'
          ] %}
          {% set pickup_times = [] %}
          {% for entity in children %}
            {% if is_state(entity, 'on') %}
              {% set exit_time = state_attr(entity, 'exit_time') %}
              {% if exit_time %}
                {% set pickup_times = pickup_times + [exit_time] %}
              {% endif %}
            {% endif %}
          {% endfor %}
          {% if pickup_times %}
            {{ pickup_times | min }}
          {% else %}
            No pickups needed
          {% endif %}
```

## Advanced Automations

### Smart Home Integration
```yaml
automation:
  - alias: "Adjust home when children leave school"
    trigger:
      - platform: state
        entity_id: 
          - binary_sensor.easyiq_avi_emilie_present
          - binary_sensor.easyiq_max_emil_present
        to: "off"
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.attributes.status_code == 8 }}  # Picked up
      - condition: time
        after: "14:00:00"  # Only in afternoon
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.home
        data:
          temperature: 21  # Warm up house for arrival
      - service: light.turn_on
        target:
          entity_id: light.entrance
        data:
          brightness: 255

  - alias: "Turn off lights when children arrive at school"
    trigger:
      - platform: state
        entity_id: 
          - binary_sensor.easyiq_avi_emilie_present
          - binary_sensor.easyiq_max_emil_present
        to: "on"
    condition:
      - condition: template
        value_template: >
          {{ trigger.to_state.attributes.status_code == 3 }}  # Arrived
      - condition: time
        before: "09:00:00"  # Only in morning
    action:
      - service: light.turn_off
        target:
          entity_id: light.kids_rooms
```

### Weekly Attendance Report
```yaml
automation:
  - alias: "Weekly attendance report"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: time
        weekday:
          - fri  # Friday evening
    action:
      - service: notify.family
        data:
          title: "Weekly School Attendance"
          message: >
            This week's attendance summary:
            {% for entity in [
              'binary_sensor.easyiq_avi_emilie_present',
              'binary_sensor.easyiq_max_emil_present'
            ] %}
            - {{ state_attr(entity, 'child_name') }}: {{ state_attr(entity, 'status') }}
            {% endfor %}
```

## Troubleshooting

### Check Presence Data
```yaml
# Add this to configuration.yaml for debugging
logger:
  logs:
    custom_components.aula_easyiq.binary_sensor: debug
```

### Test Presence API
Use the included test script:
```bash
cd /config/custom_components/aula_easyiq
python scripts/test_presence_real.py
```

### Common Issues
- **No presence data**: Verify your institution uses Aula presence tracking
- **Old data**: Check if presence updates are enabled in your Aula account
- **Wrong status**: Ensure your children are properly enrolled in the system