# EasyIQ Integration - Complete Usage Examples

This document provides comprehensive usage examples for all entities in the EasyIQ Home Assistant integration.

## Available Entities

For each child in your account, the integration creates:

### Sensors
- `sensor.easyiq_[child_name]` - Main child sensor with weekly schedule overview
- `sensor.easyiq_[child_name]_weekplan` - Detailed weekplan sensor

### Binary Sensors
- `binary_sensor.easyiq_[child_name]_present` - Presence status (ON = present at school)
- `binary_sensor.easyiq_messages` - Unread messages indicator (ON = has unread messages)

### Calendar Entities
- `calendar.easyiq_[child_name]_weekplan` - School schedule calendar
- `calendar.easyiq_[child_name]_homework` - Homework assignments calendar

---

## 📅 Weekplan Sensor Examples

### Main Child Sensor (`sensor.easyiq_[child_name]`)

**Available Attributes:**
- `child_id`: Unique child identifier
- `child_name`: Child's name
- `week`: Current week description
- `events_count`: Number of scheduled events
- `html_content`: Formatted schedule HTML
- `event_1_subject`, `event_1_time`, `event_1_activities`: First event details
- `event_2_subject`, `event_2_time`, `event_2_activities`: Second event details
- (up to 5 events)

#### Dashboard: Today's Schedule Card
```yaml
type: markdown
content: |
  ## {{ state_attr('sensor.easyiq_avi_emilie', 'child_name') }}'s Schedule
  
  **{{ state_attr('sensor.easyiq_avi_emilie', 'week') }}**
  
  {% for i in range(1, 6) %}
    {% set subject = state_attr('sensor.easyiq_avi_emilie', 'event_' ~ i ~ '_subject') %}
    {% set time = state_attr('sensor.easyiq_avi_emilie', 'event_' ~ i ~ '_time') %}
    {% set activities = state_attr('sensor.easyiq_avi_emilie', 'event_' ~ i ~ '_activities') %}
    {% if subject and subject != 'Unknown' %}
  - **{{ time }}**: {{ subject }}
    {% if activities and activities != 'Unknown' %}
    - {{ activities }}
    {% endif %}
    {% endif %}
  {% endfor %}
  
  Total events: {{ state_attr('sensor.easyiq_avi_emilie', 'events_count') }}
```

#### Dashboard: Weekly Overview Card
```yaml
type: entities
title: Weekly Schedule Overview
entities:
  - entity: sensor.easyiq_avi_emilie
    name: Avi Emilie
    secondary_info: attribute
    attribute: week
  - entity: sensor.easyiq_max_emil
    name: Max Emil
    secondary_info: attribute
    attribute: week
```

#### Automation: Schedule Change Notification
```yaml
automation:
  - alias: "Schedule updated"
    trigger:
      - platform: state
        entity_id: sensor.easyiq_avi_emilie
        attribute: events_count
    condition:
      - condition: template
        value_template: >
          {{ trigger.from_state.attributes.events_count != trigger.to_state.attributes.events_count }}
    action:
      - service: notify.family
        data:
          title: "Schedule Updated"
          message: >
            {{ state_attr('sensor.easyiq_avi_emilie', 'child_name') }}'s schedule has been updated.
            Now has {{ state_attr('sensor.easyiq_avi_emilie', 'events_count') }} events this week.
```

### Detailed Weekplan Sensor (`sensor.easyiq_[child_name]_weekplan`)

**Available Attributes:**
- `child_id`: Unique child identifier
- `child_name`: Child's name
- `weekplan_summary`: Detailed weekplan data with events array

#### Template: Next Class Sensor
```yaml
sensor:
  - platform: template
    sensors:
      next_class:
        friendly_name: "Next Class"
        value_template: >
          {% set events = state_attr('sensor.easyiq_avi_emilie_weekplan', 'weekplan_summary').events %}
          {% if events %}
            {% set now = now().strftime('%Y-%m-%d %H:%M') %}
            {% for event in events %}
              {% if event.start > now %}
                {{ event.courses }} at {{ event.start }}
                {% break %}
              {% endif %}
            {% endfor %}
          {% else %}
            No upcoming classes
          {% endif %}
```

