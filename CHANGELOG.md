# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-05-02

### Added
- **MitID authentication**: Replaces the deprecated Unilogin password flow with the same
  MitID OAuth 2.0 + SAML flow used by the upstream `scaarup/aula` integration.
  - Supports both **MitID app** (QR code scan) and **MitID code reader** (token) methods
  - Multi-step config flow with a dedicated web view at
    `/api/aula_easyiq/auth/<flow_id>` for displaying QR codes and identity selection
  - Refresh-token-based renewal of access tokens, persisted in the config entry
  - Reauth flow triggered automatically when refresh fails (`ConfigEntryAuthFailed`)
- **Vendored `aula_login_client` package** (incl. `mitid_browserclient`) for the MitID
  flow, sourced from `scaarup/aula` (MIT). Credit retained.

### Changed
- **`manifest.json` requirements** now include `pycryptodome`, `qrcode`, `requests`,
  `beautifulsoup4`, and `lxml` for the MitID flow.
- **Config entry schema (VERSION = 2)** now stores `mitid_username`, `auth_method`,
  `access_token`, `refresh_token`, `token_expires_at` instead of `username` / `password`.
- **Aula API calls** now pass `access_token` as a query parameter (the MitID OAuth
  flow's tokens replace cookie-based session auth).

### Removed
- The Unilogin username/password login flow in `client.py`. Aula has deprecated this
  authentication method, so it no longer works in practice.

### Migration
- Existing 0.4.x users will receive a reauth prompt on the next restart and need
  to re-authenticate with MitID once.

## [0.4.0] - 2025-09-28

### Added
- **Configurable Data Range**: New configuration options for how many days forward to fetch data
  - Weekplan days forward (default: 5 days, range: 1-14 business days)
  - Homework days forward (default: 5 days, range: 1-14 business days)
- **Independent Day Settings**: Weekplan and homework can have different day ranges
- **Business Days Filtering**: Automatically excludes weekends from day counting
- **Dynamic Descriptions**: Sensor descriptions update based on configuration (e.g., "Next 3 Business Days")

### Changed
- **Client Implementation**: Enhanced to support configurable day ranges instead of hardcoded 5-day limit
- **Data Filtering**: Added intelligent business day filtering with `_filter_events_by_days()` method
- **HTML Builders**: Updated to show dynamic day descriptions in weekplan and homework content
- **Configuration UI**: Added new day range options with validation (1-14 days)

### Improved
- **Flexibility**: Users can configure shorter periods (1-3 days) for daily focus or longer periods (7-14 days) for better planning
- **Performance**: Fewer days means less data processing and storage
- **User Experience**: Clear configuration labels and comprehensive documentation
- **Backward Compatibility**: Maintains 5-day default for existing installations

### Fixed
- **Test Script**: Fixed missing `await` keyword in presence data retrieval test

## [0.3.0] - 2025-09-26

### Added
- **Configurable Update Intervals**: Individual update intervals for different data types
  - Weekplan update interval (default: 15 minutes) - EasyIQ API
  - Homework update interval (default: 15 minutes) - EasyIQ API
  - Presence update interval (default: 5 minutes) - Aula API
  - Messages update interval (default: 5 minutes) - Aula API
- **Smart Polling System**: Selective data updates based on individual intervals
- **Dual API Support**: Optimized routing between Aula API (real-time data) and EasyIQ API (schedule data)
- **Reduced API Load**: 46% reduction in API calls with intelligent polling
- **Configuration UI**: Clean interface for setting custom update intervals
- **Interval Validation**: All intervals must be between 60-3600 seconds (1 minute to 1 hour)

### Changed
- **Data Update Coordinator**: Enhanced to support per-section update intervals with automatic base frequency calculation
- **EasyIQ Client**: Added selective update method for efficient dual-API data retrieval
- **Configuration Flow**: Streamlined options to show only relevant interval settings
- **API Query Strategy**: Intelligent routing between Aula API (presence/messages) and EasyIQ API (weekplan/homework)

### Improved
- **Performance**: More efficient dual-API usage with targeted data updates
- **Flexibility**: Users can prioritize real-time data (presence/messages) with shorter intervals
- **Resource Usage**: 46% reduction in API calls while maintaining optimal data freshness
- **Code Quality**: Removed redundant configuration options and simplified implementation

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