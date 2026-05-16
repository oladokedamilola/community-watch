# GridWatch - Outage Monitoring System

## Overview

GridWatch is a comprehensive web-based platform designed to bridge the communication gap between rural communities and utility service providers. The system enables community members to report electricity, water supply, and telecommunications outages in real-time, while providing administrators with powerful tools to monitor, verify, and manage these reports efficiently.

## Purpose

In many rural communities across Africa, access to essential services such as electricity, water supply, and telecommunications remains unstable. Residents face frequent outages that can last for hours or even days, with no efficient way to report these issues or track their resolution. Traditional reporting methods are often manual, unreliable, and lack transparency.

GridWatch addresses these challenges by providing:
- A centralized platform for outage reporting and monitoring
- Real-time status updates and notifications
- Data-driven insights for service providers
- Community-powered transparency

## Key Features

### For Community Members

#### Report Outages
- Submit reports for electricity, water supply, or network outages
- Provide location details with interactive map pinning
- Upload photos as evidence
- Optional anonymous reporting
- Automatic reference number generation

#### Track Reports
- Unique report ID for each submission
- Real-time status tracking (Pending → Verified → In Progress → Resolved)
- Status history timeline
- Email and in-app notifications for status changes

#### Community Feed
- Browse all public outage reports
- React with "Urgent" or "Helpful" buttons
- Comment on reports
- Sort by latest, most urgent, or most discussed
- Filter by outage type
- Save posts for later reference

#### Interactive Map
- View all reported outages on a live map
- Color-coded markers by outage type
- Click markers to see report details
- Filter by type, status, and date range
- Toggle between marker and heatmap views
- Search any location
- Find your current location

#### Dashboard
- Personal statistics (total reports, pending, resolved)
- List of recent reports
- Nearby active outages based on your village
- Quick action buttons for common tasks

#### Profile Management
- Update personal information
- Upload profile picture
- Set village/community location
- Change password
- Set up password for Google-authenticated accounts

### For Administrators

#### Admin Dashboard
- Key metrics overview (total reports, pending, in progress, resolved)
- Reports by type chart
- Recent reports list
- Quick action buttons

#### Report Management
- View all reports with pagination
- Filter by status, type, and search
- Bulk status updates
- Detailed report view with full information
- Update report status with internal notes
- Add resolution notes visible to users
- Assign reports to teams
- Set estimated restoration time

#### Analytics
- Overview metrics with date range filtering
- Report trends (daily, weekly, monthly)
- Reports by type and status charts
- Response time analytics by outage type
- Most affected villages ranking
- Reports by hour distribution
- Export data to CSV, Excel, or PDF

#### User Management
- View all registered users
- User details and activity
- Role-based access control

### Notification System

GridWatch features a comprehensive multi-channel notification system:

#### Email Notifications
- Welcome email on registration
- Email verification for account activation
- Report submission confirmation
- Status change updates
- Resolution notices
- Password reset instructions
- Password setup for Google-authenticated users

#### In-App Notifications
- Real-time notification bell with badge counter
- Mark notifications as read
- Delete individual notifications
- Mark all as read
- Notification history with pagination

#### Web Push Notifications (PWA)
- Browser push notifications for status updates
- Works even when the app is closed
- Permission-based opt-in

### Authentication & Security

#### Account Management
- Email-based registration (no username required)
- Email verification for account activation
- Password reset functionality
- Password strength requirements
- Rate limiting for security

#### Social Authentication
- Google OAuth integration
- Automatic account linking for existing emails
- Password setup for Google-authenticated users

#### Security Features
- CSRF protection
- XSS prevention
- SQL injection protection
- Rate limiting for login, registration, and password reset
- Session management with "Remember Me" option

### Progressive Web App (PWA)

GridWatch is fully installable as a Progressive Web App:

- Install on mobile or desktop devices
- Offline support with service workers
- Offline report queuing
- Background sync when connection returns
- Push notifications
- Splash screen on mobile
- App-like experience

### Mapping & Geocoding

- Interactive maps using Leaflet.js
- Automatic geocoding of location text to coordinates
- Reverse geocoding for coordinates to location names
- Location search with autocomplete
- Distance calculation for nearby reports
- Fallback geocoding database for Nigerian locations

