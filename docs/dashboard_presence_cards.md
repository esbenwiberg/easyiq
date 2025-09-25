# EasyIQ Presence Dashboard Cards

This document provides various dashboard card examples for displaying presence information with colored icons and English text, similar to the Danish format shown in the original screenshot.

## Card Examples

### Option 1: Markdown Card with Colored Icons (Recommended)

This card closely matches your screenshot format with colored status indicators:

```yaml
type: markdown
content: |
  {% set entity = 'binary_sensor.easyiq_avi_emilie_present' %}
  {% set status = state_attr(entity, 'status') %}
  {% set status_code = state_attr(entity, 'status_code') %}
  {% set child_name = state_attr(entity, 'child_name') %}
  
  {% if status_code == 8 %}
    {% set icon = '🏠' %}
    {% set color = '#4CAF50' %}
    {% set english_status = 'Picked up / Gone' %}
  {% elif status_code == 3 %}
    {% set icon = '🏫' %}
    {% set color = '#2196F3' %}
    {% set english_status = 'Present at school' %}
  {% elif status_code == 0 %}
    {% set icon = '❌' %}
    {% set color = '#FF9800' %}
    {% set english_status = 'Not arrived' %}
  {% elif status_code == 1 %}
    {% set icon = '🤒' %}
    {% set color = '#F44336' %}
    {% set english_status = 'Sick' %}
  {% elif status_code == 2 %}
    {% set icon = '🏖️' %}
    {% set color = '#9C27B0' %}
    {% set english_status = 'Holiday / Free' %}
  {% elif status_code == 4 %}
    {% set icon = '🚌' %}
    {% set color = '#FF5722' %}
    {% set english_status = 'On trip' %}
  {% elif status_code == 5 %}
    {% set icon = '😴' %}
    {% set color = '#607D8B' %}
    {% set english_status = 'Sleeping' %}
  {% else %}
    {% set icon = '❓' %}
    {% set color = '#757575' %}
    {% set english_status = 'Unknown' %}
  {% endif %}
  
  <div style="padding: 20px; border-radius: 12px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-left: 4px solid {{ color }}; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    <h3 style="margin: 0 0 16px 0; color: {{ color }}; display: flex; align-items: center; font-size: 20px;">
      <span style="font-size: 24px; margin-right: 8px;">{{ icon }}</span>
      {{ child_name }}
    </h3>
    
    <div style="font-size: 16px; line-height: 1.8; color: #495057;">
      <div style="margin-bottom: 8px;">
        <strong style="color: {{ color }}; font-size: 18px;">Status:</strong> 
        <span style="color: {{ color }}; font-weight: 600;">{{ english_status }}</span>
      </div>
      
      <div style="margin-bottom: 6px;">
        <strong style="color: #6c757d;">Arrived:</strong> 
        <span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px;">
          {{ state_attr(entity, 'check_in_time') or 'Not yet' }}
        </span>
      </div>
      
      <div style="margin-bottom: 6px;">
        <strong style="color: #6c757d;">Left:</strong> 
        <span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px;">
          {{ state_attr(entity, 'check_out_time') or 'Still there' }}
        </span>
      </div>
      
      <div style="margin-bottom: 12px;">
        <strong style="color: #6c757d;">Planned pickup:</strong> 
        <span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px;">
          {{ state_attr(entity, 'exit_time') or 'Not set' }}
        </span>
      </div>
      
      {% if state_attr(entity, 'comment') %}
      <div style="margin-top: 12px; padding: 12px; background: #fff3cd; border-radius: 6px; border-left: 3px solid #ffc107;">
        <strong style="color: #856404;">Notes:</strong><br>
        <em style="color: #856404;">{{ state_attr(entity, 'comment') }}</em>
      </div>
      {% endif %}
      
      {% if state_attr(entity, 'exit_with') %}
      <div style="margin-top: 8px;">
        <strong style="color: #6c757d;">Picked up by:</strong> 
        <span style="color: {{ color }}; font-weight: 600;">{{ state_attr(entity, 'exit_with') }}</span>
      </div>
      {% endif %}
    </div>
  </div>
```

