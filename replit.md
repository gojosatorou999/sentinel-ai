# Coastal Alert - Hazard Reporting System

## Overview

Coastal Alert is a voice-based hazard reporting system designed to protect coastal communities. Users can report hazards by entering their phone number on a web interface, which triggers an automated Twilio voice call to collect incident details. The system features an admin dashboard for viewing submitted reports.

The application follows a simple monolithic Flask architecture with:
- A public-facing reporting interface
- Twilio-powered voice call system for gathering hazard information
- Admin-protected reports dashboard
- CSV-based data persistence

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Web Framework
- **Flask** serves as the web framework handling all HTTP routes
- Session-based authentication for admin access using Flask's built-in session management
- Templates rendered with Jinja2

### Voice Call Integration
- **Twilio** handles outbound voice calls for collecting hazard reports
- Voice interactions use TwiML (Twilio Markup Language) for call flow control
- Gather elements collect user input via voice/DTMF tones

### Data Storage
- **CSV file** (`reports.csv`) serves as the primary data store
- In-memory dictionaries track ongoing call state (`call_data`) and report history (`all_reports`)
- Reports include: timestamp, phone, hazard type, location, severity, description

### Authentication
- Simple username/password authentication for admin portal
- Credentials stored in environment variables (`ADMIN_USERNAME`, `ADMIN_PASSWORD`)
- Session-based login state management

### Frontend
- Server-rendered HTML templates with static CSS
- Dark theme UI with coastal/maritime aesthetic
- AJAX calls for initiating phone calls without page refresh

### Timezone Handling
- All timestamps displayed in IST (Asia/Kolkata) using pytz

## External Dependencies

### Twilio (Voice API)
- **Purpose**: Automated outbound calls for hazard reporting
- **Configuration**: Requires `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` environment variables
- **Client**: Initialized only when credentials are present

### Environment Variables Required
| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio account identifier |
| `TWILIO_AUTH_TOKEN` | Twilio API authentication |
| `TWILIO_PHONE_NUMBER` | Outbound caller ID |
| `ADMIN_USERNAME` | Admin portal login |
| `ADMIN_PASSWORD` | Admin portal password |

### Python Dependencies
- `flask` - Web framework
- `twilio` - Twilio API client
- `pytz` - Timezone handling