#### Dashboard: Detailed Schedule Table
```yaml
type: markdown
content: |
  ## Detailed Weekly Schedule
  
  {% set weekplan = state_attr('sensor.easyiq_avi_emilie_weekplan', 'weekplan_summary') %}
  {% if weekplan and weekplan.events %}
  | Time | Subject | Activities |
  |------|---------|------------|
  {% for event in weekplan.events[:10] %}
  | {{ event.start }} | {{ event.courses }} | {{ event.activities }} |
  {% endfor %}
  
  Showing {{ weekplan.events | length }} of {{ weekplan.total_events }} events
  {% else %}
  No schedule data available
  {% endif %}
```

---

## 📧 Message Binary Sensor Examples

### Message Sensor (`binary_sensor.easyiq_messages`)

**Available Attributes:**
- `unread_count`: Number of unread messages
- `subject`: Subject of latest message
- `text`: Content of latest message
- `sender`: Sender of latest message
- `coordinator_available`: Integration status
- `last_update_success`: Last update status

#### Dashboard: Message Status Card
```yaml
type: glance
title: School Messages
entities:
  - entity: binary_sensor.easyiq_messages
    name: Unread Messages
    attribute: unread_count
  - entity: binary_sensor.easyiq_messages
    name: Latest Subject
    attribute: subject
  - entity: binary_sensor.easyiq_messages
    name: From
    attribute: sender
```

#### Dashboard: Latest Message Card
```yaml
type: markdown
content: |
  ## Latest School Message
  
  {% if is_state('binary_sensor.easyiq_messages', 'on') %}
  **{{ state_attr('binary_sensor.easyiq_messages', 'unread_count') }} unread messages**
  
  **Latest Message:**
  - **From:** {{ state_attr('binary_sensor.easyiq_messages', 'sender') }}
  - **Subject:** {{ state_attr('binary_sensor.easyiq_messages', 'subject') }}
  - **Message:** {{ state_attr('binary_sensor.easyiq_messages', 'text') }}
  {% else %}
  No unread messages
  {% endif %}
```

#### Automation: New Message Notification
```yaml
automation:
  - alias: "New school message"
    trigger:
      - platform: state
        entity_id: binary_sensor.easyiq_messages
        to: "on"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "New School Message"
          message: >
            From: {{ state_attr('binary_sensor.easyiq_messages', 'sender') }}
            Subject: {{ state_attr('binary_sensor.easyiq_messages', 'subject') }}
          data:
            actions:
              - action: "read_message"
                title: "Read Message"
```

#### Automation: Daily Message Summary
```yaml
automation:
  - alias: "Daily message summary"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.easyiq_messages
        state: "on"
    action:
      - service: notify.family
        data:
          title: "Daily School Messages"
          message: >
            You have {{ state_attr('binary_sensor.easyiq_messages', 'unread_count') }} unread school messages.
            Latest: {{ state_attr('binary_sensor.easyiq_messages', 'subject') }}
```

---

## 📅 Calendar Entity Examples

### Weekplan Calendar (`calendar.easyiq_[child_name]_weekplan`)

#### Dashboard: Calendar Card
```yaml
type: calendar
entity: calendar.easyiq_avi_emilie_weekplan
title: "Avi's School Schedule"
```

#### Dashboard: Upcoming Events
```yaml
type: markdown
content: |
  ## Upcoming School Events
  
  {% set events = state_attr('calendar.easyiq_avi_emilie_weekplan', 'events') %}
  {% if events %}
  {% for event in events[:5] %}
  - **{{ event.start.strftime('%H:%M') }}**: {{ event.summary }}
    {% if event.description %}
    - {{ event.description }}
    {% endif %}
  {% endfor %}
  {% else %}
  No upcoming events
  {% endif %}
```

#### Automation: Next Class Reminder
```yaml
automation:
  - alias: "Next class reminder"
    trigger:
      - platform: calendar
        entity_id: calendar.easyiq_avi_emilie_weekplan
        event: start
        offset: "-00:15:00"  # 15 minutes before
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Class Starting Soon"
          message: >
            {{ trigger.calendar_event.summary }} starts in 15 minutes
            at {{ trigger.calendar_event.start.strftime('%H:%M') }}
```

### Homework Calendar (`calendar.easyiq_[child_name]_homework`)

#### Dashboard: Homework Overview
```yaml
type: calendar
entity: calendar.easyiq_avi_emilie_homework
title: "Homework & Assignments"
```