### Option 2: Compact Markdown Card

A more compact version for smaller spaces:

```yaml
type: markdown
content: |
  {% set entity = 'binary_sensor.easyiq_avi_emilie_present' %}
  {% set status_code = state_attr(entity, 'status_code') %}
  
  {% if status_code == 8 %}
    {% set icon = '🏠' %}
    {% set color = '#4CAF50' %}
    {% set status_text = 'Gone' %}
  {% elif status_code == 3 %}
    {% set icon = '🏫' %}
    {% set color = '#2196F3' %}
    {% set status_text = 'At School' %}
  {% elif status_code == 0 %}
    {% set icon = '❌' %}
    {% set color = '#FF9800' %}
    {% set status_text = 'Not Arrived' %}
  {% elif status_code == 1 %}
    {% set icon = '🤒' %}
    {% set color = '#F44336' %}
    {% set status_text = 'Sick' %}
  {% else %}
    {% set icon = '❓' %}
    {% set color = '#757575' %}
    {% set status_text = 'Unknown' %}
  {% endif %}
  
  <div style="padding: 16px; border-radius: 8px; background: #f8f9fa; border-left: 4px solid {{ color }};">
    <div style="font-size: 18px; font-weight: bold; color: {{ color }}; margin-bottom: 12px;">
      {{ icon }} Status: {{ status_text }}
    </div>
    <div style="font-size: 14px; line-height: 1.6; color: #495057;">
      <strong>Arrived:</strong> {{ state_attr(entity, 'check_in_time') or 'Not yet' }}<br>
      <strong>Left:</strong> {{ state_attr(entity, 'check_out_time') or 'Still there' }}<br>
      <strong>Pickup:</strong> {{ state_attr(entity, 'exit_time') or 'Not set' }}
    </div>
  </div>
```

### Option 3: Custom Button Card (requires custom:button-card)

For users with the custom button card component:

