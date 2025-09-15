# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-15

### Added
- Initial release of EasyIQ Home Assistant integration
- Support for weekly schedule (weekplan) data retrieval
- Support for homework assignments (lektier) data retrieval
- Support for student presence status monitoring
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
- Authenticates via Aula credentials
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
- Improved caching for better performance
- Support for multiple institution configurations