#### Automation: Homework Due Tomorrow
```yaml
automation:
  - alias: "Homework due tomorrow"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - service: calendar.get_events
        target:
          entity_id: calendar.easyiq_avi_emilie_homework
        data:
          start_date_time: "{{ (now() + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00') }}"
          end_date_time: "{{ (now() + timedelta(days=1)).strftime('%Y-%m-%d 23:59:59') }}"
        response_variable: homework_events
      - condition: template
        value_template: "{{ homework_events['calendar.easyiq_avi_emilie_homework']['events'] | length > 0 }}"
      - service: notify.family
        data:
          title: "Homework Due Tomorrow"
          message: >
            {% set events = homework_events['calendar.easyiq_avi_emilie_homework']['events'] %}
            {{ events | length }} homework assignments due tomorrow:
            {% for event in events %}
            - {{ event.summary }}
            {% endfor %}
```

---

## 🏠 Smart Home Integration Examples

### Morning Routine
```yaml
automation:
  - alias: "School morning routine"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
      - condition: template
        value_template: >
          {{ state_attr('sensor.easyiq_avi_emilie', 'events_count') > 0 }}
    action:
      - service: light.turn_on
        target:
          entity_id: light.kids_rooms
        data:
          brightness: 255
      - service: media_player.play_media
        target:
          entity_id: media_player.kitchen_speaker
        data:
          media_content_id: "Today's schedule"
          media_content_type: "tts"
      - service: tts.google_translate_say
        data:
          entity_id: media_player.kitchen_speaker
          message: >
            Good morning! Today {{ state_attr('sensor.easyiq_avi_emilie', 'child_name') }} 
            has {{ state_attr('sensor.easyiq_avi_emilie', 'events_count') }} classes scheduled.
            First class: {{ state_attr('sensor.easyiq_avi_emilie', 'event_1_subject') }} 
            at {{ state_attr('sensor.easyiq_avi_emilie', 'event_1_time') }}.
```

### Evening Summary
```yaml
automation:
  - alias: "Evening school summary"
    trigger:
      - platform: time
        at: "18:30:00"
    action:
      - service: notify.family
        data:
          title: "Today's School Summary"
          message: >
            **Presence Status:**
            {% for child in ['avi_emilie', 'max_emil'] %}
            - {{ state_attr('binary_sensor.easyiq_' ~ child ~ '_present', 'child_name') }}: 
              {{ state_attr('binary_sensor.easyiq_' ~ child ~ '_present', 'status') }}
              {% if state_attr('binary_sensor.easyiq_' ~ child ~ '_present', 'check_out_time') %}
              (Left at {{ state_attr('binary_sensor.easyiq_' ~ child ~ '_present', 'check_out_time') }})
              {% endif %}
            {% endfor %}
            
            **Messages:** 
            {% if is_state('binary_sensor.easyiq_messages', 'on') %}
            {{ state_attr('binary_sensor.easyiq_messages', 'unread_count') }} unread
            {% else %}
            No new messages
            {% endif %}
```

### Weekend Planning
```yaml
automation:
  - alias: "Weekend school planning"
    trigger:
      - platform: time
        at: "10:00:00"
    condition:
      - condition: time
        weekday:
          - sun
    action:
      - service: calendar.get_events
        target:
          entity_id: calendar.easyiq_avi_emilie_homework
        data:
          start_date_time: "{{ now().strftime('%Y-%m-%d 00:00:00') }}"
          end_date_time: "{{ (now() + timedelta(days=7)).strftime('%Y-%m-%d 23:59:59') }}"
        response_variable: upcoming_homework
      - service: notify.family
        data:
          title: "Week Ahead Planning"
          message: >
            **This Week's Schedule:**
            - {{ state_attr('sensor.easyiq_avi_emilie', 'child_name') }}: {{ state_attr('sensor.easyiq_avi_emilie', 'events_count') }} events
            
            **Homework Due:**
            {% set events = upcoming_homework['calendar.easyiq_avi_emilie_homework']['events'] %}
            {% if events | length > 0 %}
            {% for event in events %}
            - {{ event.summary }} (Due: {{ event.start.strftime('%A') }})
            {% endfor %}
            {% else %}
            No homework assignments this week
            {% endif %}
```

---

## 📊 Advanced Template Sensors