```yaml
type: custom:button-card
entity: binary_sensor.easyiq_avi_emilie_present
name: |
  [[[
    return entity.attributes.child_name;
  ]]]
show_state: false
show_icon: false
styles:
  card:
    - padding: 20px
    - border-radius: 12px
    - background: |
        [[[
          const status_code = entity.attributes.status_code;
          if (status_code === 8) return 'linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%)';
          if (status_code === 3) return 'linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%)';
          if (status_code === 0) return 'linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%)';
          if (status_code === 1) return 'linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%)';
          return 'linear-gradient(135deg, #F5F5F5 0%, #EEEEEE 100%)';
        ]]]
    - border-left: |
        [[[
          const status_code = entity.attributes.status_code;
          if (status_code === 8) return '4px solid #4CAF50';
          if (status_code === 3) return '4px solid #2196F3';
          if (status_code === 0) return '4px solid #FF9800';
          if (status_code === 1) return '4px solid #F44336';
          return '4px solid #757575';
        ]]]
    - box-shadow: 0 2px 8px rgba(0,0,0,0.1)
  name:
    - font-size: 20px
    - font-weight: bold
    - color: |
        [[[
          const status_code = entity.attributes.status_code;
          if (status_code === 8) return '#4CAF50';
          if (status_code === 3) return '#2196F3';
          if (status_code === 0) return '#FF9800';
          if (status_code === 1) return '#F44336';
          return '#757575';
        ]]]
    - margin-bottom: 16px
custom_fields:
  icon_status: |
    [[[
      const status_code = entity.attributes.status_code;
      let english_status = 'Unknown';
      let icon = '❓';
      let color = '#757575';
      
      if (status_code === 8) { 
        english_status = 'Picked up / Gone'; 
        icon = '🏠'; 
        color = '#4CAF50';
      } else if (status_code === 3) { 
        english_status = 'Present at school'; 
        icon = '🏫'; 
        color = '#2196F3';
      } else if (status_code === 0) { 
        english_status = 'Not arrived'; 
        icon = '❌'; 
        color = '#FF9800';
      } else if (status_code === 1) { 
        english_status = 'Sick'; 
        icon = '🤒'; 
        color = '#F44336';
      } else if (status_code === 2) { 
        english_status = 'Holiday / Free'; 
        icon = '🏖️'; 
        color = '#9C27B0';
      }
      
      return `<div style="text-align: left; font-size: 16px; line-height: 1.8; color: #495057;">
        <div style="margin-bottom: 12px; font-size: 18px;">
          <span style="font-size: 24px; margin-right: 8px;">${icon}</span>
          <strong style="color: ${color};">Status:</strong> 
          <span style="color: ${color}; font-weight: 600;">${english_status}</span>
        </div>
        <div style="margin-bottom: 6px;">
          <strong style="color: #6c757d;">Arrived:</strong> 
          <span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px;">
            ${entity.attributes.check_in_time || 'Not yet'}
          </span>
        </div>
        <div style="margin-bottom: 6px;">
          <strong style="color: #6c757d;">Left:</strong> 
          <span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px;">
            ${entity.attributes.check_out_time || 'Still there'}
          </span>
        </div>
        <div style="margin-bottom: 12px;">
          <strong style="color: #6c757d;">Planned pickup:</strong> 
          <span style="font-family: monospace; background: #f8f9fa; padding: 2px 6px; border-radius: 4px;">
            ${entity.attributes.exit_time || 'Not set'}
          </span>
        </div>
        ${entity.attributes.comment ? `<div style="margin-top: 12px; padding: 12px; background: #fff3cd; border-radius: 6px; border-left: 3px solid #ffc107;">
          <strong style="color: #856404;">Notes:</strong><br>
          <em style="color: #856404;">${entity.attributes.comment}</em>
        </div>` : ''}
        ${entity.attributes.exit_with ? `<div style="margin-top: 8px;">
          <strong style="color: #6c757d;">Picked up by:</strong> 
          <span style="color: ${color}; font-weight: 600;">${entity.attributes.exit_with}</span>
        </div>` : ''}
      </div>`;
    ]]]
```

### Option 4: Multiple Children Grid

For displaying multiple children in a grid layout:

```yaml
type: grid
columns: 2
square: false
cards:
  - type: markdown
    content: |
      {% set entity = 'binary_sensor.easyiq_avi_emilie_present' %}
      {% set status_code = state_attr(entity, 'status_code') %}
      {% if status_code == 8 %}
        {% set icon = '🏠' %}
        {% set color = '#4CAF50' %}
        {% set status_text = 'Gone' %}
      {% elif status_code == 3 %}
        {% set icon = '🏫' %}
        {% set color = '#2196F3' %}
        {% set status_text = 'At School' %}
      {% else %}
        {% set icon = '❓' %}
        {% set color = '#757575' %}
        {% set status_text = 'Unknown' %}
      {% endif %}
      
      <div style="padding: 16px; border-radius: 8px; background: #f8f9fa; border-left: 4px solid {{ color }}; text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px;">{{ icon }}</div>
        <div style="font-size: 16px; font-weight: bold; color: {{ color }}; margin-bottom: 8px;">
          {{ state_attr(entity, 'child_name') }}
        </div>
        <div style="font-size: 14px; color: {{ color }}; font-weight: 600; margin-bottom: 8px;">
          {{ status_text }}
        </div>
        <div style="font-size: 12px; color: #6c757d;">
          In: {{ state_attr(entity, 'check_in_time') or 'Not yet' }}<br>
          Out: {{ state_attr(entity, 'check_out_time') or 'Still there' }}
        </div>
      </div>
      
  - type: markdown
    content: |
      {% set entity = 'binary_sensor.easyiq_max_emil_present' %}
      {% set status_code = state_attr(entity, 'status_code') %}
      {% if status_code == 8 %}
        {% set icon = '🏠' %}
        {% set color = '#4CAF50' %}
        {% set status_text = 'Gone' %}
      {% elif status_code == 3 %}
        {% set icon = '🏫' %}
        {% set color = '#2196F3' %}
        {% set status_text = 'At School' %}
      {% else %}
        {% set icon = '❓' %}
        {% set color = '#757575' %}
        {% set status_text = 'Unknown' %}
      {% endif %}
      
      <div style="padding: 16px; border-radius: 8px; background: #f8f9fa; border-left: 4px solid {{ color }}; text-align: center;">
        <div style="font-size: 32px; margin-bottom: 8px;">{{ icon }}</div>
        <div style="font-size: 16px; font-weight: bold; color: {{ color }}; margin-bottom: 8px;">
          {{ state_attr(entity, 'child_name') }}
        </div>
        <div style="font-size: 14px; color: {{ color }}; font-weight: 600; margin-bottom: 8px;">
          {{ status_text }}
        </div>
        <div style="font-size: 12px; color: #6c757d;">
          In: {{ state_attr(entity, 'check_in_time') or 'Not yet' }}<br>
          Out: {{ state_attr(entity, 'check_out_time') or 'Still there' }}
        </div>
      </div>
```

