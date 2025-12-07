# Privacy Policy - Fantasy Basketball Service API

**Effective Date:** January 2025

## Overview

This Privacy Policy describes how the Fantasy Basketball Service API ("Service") collects, uses, and protects user data and information. The Service is designed to provide read-only access to pre-configured fantasy basketball league data.

## 1. Data Access Scope

### 1.1 Pre-Configured League Only
This Service is configured to access **only one league**:
- **League Name:** Terrific Twelve
- **League ID:** 30695
- **Year:** 2025-2026 Season

The Service cannot be reconfigured to access other leagues. All endpoints are hardwired to read data exclusively from League ID 30695. Any requests for data from other leagues will be rejected.

### 1.2 Read-Only Operations
All endpoints provided by this Service are **read-only**. The API:
- ✅ Can retrieve league data, team information, player rosters, and predictions
- ❌ Cannot make changes to team rosters
- ❌ Cannot modify league settings
- ❌ Cannot alter player lineups (except through authorized lineup optimization endpoints that respect ESPN constraints)
- ❌ Cannot execute trades or transactions
- ❌ Cannot modify team information

Any endpoints that appear to modify data (such as `/api/v1/lineup/update`, `/api/v1/scheduling/post-transaction`) operate only within the constraints of the ESPN Fantasy API and require explicit league manager authorization through separate credentials.

## 2. Authentication & Credentials

### 2.1 API Key Authentication
Access to the Service requires an API key. The API key is:
- Used solely for rate limiting and access control
- Not stored on user devices
- Transmitted via secure HTTPS connections
- Managed through the `/api/v1/auth/` endpoints (admin-only)

### 2.2 League Manager Credentials
The Service uses **League Manager credentials** to access league data:
- These credentials are configured server-side only
- User requests do NOT include or transmit these credentials
- The Service acts as an intermediary, translating API requests into read-only ESPN API calls
- League Manager credentials are never exposed to end users

### 2.3 Credential Security
- Credentials are stored in environment variables (`.env` file)
- Never committed to version control
- Access restricted to authorized administrators only
- Rotated according to security best practices

## 3. Data Collection & Use

### 3.1 What Data We Access
The Service accesses and may return:
- Player names, positions, and NBA team affiliations
- Player injury status and availability information
- Team rosters and player statistics
- Historical and projected fantasy points
- League standings and matchup information
- NBA game schedules and outcomes
- Advanced analytics on team performance

### 3.2 What Data We Do NOT Access
- User passwords or authentication credentials
- Personal identifying information beyond what ESPN stores
- Trading messages or private team notes
- Financial information
- Email addresses (beyond League Manager account)
- IP addresses or detailed usage logs
- Personal health information beyond injury status

### 3.3 Data Use
Data is accessed for the following purposes only:
- Providing fantasy basketball predictions and analysis
- Generating team performance reports
- Facilitating lineup optimization recommendations
- Supporting player scouting and analysis
- Historical data retention for season-long analysis

All data usage remains within the scope of League ID 30695 only.

## 4. Data Storage & Retention

### 4.1 Caching
The Service may cache league data locally for performance optimization:
- Cache files are stored in `~/.fantasy_league_cache/`
- Cache expires automatically and is refreshed from ESPN regularly
- Cache contains only data from League ID 30695
- Cache can be manually cleared via admin endpoints

### 4.2 Retention Policy
- Active league data is retained for the duration of the season
- Historical data from previous seasons is retained for analysis purposes
- Cache and temporary data are cleared upon server shutdown
- Users may request cache deletion through admin endpoints

### 4.3 No Third-Party Sharing
Data accessed through this Service is:
- ❌ NOT shared with third parties
- ❌ NOT sold or monetized
- ❌ NOT used for marketing purposes
- ❌ NOT transferred to other services without explicit consent
- ✅ Used only by League ID 30695 members and authorized administrators

## 5. Data Security

### 5.1 Transmission Security
- All API communication uses HTTPS/TLS encryption
- API keys are transmitted in request headers or query parameters
- Data in transit is protected from interception

### 5.2 Storage Security
- Cached data is stored locally with file-system permissions
- Environment variables containing credentials are protected
- No sensitive data is logged in application logs
- Database queries are parameterized to prevent injection

### 5.3 Access Control
- Admin endpoints require special authentication
- API key management controls who can access the Service
- Read-only database operations prevent accidental data modification
- All operations are logged for audit purposes

## 6. League Manager Authorization

### 6.1 Proxy Access
Users access league data through the Service as a proxy:
- The Service acts on behalf of the League Manager
- League Manager has authorized this data access through configured credentials
- Users' read-only access is mediated by the Service
- The Service ensures no write operations modify league data

### 6.2 Scope Limitations
Access is strictly limited to:
- One league: Terrific Twelve (ID 30695)
- Read-only operations only
- Data relevant to the current season and user's team
- Public and team-visible information only

## 7. User Rights & Responsibilities

### 7.1 User Rights
You have the right to:
- Know what data the Service accesses
- Request clarification on data usage
- Report security concerns to administrators
- Request your API key to be revoked
- Access your team's data through the API

### 7.2 User Responsibilities
By using the Service, you agree to:
- Use your API key responsibly and keep it confidential
- Not attempt to access leagues other than ID 30695
- Not attempt to modify league data through the Service
- Not reverse-engineer or circumvent security measures
- Respect rate limits and fair usage policies
- Comply with ESPN's Terms of Service

## 8. Limitations & Disclaimers

### 8.1 League-Specific Limitation
This Service is hard-coded to access only League ID 30695 (Terrific Twelve). 
- No other leagues can be accessed
- No configuration options exist to change the target league
- This is an intentional design decision for security and compliance

### 8.2 Read-Only Guarantee
The Service provides read-only access. Any modifications to league data must be made directly through ESPN's web interface or official mobile app with appropriate credentials.

### 8.3 Prediction Accuracy
- Predictions and analysis are estimates based on available data
- Actual results may vary significantly
- The Service makes no warranty regarding prediction accuracy

### 8.4 Data Availability
- The Service depends on ESPN's API availability
- Outages or disruptions may temporarily affect data access
- Historical data may not be complete for early-season periods

## 9. Changes to This Policy

The Service provider may update this Privacy Policy at any time. Users will be notified of material changes through:
- Updates to this document in the repository
- Notifications via the `/privacy` endpoint
- Announcements to League ID 30695 members

Continued use of the Service constitutes acceptance of the updated policy.

## 10. Contact & Support

For questions about this Privacy Policy or data practices:
- Contact the Service administrator through the league communications
- Report security concerns immediately to the League Manager
- Submit feature requests or bug reports through official channels

---

## Summary of Key Privacy Protections

| Protection | Status |
|-----------|--------|
| Single League Limitation | ✅ Only League ID 30695 |
| Read-Only Operations | ✅ No write/modify capabilities |
| Encrypted Transmission | ✅ HTTPS/TLS |
| No Third-Party Sharing | ✅ Data stays within league |
| Server-Side Credentials | ✅ Never exposed to users |
| API Key Management | ✅ Rate limiting & access control |
| Local Caching | ✅ Auto-expiring, clearable |
| Audit Logging | ✅ All operations logged |
| No Password Storage | ✅ Not collected |
| No Personal Data Sales | ✅ Not monetized |

---

**Last Updated:** January 2025
**Service:** Fantasy Basketball Predictions API
**Version:** 1.0.0