### Data Export

- Export reports to CSV format
- Export reports to Excel format
- Export summary reports to PDF
- Filtered exports based on status, type, and date range

## Technology Stack

### Backend
- **Framework**: Django 6.0
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: Django Auth + Allauth
- **Email**: SMTP with Gmail integration
- **Task Queue**: Background sync for PWA

### Frontend
- **HTML/CSS**: Custom responsive design
- **JavaScript**: Vanilla JS with AJAX
- **CSS Framework**: Custom CSS with CSS Grid and Flexbox
- **Icons**: Font Awesome 6
- **Fonts**: Poppins + Roboto (Google Fonts)

### Mapping
- **Library**: Leaflet.js
- **Tile Provider**: CartoDB Voyager
- **Geocoding**: OpenStreetMap Nominatim
- **Clustering**: Leaflet.markercluster
- **Heatmaps**: Leaflet.heat

### PWA
- **Service Worker**: Custom implementation
- **Manifest**: Web App Manifest
- **Offline Storage**: IndexedDB
- **Push Notifications**: Web Push API

### Third-Party Integrations
- Google OAuth 2.0
- Google Maps API (optional fallback)
- Chart.js for analytics

## System Requirements

### Web Browser
- Modern browser with JavaScript enabled
- Chrome 60+ (recommended for PWA features)
- Firefox 60+
- Safari 12+
- Edge 79+

### Internet Connection
- Required for real-time features
- Offline mode available for report submission (syncs when online)

### Device Support
- Desktop: Full experience with sidebar navigation
- Tablet: Responsive layout with collapsible sidebar
- Mobile: Touch-friendly interface with bottom navigation

## Database Schema

### Core Models

#### CustomUser
- Email (unique, used for login)
- First name, last name
- Role flags (is_admin, is_active, is_staff)
- Profile information
- Timestamps

#### Profile
- One-to-one with User
- Profile picture
- Phone number
- Village/community
- Timestamps

#### OutageReport
- Report ID (auto-generated, format: GW-YYYYMMDD-XXXX)
- Outage type (electricity, water, network)
- Location text and coordinates
- Description
- Photo upload
- Status (pending, verified, in_progress, resolved, rejected)
- User association (with anonymous option)
- Timestamps (reported, verified, resolved)

#### ReportUpdate
- Tracks status changes over time
- Notes from admin
- User who made the update

#### Notification
- User association
- Notification type
- Title and message
- Link to related report
- Read status
- Timestamp

#### ReportReaction
- User to report relationship
- Reaction type (urgent, helpful, confirm)
- Timestamp

#### ReportComment
- User to report relationship
- Comment text
- Edit tracking
- Timestamps

#### SavedPost
- User to report relationship
- Timestamp

#### EmailVerification
- Token-based email verification
- Expiry handling

#### PasswordReset
- Token-based password reset
- Expiry handling

#### PasswordSetup
- For Google-authenticated users to set password
- Token-based with expiry

#### RateLimit
- Tracks attempts for various actions
- Blocking mechanism for security

## Installation Instructions

### Prerequisites
- Python 3.12 or higher
- pip package manager
- Virtual environment (recommended)

### Setup Steps

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env` file:
```env
DJANGO_SECRET_KEY=your-secret-key
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
SITE_URL=http://127.0.0.1:8000
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser (admin):
```bash
python manage.py createsuperuser
```

6. Collect static files:
```bash
python manage.py collectstatic
```

7. Run development server:
```bash
python manage.py runserver
```

## Usage Guide

### For Community Members

#### Registering an Account
1. Navigate to the registration page
2. Enter your first name, last name, and email address
3. Create a strong password
4. Submit the form
5. Check your email for verification link
6. Click the link to activate your account

#### Reporting an Outage
1. Log in to your account
2. Click "Report Outage" in the sidebar
3. Select the outage type (Electricity, Water, or Network)
4. Enter your location (village/town and state)
5. Provide a detailed description
6. Optionally upload a photo
7. Optionally provide contact information
8. Submit the report

#### Tracking Your Report
1. Go to "My Reports" in the sidebar
2. Click "Track Status" on any report
3. View the status timeline
4. See admin notes and resolution details
5. Receive notifications when status changes