### Option 5: Entities Card with Custom Row

Simple entities card with custom formatting:

```yaml
type: entities
title: School Presence
entities:
  - type: custom:multiple-entity-row
    entity: binary_sensor.easyiq_avi_emilie_present
    name: |
      {% set status_code = state_attr('binary_sensor.easyiq_avi_emilie_present', 'status_code') %}
      {% if status_code == 8 %}🏠{% elif status_code == 3 %}🏫{% elif status_code == 0 %}❌{% elif status_code == 1 %}🤒{% else %}❓{% endif %}
      {{ state_attr('binary_sensor.easyiq_avi_emilie_present', 'child_name') }}
    secondary_info: |
      {% set status_code = state_attr('binary_sensor.easyiq_avi_emilie_present', 'status_code') %}
      {% if status_code == 8 %}Picked up / Gone
      {% elif status_code == 3 %}Present at school
      {% elif status_code == 0 %}Not arrived
      {% elif status_code == 1 %}Sick
      {% elif status_code == 2 %}Holiday / Free
      {% else %}Unknown{% endif %}
    entities:
      - attribute: check_in_time
        name: "⏰"
        format: time
      - attribute: check_out_time
        name: "🚪"
        format: time
      - attribute: exit_time
        name: "📅"
        format: time
```

## Status Code Reference

The integration provides these status codes with corresponding colors and icons:

| Code | Danish Status | English Status | Icon | Color |
|------|---------------|----------------|------|-------|
| 0 | IKKE KOMMET | Not arrived | ❌ | Orange (#FF9800) |
| 1 | SYG | Sick | 🤒 | Red (#F44336) |
| 2 | FERIE/FRI | Holiday / Free | 🏖️ | Purple (#9C27B0) |
| 3 | KOMMET/TIL STEDE | Present at school | 🏫 | Blue (#2196F3) |
| 4 | PÅ TUR | On trip | 🚌 | Deep Orange (#FF5722) |
| 5 | SOVER | Sleeping | 😴 | Blue Grey (#607D8B) |
| 8 | HENTET/GÅET | Picked up / Gone | 🏠 | Green (#4CAF50) |

## Customization Tips

1. **Change Entity Names**: Replace `binary_sensor.easyiq_avi_emilie_present` with your actual entity name
2. **Adjust Colors**: Modify the color codes to match your dashboard theme
3. **Add More Children**: Duplicate the card structure for multiple children
4. **Modify Icons**: Change the emoji icons to Material Design Icons (mdi:) if preferred
5. **Responsive Design**: Use CSS media queries for mobile-friendly layouts

## Installation Notes

- **Option 1 & 2**: Work with standard Home Assistant (no additional components needed)
- **Option 3**: Requires the `custom:button-card` component from HACS
- **Option 4**: Uses standard grid layout
- **Option 5**: Requires `custom:multiple-entity-row` component from HACS

Choose the option that best fits your Home Assistant setup and design preferences!