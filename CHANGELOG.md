# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-09-15

### Added
- Initial release of EasyIQ Home Assistant integration
- Support for weekly schedule (weekplan) data retrieval
- Support for homework assignments (lektier) data retrieval
- Support for student presence status monitoring
- Support for Aula messages monitoring
- Calendar integration for school events
- Multi-child support for families with multiple students
- English interface with Danish school data support
- HACS compatibility for easy installation
- Configuration flow for easy setup through Home Assistant UI

### Features
- **Weekplan Sensor**: Displays weekly school schedule with events, subjects, and times
- **Homework Tracking**: Shows homework assignments with descriptions and due dates
- **Presence Monitoring**: Real-time attendance status updates
- **Calendar Events**: School schedule appears in Home Assistant calendar
- **Rich Attributes**: Detailed event information available as sensor attributes

### Technical
- Uses EasyIQ CalendarGetWeekplanEvents API endpoint
- Authenticates via Aula credentials (Unilogin)
- Supports both schedule events (itemType 9) and homework (itemType 4)
- Implements proper Home Assistant integration patterns
- Includes comprehensive error handling and logging

### Supported Institutions
- Danish schools using Aula + EasyIQ combination
- Tested with multiple institution configurations

## [Unreleased]

### Planned
- Support for additional EasyIQ features
- Enhanced error handling for network issues