#### Using the Community Feed
1. Navigate to "Community Feed"
2. Browse recent reports from all users
3. React with "Urgent" or "Helpful"
4. Comment on reports
5. Save important posts
6. Filter by type or sort order

#### Viewing the Outage Map
1. Click "Outage Map" in the sidebar
2. See all reported outages plotted on the map
3. Click markers to view report details
4. Use filters to narrow down results
5. Toggle between marker and heatmap view
6. Search for specific locations

### For Administrators

#### Managing Reports
1. Log in with admin credentials
2. Navigate to "All Reports" in the admin section
3. Filter reports by status, type, or search
4. Click "View" on any report
5. Update status with internal notes
6. Add resolution notes visible to users
7. Assign to team members
8. Set estimated restoration time

#### Using Analytics
1. Go to "Analytics" in the admin section
2. View key metrics and charts
3. Filter by date range
4. Export data to CSV, Excel, or PDF
5. Identify outage patterns and hotspots

## API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reports/api/outages/geojson/` | GET | Returns outage data as GeoJSON for mapping |
| `/reports/api/outages/heatmap/` | GET | Returns heatmap data |
| `/reports/api/search-location/` | GET | Geocodes a location name |
| `/reports/api/reverse-geocode/` | GET | Converts coordinates to location name |
| `/reports/api/outages/nearby/` | GET | Finds nearby outages |

### Authenticated Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reports/api/submit/` | POST | Submit new outage report |
| `/reports/api/reaction/<id>/` | POST | Add/remove reaction |
| `/reports/api/comment/<id>/` | POST | Add comment |
| `/reports/api/comments/<id>/` | GET | Get comments |
| `/reports/api/save-post/<id>/` | POST | Save/unsave post |
| `/reports/api/notifications/` | GET | Get user notifications |
| `/reports/api/notifications/mark-read/<id>/` | POST | Mark notification as read |

## Email Templates

GridWatch includes professionally designed email templates for:

- Welcome email
- Email verification
- Report submission confirmation
- Status update notification
- Resolution notice
- Password reset
- Password setup (for Google users)
- Admin new report notification

## PWA Features

### Offline Capabilities
- Service worker caches static assets
- Offline fallback page
- Report queue for offline submissions
- IndexedDB storage for pending reports

### Installation
- Users can install GridWatch as an app
- Home screen icon with custom branding
- Splash screen on launch
- Standalone window (no browser chrome)

## Security Considerations

- All passwords are hashed using Django's PBKDF2 algorithm
- CSRF tokens on all forms
- XSS protection through template escaping
- SQL injection prevention via Django ORM
- Rate limiting on sensitive actions
- Email verification required for account activation
- Session management with configurable expiry
- Secure headers (HSTS, X-Frame-Options, etc.)

## Performance Optimizations

- Database indexing on frequently queried fields
- Pagination for large datasets
- AJAX requests for real-time updates
- Lazy loading for images
- Optimized static file delivery
- Marker clustering for map performance
- Caching of geocoding results

## Troubleshooting

### Common Issues

**Map markers not displaying**
- Ensure reports have latitude and longitude coordinates
- Check that geocoding is working for new reports
- Verify Leaflet.js library is loading

**Notifications not sending**
- Check email configuration in settings
- Verify email backend is properly configured
- Check spam folder for emails
- Ensure user has consented to web push notifications

**PWA not installing**
- Site must be served over HTTPS
- Manifest.json must be accessible
- Service worker must register successfully
- Check browser console for errors

**Slow performance**
- Enable database indexing
- Implement pagination for large datasets
- Use marker clustering for maps with many points
- Optimize image uploads (max 5MB)

## Future Enhancements

- SMS notifications for areas with limited internet
- Voice-based reporting for low-literacy users
- Multi-language support (French, Swahili, Yoruba, Hausa)
- Integration with utility company APIs
- Automated outage detection via IoT sensors
- Mobile app (React Native / Flutter)
- Real-time chat between users and admins
- Community reputation system
- Predictive outage analytics using machine learning

## License

This project is proprietary and confidential. Unauthorized copying, distribution, or use of this software is strictly prohibited.

## Support

For technical support or inquiries, please contact the system administrator through the official channels.

---

**GridWatch - Watch. Report. Restore.**