### School Status Summary
```yaml
sensor:
  - platform: template
    sensors:
      school_status_summary:
        friendly_name: "School Status Summary"
        value_template: >
          {% set children = ['avi_emilie', 'max_emil'] %}
          {% set present = children | select('is_state', 'binary_sensor.easyiq_' ~ item ~ '_present', 'on') | list | length %}
          {% set total = children | length %}
          {{ present }}/{{ total }} at school
        attribute_templates:
          children_status: >
            {% set children = [
              ('Avi Emilie', 'binary_sensor.easyiq_avi_emilie_present'),
              ('Max Emil', 'binary_sensor.easyiq_max_emil_present')
            ] %}
            {% set statuses = [] %}
            {% for name, entity in children %}
              {% set status = state_attr(entity, 'status') %}
              {% set statuses = statuses + [name + ': ' + status] %}
            {% endfor %}
            {{ statuses | join(', ') }}
          total_events_today: >
            {% set children = ['avi_emilie', 'max_emil'] %}
            {% set total = 0 %}
            {% for child in children %}
              {% set events = state_attr('sensor.easyiq_' ~ child, 'events_count') %}
              {% set total = total + (events if events else 0) %}
            {% endfor %}
            {{ total }}
          unread_messages: >
            {{ state_attr('binary_sensor.easyiq_messages', 'unread_count') }}
```

### Next Event Sensor
```yaml
sensor:
  - platform: template
    sensors:
      next_school_event:
        friendly_name: "Next School Event"
        value_template: >
          {% set children = ['avi_emilie', 'max_emil'] %}
          {% set next_events = [] %}
          {% for child in children %}
            {% set events = state_attr('sensor.easyiq_' ~ child ~ '_weekplan', 'weekplan_summary').events %}
            {% if events %}
              {% set now = now().strftime('%Y-%m-%d %H:%M') %}
              {% for event in events %}
                {% if event.start > now %}
                  {% set next_events = next_events + [(event.start, event.courses, state_attr('sensor.easyiq_' ~ child, 'child_name'))] %}
                  {% break %}
                {% endif %}
              {% endfor %}
            {% endif %}
          {% endfor %}
          {% if next_events %}
            {% set next_event = next_events | sort | first %}
            {{ next_event[1] }} for {{ next_event[2] }} at {{ next_event[0] }}
          {% else %}
            No upcoming events
          {% endif %}
```

---

## 🔧 Troubleshooting Examples

### Integration Health Check
```yaml
sensor:
  - platform: template
    sensors:
      easyiq_health:
        friendly_name: "EasyIQ Integration Health"
        value_template: >
          {% set entities = [
            'sensor.easyiq_avi_emilie',
            'binary_sensor.easyiq_avi_emilie_present',
            'binary_sensor.easyiq_messages',
            'calendar.easyiq_avi_emilie_weekplan'
          ] %}
          {% set working = entities | select('has_value') | list | length %}
          {% set total = entities | length %}
          {{ working }}/{{ total }} entities working
        attribute_templates:
          entity_status: >
            {% set entities = [
              'sensor.easyiq_avi_emilie',
              'binary_sensor.easyiq_avi_emilie_present',
              'binary_sensor.easyiq_messages',
              'calendar.easyiq_avi_emilie_weekplan'
            ] %}
            {% set statuses = [] %}
            {% for entity in entities %}
              {% if has_value(entity) %}
                {% set statuses = statuses + [entity + ': OK'] %}
              {% else %}
                {% set statuses = statuses + [entity + ': ERROR'] %}
              {% endif %}
            {% endfor %}
            {{ statuses | join(', ') }}
```

### Debug Information Card
```yaml
type: markdown
content: |
  ## EasyIQ Debug Information
  
  **Integration Status:**
  - Health: {{ states('sensor.easyiq_health') }}
  - Last Update: {{ state_attr('binary_sensor.easyiq_messages', 'last_update_success') }}
  - Coordinator Available: {{ state_attr('binary_sensor.easyiq_messages', 'coordinator_available') }}
  
  **Data Status:**
  - Events Count: {{ state_attr('sensor.easyiq_avi_emilie', 'events_count') }}
  - Presence Status: {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'status') }}
  - Messages: {{ state_attr('binary_sensor.easyiq_messages', 'unread_count') }}
  
  **Entity States:**
  {{ state_attr('sensor.easyiq_health', 'entity_status') }}
```

This comprehensive guide covers all entities and provides practical examples for dashboards, automations, and smart home integration.