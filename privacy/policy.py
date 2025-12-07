"""Privacy policy content and HTML generation"""


def get_privacy_policy_html():
    """
    Generate and return the privacy policy as HTML.
    
    Returns:
        str: Complete HTML privacy policy document
    """
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - Fantasy Basketball Service API</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        h1 {
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 10px;
            color: #2c3e50;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        h3 {
            color: #555;
            margin-top: 20px;
        }
        .summary-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background-color: white;
            border: 1px solid #ddd;
        }
        .summary-table th {
            background-color: #3498db;
            color: white;
            padding: 12px;
            text-align: left;
        }
        .summary-table td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        .summary-table tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .checkmark {
            color: #27ae60;
            font-weight: bold;
        }
        .xmark {
            color: #e74c3c;
            font-weight: bold;
        }
        .highlight {
            background-color: #fff3cd;
            padding: 15px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }
        .info-box {
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 4px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }
        ul {
            margin: 10px 0;
            padding-left: 30px;
        }
        li {
            margin: 8px 0;
        }
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
    </style>
</head>
<body>
    <h1>Privacy Policy - Fantasy Basketball Service API</h1>
    <p><strong>Effective Date:</strong> January 2025</p>

    <h2>Overview</h2>
    <p>This Privacy Policy describes how the Fantasy Basketball Service API ("Service") collects, uses, and protects user data and information. The Service is designed to provide read-only access to pre-configured fantasy basketball league data.</p>

    <h2>1. Data Access Scope</h2>
    
    <h3>1.1 Pre-Configured League Only</h3>
    <p>This Service is configured to access <strong>only one league</strong>:</p>
    <div class="info-box">
        <ul>
            <li><strong>League Name:</strong> Terrific Twelve</li>
            <li><strong>League ID:</strong> 30695</li>
            <li><strong>Year:</strong> 2025-2026 Season</li>
        </ul>
    </div>
    <p>The Service cannot be reconfigured to access other leagues. All endpoints are hardwired to read data exclusively from League ID 30695. Any requests for data from other leagues will be rejected.</p>

    <h3>1.2 Read-Only Operations</h3>
    <p>All endpoints provided by this Service are <strong>read-only</strong>. The API:</p>
    <ul>
        <li><span class="checkmark">✅</span> Can retrieve league data, team information, player rosters, and predictions</li>
        <li><span class="xmark">❌</span> Cannot make changes to team rosters</li>
        <li><span class="xmark">❌</span> Cannot modify league settings</li>
        <li><span class="xmark">❌</span> Cannot alter player lineups (except through authorized lineup optimization endpoints that respect ESPN constraints)</li>
        <li><span class="xmark">❌</span> Cannot execute trades or transactions</li>
        <li><span class="xmark">❌</span> Cannot modify team information</li>
    </ul>

    <h2>2. Authentication & Credentials</h2>
    
    <h3>2.1 API Key Authentication</h3>
    <p>Access to the Service requires an API key. The API key is:</p>
    <ul>
        <li>Used solely for rate limiting and access control</li>
        <li>Not stored on user devices</li>
        <li>Transmitted via secure HTTPS connections</li>
        <li>Managed through the <code>/api/v1/auth/</code> endpoints (admin-only)</li>
    </ul>

    <h3>2.2 League Manager Credentials</h3>
    <p>The Service uses <strong>League Manager credentials</strong> to access league data:</p>
    <ul>
        <li>These credentials are configured server-side only</li>
        <li>User requests do NOT include or transmit these credentials</li>
        <li>The Service acts as an intermediary, translating API requests into read-only ESPN API calls</li>
        <li>League Manager credentials are never exposed to end users</li>
    </ul>

    <h3>2.3 Credential Security</h3>
    <ul>
        <li>Credentials are stored in environment variables (<code>.env</code> file)</li>
        <li>Never committed to version control</li>
        <li>Access restricted to authorized administrators only</li>
        <li>Rotated according to security best practices</li>
    </ul>

    <h2>3. Data Collection & Use</h2>
    
    <h3>3.1 What Data We Access</h3>
    <p>The Service accesses and may return:</p>
    <ul>
        <li>Player names, positions, and NBA team affiliations</li>
        <li>Player injury status and availability information</li>
        <li>Team rosters and player statistics</li>
        <li>Historical and projected fantasy points</li>
        <li>League standings and matchup information</li>
        <li>NBA game schedules and outcomes</li>
        <li>Advanced analytics on team performance</li>
    </ul>

    <h3>3.2 What Data We Do NOT Access</h3>
    <ul>
        <li>User passwords or authentication credentials</li>
        <li>Personal identifying information beyond what ESPN stores</li>
        <li>Trading messages or private team notes</li>
        <li>Financial information</li>
        <li>Email addresses (beyond League Manager account)</li>
        <li>IP addresses or detailed usage logs</li>
        <li>Personal health information beyond injury status</li>
    </ul>

    <h3>3.3 Data Use</h3>
    <p>Data is accessed for the following purposes only:</p>
    <ul>
        <li>Providing fantasy basketball predictions and analysis</li>
        <li>Generating team performance reports</li>
        <li>Facilitating lineup optimization recommendations</li>
        <li>Supporting player scouting and analysis</li>
        <li>Historical data retention for season-long analysis</li>
    </ul>

    <h2>4. Data Storage & Retention</h2>
    
    <h3>4.1 Caching</h3>
    <p>The Service may cache league data locally for performance optimization:</p>
    <ul>
        <li>Cache files are stored in <code>~/.fantasy_league_cache/</code></li>
        <li>Cache expires automatically and is refreshed from ESPN regularly</li>
        <li>Cache contains only data from League ID 30695</li>
        <li>Cache can be manually cleared via admin endpoints</li>
    </ul>

    <h3>4.2 Retention Policy</h3>
    <ul>
        <li>Active league data is retained for the duration of the season</li>
        <li>Historical data from previous seasons is retained for analysis purposes</li>
        <li>Cache and temporary data are cleared upon server shutdown</li>
        <li>Users may request cache deletion through admin endpoints</li>
    </ul>

    <h3>4.3 No Third-Party Sharing</h3>
    <p>Data accessed through this Service is:</p>
    <ul>
        <li><span class="xmark">❌</span> NOT shared with third parties</li>
        <li><span class="xmark">❌</span> NOT sold or monetized</li>
        <li><span class="xmark">❌</span> NOT used for marketing purposes</li>
        <li><span class="xmark">❌</span> NOT transferred to other services without explicit consent</li>
        <li><span class="checkmark">✅</span> Used only by League ID 30695 members and authorized administrators</li>
    </ul>

    <h2>5. Data Security</h2>
    
    <h3>5.1 Transmission Security</h3>
    <ul>
        <li>All API communication uses HTTPS/TLS encryption</li>
        <li>API keys are transmitted in request headers or query parameters</li>
        <li>Data in transit is protected from interception</li>
    </ul>

    <h3>5.2 Storage Security</h3>
    <ul>
        <li>Cached data is stored locally with file-system permissions</li>
        <li>Environment variables containing credentials are protected</li>
        <li>No sensitive data is logged in application logs</li>
        <li>Database queries are parameterized to prevent injection</li>
    </ul>

    <h3>5.3 Access Control</h3>
    <ul>
        <li>Admin endpoints require special authentication</li>
        <li>API key management controls who can access the Service</li>
        <li>Read-only database operations prevent accidental data modification</li>
        <li>All operations are logged for audit purposes</li>
    </ul>

    <h2>6. League Manager Authorization</h2>
    
    <h3>6.1 Proxy Access</h3>
    <p>Users access league data through the Service as a proxy:</p>
    <ul>
        <li>The Service acts on behalf of the League Manager</li>
        <li>League Manager has authorized this data access through configured credentials</li>
        <li>Users' read-only access is mediated by the Service</li>
        <li>The Service ensures no write operations modify league data</li>
    </ul>

    <h3>6.2 Scope Limitations</h3>
    <p>Access is strictly limited to:</p>
    <ul>
        <li>One league: Terrific Twelve (ID 30695)</li>
        <li>Read-only operations only</li>
        <li>Data relevant to the current season and user's team</li>
        <li>Public and team-visible information only</li>
    </ul>

    <h2>7. User Rights & Responsibilities</h2>
    
    <h3>7.1 User Rights</h3>
    <p>You have the right to:</p>
    <ul>
        <li>Know what data the Service accesses</li>
        <li>Request clarification on data usage</li>
        <li>Report security concerns to administrators</li>
        <li>Request your API key to be revoked</li>
        <li>Access your team's data through the API</li>
    </ul>

    <h3>7.2 User Responsibilities</h3>
    <p>By using the Service, you agree to:</p>
    <ul>
        <li>Use your API key responsibly and keep it confidential</li>
        <li>Not attempt to access leagues other than ID 30695</li>
        <li>Not attempt to modify league data through the Service</li>
        <li>Not reverse-engineer or circumvent security measures</li>
        <li>Respect rate limits and fair usage policies</li>
        <li>Comply with ESPN's Terms of Service</li>
    </ul>

    <h2>8. Limitations & Disclaimers</h2>
    
    <h3>8.1 League-Specific Limitation</h3>
    <div class="highlight">
        <p>This Service is hard-coded to access only League ID 30695 (Terrific Twelve).</p>
        <ul>
            <li>No other leagues can be accessed</li>
            <li>No configuration options exist to change the target league</li>
            <li>This is an intentional design decision for security and compliance</li>
        </ul>
    </div>

    <h3>8.2 Read-Only Guarantee</h3>
    <p>The Service provides read-only access. Any modifications to league data must be made directly through ESPN's web interface or official mobile app with appropriate credentials.</p>

    <h3>8.3 Prediction Accuracy</h3>
    <ul>
        <li>Predictions and analysis are estimates based on available data</li>
        <li>Actual results may vary significantly</li>
        <li>The Service makes no warranty regarding prediction accuracy</li>
    </ul>

    <h3>8.4 Data Availability</h3>
    <ul>
        <li>The Service depends on ESPN's API availability</li>
        <li>Outages or disruptions may temporarily affect data access</li>
        <li>Historical data may not be complete for early-season periods</li>
    </ul>

    <h2>Summary of Key Privacy Protections</h2>
    <table class="summary-table">
        <thead>
            <tr>
                <th>Protection</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Single League Limitation</td>
                <td><span class="checkmark">✅ Only League ID 30695</span></td>
            </tr>
            <tr>
                <td>Read-Only Operations</td>
                <td><span class="checkmark">✅ No write/modify capabilities</span></td>
            </tr>
            <tr>
                <td>Encrypted Transmission</td>
                <td><span class="checkmark">✅ HTTPS/TLS</span></td>
            </tr>
            <tr>
                <td>No Third-Party Sharing</td>
                <td><span class="checkmark">✅ Data stays within league</span></td>
            </tr>
            <tr>
                <td>Server-Side Credentials</td>
                <td><span class="checkmark">✅ Never exposed to users</span></td>
            </tr>
            <tr>
                <td>API Key Management</td>
                <td><span class="checkmark">✅ Rate limiting & access control</span></td>
            </tr>
            <tr>
                <td>Local Caching</td>
                <td><span class="checkmark">✅ Auto-expiring, clearable</span></td>
            </tr>
            <tr>
                <td>Audit Logging</td>
                <td><span class="checkmark">✅ All operations logged</span></td>
            </tr>
            <tr>
                <td>No Password Storage</td>
                <td><span class="checkmark">✅ Not collected</span></td>
            </tr>
            <tr>
                <td>No Personal Data Sales</td>
                <td><span class="checkmark">✅ Not monetized</span></td>
            </tr>
        </tbody>
    </table>

    <div class="footer">
        <p><strong>Last Updated:</strong> January 2025</p>
        <p><strong>Service:</strong> Fantasy Basketball Predictions API</p>
        <p><strong>Version:</strong> 1.0.0</p>
        <p><strong>League:</strong> Terrific Twelve (ID 30695)</p>
    </div>
</body>
</html>
    """
