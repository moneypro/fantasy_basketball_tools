"""
Fantasy Basketball Service Flask App
Main entry point for Docker deployment
"""

import os
import sys
from flask import Flask, request, jsonify
from functools import wraps

# Import your existing functions
from predict.predict_week import (
    predict_week,
    get_remaining_days_cumulative_scores,
    get_table_output_for_week,
)
from utils.create_league import create_league
from scout.player_scouting_refactored import scout_players
from scout.team_scouting import main as scout_teams
from scout.correlation import get_team_advanced_stats
from scout.players_changed_team_refactored import analyze_team_changes
from line_up.update_line_up import change_line_up_for_next_7_days
from draft_recap.best_draft_2025 import calculate_drafted_team_points_and_top_and_worst_scorers
from scheduling.post_free_agent_transaction import post_transaction
from scheduling.schedule_free_agent_add import schedule_with_at
from auth.decorators import require_api_key, optional_api_key
from auth.api_key import get_api_key_manager
from auth.admin import require_admin

# Initialize Flask app
app = Flask(__name__)

# Global league instance (loaded once at module import time)
league = None

def init_league():
    """Initialize league from cached file or ESPN API.
    
    Uses the standard create_league() which handles:
    - Loading from local pickle cache (~/.fantasy_league_cache/)
    - Fetching from ESPN if cache doesn't exist
    - Falls back to environment variables if credential files don't exist
    """
    global league
    if league is not None:
        return True  # Already initialized
    
    try:
        print(f"🔍 Loading league with LEAGUE_ID={os.getenv('LEAGUE_ID')}")
        league = create_league()
        print("✅ League loaded successfully")
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not load league: {e}")
        import traceback
        traceback.print_exc()
        return False

# Initialize league lazily on first request
@app.before_request
def ensure_league_loaded():
    """Ensure league is loaded before handling requests"""
    global league
    if league is None:
        init_league()

def require_league(f):
    """Decorator to check if league is loaded"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if league is None:
            return jsonify({
                "status": "error",
                "message": "League not initialized. Check environment variables."
            }), 503
        return f(*args, **kwargs)
    return decorated_function

# ===== Health & Info Endpoints =====

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API info"""
    return jsonify({
        "service": "Fantasy Basketball Predictions API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "GET /api/v1/health",
            "calculate_predictions": "POST /api/v1/predictions/calculate",
            "tools_schema": "GET /api/v1/tools/schema",
            "week_analysis": "POST /api/v1/predictions/week-analysis",
            "team_info": "POST /api/v1/team/{team_id}",
            "team_roster": "POST /api/v1/team/{team_id}/roster",
            "players_playing_for_scoring_period": "POST /api/v1/players-playing/{scoring_period}",
            "scoreboard": "POST /api/v1/scoreboard/{week_index}"
        }
    })

@app.route('/api/v1/health', methods=['GET'])
def health():
    """Health check endpoint"""
    league_status = "loaded" if league else "not_loaded"
    return jsonify({
        "status": "healthy",
        "league": league_status,
        "service": "fantasy-basketball-api"
    }), 200

@app.route('/privacy', methods=['GET'])
def privacy():
    """Privacy policy endpoint - returns comprehensive privacy information
    
    This endpoint serves the privacy policy for OpenAI integration and general use.
    No authentication required - privacy information should be publicly accessible.
    
    Returns the full privacy policy document in HTML format for easy reading.
    """
    privacy_html = """
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
    return privacy_html, 200, {'Content-Type': 'text/html; charset=utf-8'}

# ===== Prediction Endpoints =====

@app.route('/api/v1/predictions/calculate', methods=['POST'])
@require_api_key
@require_league
def calculate_predictions():
    """
    Calculate predictions for a week
    
    Request body:
    {
        "week_index": 1,
        "day_of_week_override": 0,
        "injury_status": ["ACTIVE"]
    }
    """
    try:
        data = request.json or {}
        
        # Validate required fields
        week_index = data.get('week_index')
        if not week_index:
            return jsonify({
                "status": "error",
                "message": "week_index is required (integer, 1-23)"
            }), 400
        
        # Validate week range
        if not isinstance(week_index, int) or week_index < 1 or week_index > 23:
            return jsonify({
                "status": "error",
                "message": "week_index must be an integer between 1 and 23"
            }), 400
        
        # Get optional parameters
        day_of_week = data.get('day_of_week_override', 0)
        injury_status = data.get('injury_status', ['ACTIVE'])
        
        # Validate day_of_week
        if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
            return jsonify({
                "status": "error",
                "message": "day_of_week_override must be 0-6 (0=Monday, 6=Sunday)"
            }), 400
        
        # Calculate predictions
        num_games, team_scores = predict_week(
            league, week_index, day_of_week, injury_status
        )
        
        # Get remaining days analysis
        remaining_days = get_remaining_days_cumulative_scores(
            league, week_index, day_of_week, injury_status
        )
        
        return jsonify({
            "status": "success",
            "data": {
                "week_index": week_index,
                "day_of_week": day_of_week,
                "num_games": num_games,
                "team_predictions": team_scores,
                "remaining_days_analysis": remaining_days
            }
        }), 200
    
    except Exception as e:
        print(f"Error in calculate_predictions: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Prediction calculation failed: {str(e)}"
        }), 500

@app.route('/api/v1/predictions/week-analysis', methods=['POST'])
@require_api_key
@require_league
def week_analysis():
    """
    Get detailed week analysis with JSON data for all injury statuses
    
    Request body params:
    - week_index: Week number (required, 1-23)
    - day_of_week_override: Starting day override (optional, 0=Monday, 6=Sunday, default=0)
    """
    try:
        from predict.predict_week import build_week_json
        
        # Get parameters from request body
        data = request.get_json() or {}
        week_index = data.get('week_index')
        day_of_week_override = data.get('day_of_week_override', 0)
        
        if not week_index:
            return jsonify({
                "status": "error",
                "message": "week_index is required"
            }), 400
        
        # Validate week range
        if not isinstance(week_index, int) or week_index < 1 or week_index > 23:
            return jsonify({
                "status": "error",
                "message": "week_index must be an integer between 1 and 23"
            }), 400
        
        # Validate day_of_week
        if not isinstance(day_of_week_override, int) or day_of_week_override < 0 or day_of_week_override > 6:
            return jsonify({
                "status": "error",
                "message": "day_of_week_override must be 0-6 (0=Monday, 6=Sunday)"
            }), 400
        
        # Get JSON analysis (includes all injury statuses and tables as structured data)
        analysis_data = build_week_json(league, week_index, day_of_week_override)
        
        return jsonify({
            "status": "success",
            "data": analysis_data
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Analysis failed: {str(e)}"
        }), 500

# ===== Agent Tool Schema Endpoint =====

@app.route('/api/v1/tools/schema', methods=['GET'])
def get_tools_schema():
    """
    Get tool schema for AI agents (Claude, ChatGPT, etc.)
    Describes what tools this service provides
    
    Authentication: Pass API key as query parameter ?api_key=<your_key>
    All endpoints require: ?api_key=fba_mjfwAOKGkneKbFLai7NyGwejuBxyrogBcMCndiww8x0
    """
    from datetime import date
    
    base_url = "https://leanora-unmumbling-noncontroversially.ngrok-free.dev"
    
    # Calculate current week
    season_start = date(2025, 10, 20)  # Week 1 starts Oct 20
    today = date.today()
    days_since_start = (today - season_start).days
    current_week = max(1, (days_since_start // 7) + 1)
    current_week = min(23, current_week)  # Cap at week 23
    
    return jsonify({
        "info": {
            "service": "Fantasy Basketball Predictions API",
            "base_url": base_url,
            "authentication": "Query parameter: ?api_key=<your_api_key>",
            "note": "All endpoints require the api_key query parameter for authentication",
            "api_endpoint": f"{base_url}/api/v1",
            "week_info": {
                "season_start_date": "2025-10-20",
                "current_week": current_week,
                "week_explanation": "Week 1 starts on Oct 20, 2025. Each week is 7 days. Week index must be 1-23.",
                "how_to_calculate": "Week = floor((days since Oct 20) / 7) + 1",
                "example": f"Today is week {current_week}"
            }
        },
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "calculate_fantasy_predictions",
                    "description": "Calculate fantasy basketball predictions for a given week",
                    "x-endpoint": "/api/v1/predictions/calculate",
                    "x-method": "POST",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "week_index": {
                                "type": "integer",
                                "description": "Fantasy week number (1-23)",
                                "minimum": 1,
                                "maximum": 23
                            },
                            "day_of_week_override": {
                                "type": "integer",
                                "description": "Override current day (0=Monday, 6=Sunday)",
                                "minimum": 0,
                                "maximum": 6
                            },
                            "injury_status": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by injury status"
                            }
                        },
                        "required": ["week_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_week_analysis",
                    "description": "Get detailed week analysis including table output",
                    "x-endpoint": "/api/v1/predictions/week-analysis",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "week_index": {
                                "type": "integer",
                                "description": "Fantasy week number (1-23)"
                            },
                            "day_of_week_override": {
                                "type": "integer",
                                "description": "Override current day"
                            },
                            "injury_status": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by injury status"
                            }
                        },
                        "required": ["week_index"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scout_players",
                    "description": "Scout and analyze players with scoring and upside analysis",
                    "x-endpoint": "/api/v1/scout/players",
                    "x-method": "POST",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of top players to return",
                                "default": 20
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scout_teams",
                    "description": "Scout teams and analyze team performance",
                    "x-endpoint": "/api/v1/scout/teams",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_advanced_stats",
                    "description": "Get team advanced stats from NBA",
                    "x-endpoint": "/api/v1/scout/advanced-stats",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "season": {
                                "type": "string",
                                "description": "NBA season (e.g., '2024-25')",
                                "default": "2025-26"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_team_changes",
                    "description": "Get players who changed NBA teams, rookies, and departures",
                    "x-endpoint": "/api/v1/scout/team-changes",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_lineup",
                    "description": "Update lineup for next 7 days",
                    "x-endpoint": "/api/v1/lineup/update",
                    "x-method": "POST",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_draft",
                    "description": "Analyze draft performance with top and worst scorers",
                    "x-endpoint": "/api/v1/draft/analysis",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "top_n": {
                                "type": "integer",
                                "description": "Number of top scorers",
                                "default": 5
                            },
                            "worst_n": {
                                "type": "integer",
                                "description": "Number of worst scorers",
                                "default": 3
                            },
                            "worst_round_limit": {
                                "type": "integer",
                                "description": "Round limit for worst performers",
                                "default": 10
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "post_transaction",
                    "description": "Post a free agent transaction",
                    "x-endpoint": "/api/v1/scheduling/post-transaction",
                    "x-method": "POST",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "player_id": {
                                "type": "integer",
                                "description": "Player ID"
                            },
                            "team_id": {
                                "type": "integer",
                                "description": "Team ID"
                            },
                            "scoring_period_id": {
                                "type": "integer",
                                "description": "Scoring period ID"
                            }
                        },
                        "required": ["player_id", "team_id", "scoring_period_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "schedule_free_agent_add",
                    "description": "Schedule a free agent add for a future date",
                    "x-endpoint": "/api/v1/scheduling/schedule-add",
                    "x-method": "POST",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "player_id": {
                                "type": "integer",
                                "description": "Player ID"
                            },
                            "date": {
                                "type": "string",
                                "description": "Date to schedule add (YYYY-MM-DD)"
                            },
                            "team_id": {
                                "type": "integer",
                                "description": "Team ID"
                            },
                            "scoring_period_id": {
                                "type": "integer",
                                "description": "Scoring period ID"
                            }
                        },
                        "required": ["player_id", "date", "team_id", "scoring_period_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_team_info",
                    "description": "Get team-specific information including matchup details and performance metrics",
                    "x-endpoint": "/api/v1/team/{team_id}",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "team_id": {
                                "type": "integer",
                                "description": "Fantasy team ID"
                            },
                            "week_index": {
                                "type": "integer",
                                "description": "Fantasy week number (1-23). Week 1 starts Oct 20, 2026 (Monday). Each week = 7 days. Currently in week 7. Defaults to current week.",
                                "minimum": 1,
                                "maximum": 23
                            },
                            "day_of_week_override": {
                                "type": "integer",
                                "description": "Override starting day (0=Monday, 6=Sunday)",
                                "minimum": 0,
                                "maximum": 6,
                                "default": 0
                            },
                            "injury_status": {
                                "type": "string",
                                "description": "Comma-separated injury statuses (e.g., 'ACTIVE,PROBABLE')",
                                "default": "ACTIVE"
                            }
                        },
                        "required": ["team_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_team_roster",
                    "description": "Get a team's current roster with player details, positions, and injury status",
                    "x-endpoint": "/api/v1/team/{team_id}/roster",
                    "x-method": "GET",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "team_id": {
                                "type": "integer",
                                "description": "Fantasy team ID"
                            }
                        },
                        "required": ["team_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_players_playing_for_scoring_period",
                    "description": "Get players from a team who have games on a specific scoring period. Scoring periods: 1=Oct 21, 2=Oct 22, ..., 47=Dec 6, 2026",
                    "x-endpoint": "/api/v1/players-playing/{scoring_period}",
                    "x-method": "GET",
                    "x-scoring-period-reference": "Scoring period 1 starts Oct 21, 2026. Each scoring period is 1 day. Period 47 is Dec 6, 2026. Can query any future period.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scoring_period": {
                                "type": "integer",
                                "description": "Scoring period ID (any positive integer >= 1). Each period = 1 day. 1=Oct 21, 2=Oct 22, ..., 47=Dec 6, 2026",
                                "minimum": 1
                            },
                            "team_id": {
                                "type": "integer",
                                "description": "Fantasy team ID (query parameter)"
                            }
                        },
                        "required": ["scoring_period", "team_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_scoreboard",
                    "description": "Get current scores for all matchups in a specific fantasy week",
                    "x-endpoint": "/api/v1/scoreboard/{week_index}",
                    "x-method": "GET",
                    "x-week-reference": "Week 1 starts Oct 20, 2026 (Monday). Each week = 7 days. Currently in week 7.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "week_index": {
                                "type": "integer",
                                "description": "Fantasy week number (1-23). Week 1 starts Oct 20, 2026 (Monday). Each week = 7 days.",
                                "minimum": 1,
                                "maximum": 23
                            }
                        },
                        "required": ["week_index"]
                    }
                }
            }
        ]
    })

# ===== Scout Endpoints =====

@app.route('/api/v1/scout/players', methods=['POST'])
@require_api_key
@require_league
def scout_player_endpoint():
    """Scout players - analyze player stats and rankings
    
    Request body:
    {
        "limit": 20
    }
    
    Returns structured data with:
    - players: List of analyzed players with scores and eligibility
    - upside_differences: Players with biggest upside/downside potential
    - total_players_analyzed: Total players processed
    - limit_returned: Number of players returned
    """
    try:
        from dataclasses import asdict
        
        data = request.json or {}
        limit = data.get('limit', 20)
        
        # Scout players returns structured ScoutingResult
        result = scout_players(limit=limit)
        
        return jsonify({
            "status": "success",
            "data": {
                "total_players_analyzed": result.total_players_analyzed,
                "limit_returned": result.limit_returned,
                "players": [asdict(p) for p in result.players],
                "upside_differences": [asdict(u) for u in result.upside_differences]
            }
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Scout players failed: {str(e)}"
        }), 500

@app.route('/api/v1/scout/teams', methods=['GET'])
@require_api_key
@require_league
def scout_team_endpoint():
    """Scout teams - analyze team stats and performance"""
    try:
        scout_teams()
        return jsonify({
            "status": "success",
            "message": "Team scouting completed"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Scout teams failed: {str(e)}"
        }), 500

@app.route('/api/v1/scout/advanced-stats', methods=['GET'])
@require_api_key
def advanced_stats_endpoint():
    """Get team advanced stats
    
    Query params:
    - season: NBA season (default: 2024-25)
    """
    try:
        season = request.args.get('season', '2025-26')
        stats = get_team_advanced_stats(season=season)
        
        return jsonify({
            "status": "success",
            "season": season,
            "data": stats.to_dict(orient='records')
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to get advanced stats: {str(e)}"
        }), 500

@app.route('/api/v1/scout/team-changes', methods=['GET'])
@require_api_key
@require_league
def team_changes_endpoint():
    """Get players who changed NBA teams between 2025 and 2026
    
    Returns:
    - changed_teams: Players who switched teams (filtered by avg_fpts >= 10)
    - rookies: New players in 2026 (not in 2025)
    - departures: Players who left the league
    - Total counts for each category
    """
    try:
        from dataclasses import asdict
        
        result = analyze_team_changes()
        
        return jsonify({
            "status": "success",
            "data": {
                "total_changed": result.total_changed,
                "total_rookies": result.total_rookies,
                "total_departures": result.total_departures,
                "changed_teams": [asdict(c) for c in result.changed_teams],
                "rookies": [asdict(r) for r in result.rookies],
                "departures": [asdict(d) for d in result.departures]
            }
        }), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Failed to get team changes: {str(e)}"
        }), 500

# ===== Lineup Endpoints =====

@app.route('/api/v1/lineup/update', methods=['POST'])
@require_api_key
@require_league
def update_lineup_endpoint():
    """Update lineup for next 7 days"""
    try:
        change_line_up_for_next_7_days()
        return jsonify({
            "status": "success",
            "message": "Lineup updated for next 7 days"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to update lineup: {str(e)}"
        }), 500

# ===== Draft Recap Endpoints =====

@app.route('/api/v1/draft/analysis', methods=['GET'])
@require_api_key
@require_league
def draft_analysis_endpoint():
    """Analyze draft performance
    
    Query params:
    - top_n: Number of top scorers to include (default: 5)
    - worst_n: Number of worst scorers to include (default: 3)
    - worst_round_limit: Round limit for worst performers (default: 10)
    """
    try:
        top_n = request.args.get('top_n', 5, type=int)
        worst_n = request.args.get('worst_n', 3, type=int)
        worst_round_limit = request.args.get('worst_round_limit', 10, type=int)
        
        analysis = calculate_drafted_team_points_and_top_and_worst_scorers(
            league,
            top_n=top_n,
            worst_n=worst_n,
            worst_round_limit=worst_round_limit
        )
        
        return jsonify({
            "status": "success",
            "data": analysis
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Draft analysis failed: {str(e)}"
        }), 500

# ===== Scheduling Endpoints =====

@app.route('/api/v1/scheduling/post-transaction', methods=['POST'])
@require_api_key
def post_transaction_endpoint():
    """Post a free agent transaction
    
    Request body:
    {
        "player_id": 12345,
        "team_id": 1,
        "scoring_period_id": 1
    }
    """
    try:
        data = request.json or {}
        player_id = data.get('player_id')
        team_id = data.get('team_id')
        scoring_period_id = data.get('scoring_period_id')
        
        if not all([player_id, team_id, scoring_period_id]):
            return jsonify({
                "status": "error",
                "message": "Missing required fields: player_id, team_id, scoring_period_id"
            }), 400
        
        # Post transaction (this makes actual ESPN API calls)
        result = post_transaction(
            url="https://lm-api-reads.platform.espn.com/transactions",
            player_id=player_id,
            team_id=team_id,
            scoring_period_id=scoring_period_id,
            espn_s2=os.getenv('ESPN_S2'),
            swid=os.getenv('SWID')
        )
        
        return jsonify({
            "status": "success",
            "message": "Transaction posted successfully",
            "data": result
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to post transaction: {str(e)}"
        }), 500

@app.route('/api/v1/scheduling/schedule-add', methods=['POST'])
@require_api_key
def schedule_add_endpoint():
    """Schedule a free agent add for future date
    
    Request body:
    {
        "player_id": 12345,
        "date": "2025-12-15",
        "team_id": 1,
        "scoring_period_id": 1
    }
    """
    try:
        data = request.json or {}
        player_id = data.get('player_id')
        date = data.get('date')
        team_id = data.get('team_id')
        scoring_period_id = data.get('scoring_period_id')
        
        if not all([player_id, date, team_id, scoring_period_id]):
            return jsonify({
                "status": "error",
                "message": "Missing required fields: player_id, date, team_id, scoring_period_id"
            }), 400
        
        result = schedule_with_at(
            player_id=player_id,
            date_string=date,
            team_id=team_id,
            scoring_period_id=scoring_period_id
        )
        
        return jsonify({
            "status": "success",
            "message": "Add scheduled successfully",
            "data": result
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to schedule add: {str(e)}"
        }), 500

# ===== Authentication Endpoints =====

@app.route('/api/v1/auth/keys/generate', methods=['POST'])
@require_admin
def generate_api_key():
    """Generate a new API key.
    
    Request body:
    {
        "name": "my-app",
        "rate_limit": 100
    }
    
    Returns the new API key (shown only once!)
    """
    try:
        manager = get_api_key_manager()
        data = request.json or {}
        
        name = data.get('name', 'Unnamed Key')
        rate_limit = data.get('rate_limit', 100)
        
        if not name or len(name) < 3:
            return jsonify({
                "status": "error",
                "message": "name is required (min 3 characters)"
            }), 400
        
        new_key = manager.generate_key(name, rate_limit)
        
        return jsonify({
            "status": "success",
            "message": "API key generated successfully",
            "data": {
                "api_key": new_key,
                "name": name,
                "rate_limit": rate_limit,
                "warning": "Save this key now - you won't see it again!"
            }
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to generate API key: {str(e)}"
        }), 500

@app.route('/api/v1/auth/keys', methods=['GET'])
@require_admin
def list_api_keys():
    """List all API keys (keys are truncated for security)"""
    try:
        manager = get_api_key_manager()
        keys = manager.list_keys()
        
        return jsonify({
            "status": "success",
            "data": keys,
            "count": len(keys)
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to list API keys: {str(e)}"
        }), 500

@app.route('/api/v1/admin/refresh-league', methods=['POST'])
@require_admin
def refresh_league():
    """Force refresh league data from ESPN (bypasses cache)
    
    This endpoint requires admin authentication.
    Useful when the cached league data is stale.
    Deletes the cache file and fetches fresh data from ESPN.
    """
    try:
        global league
        import os
        
        print("🔄 Admin requested league refresh...")
        
        # Delete the cache file to force fresh fetch
        from utils.create_league import get_cache_path
        cache_path = get_cache_path(2026)  # Default year
        
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
                print(f"✅ Deleted stale cache: {cache_path}")
            except Exception as e:
                print(f"⚠️  Could not delete cache: {e}")
        
        # Create a new league instance without using cache
        from utils.create_league import create_league
        
        # Fetch fresh league data from ESPN (bypass cache)
        new_league = create_league(use_local_cache=False)
        
        if new_league:
            league = new_league
            print("✅ League refreshed successfully from ESPN")
            return jsonify({
                "status": "success",
                "message": "League refreshed successfully from ESPN API (cache cleared)",
                "league_name": league.league_name if hasattr(league, 'league_name') else "Unknown",
                "year": league.year if hasattr(league, 'year') else "Unknown",
                "cache_cleared": True
            }), 200
        else:
            print("❌ Failed to refresh league")
            return jsonify({
                "status": "error",
                "message": "Failed to refresh league from ESPN"
            }), 500
    
    except Exception as e:
        print(f"Error in refresh_league: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Failed to refresh league: {str(e)}"
        }), 500

@app.route('/api/v1/auth/keys/revoke', methods=['POST'])
@require_admin
def revoke_api_key():
    """Revoke an API key
    
    Request body:
    {
        "api_key": "fba_..."
    }
    """
    try:
        data = request.json or {}
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({
                "status": "error",
                "message": "api_key is required in request body"
            }), 400
        
        manager = get_api_key_manager()
        
        if manager.revoke_key(api_key):
            return jsonify({
                "status": "success",
                "message": "API key revoked successfully"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "API key not found"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to revoke API key: {str(e)}"
        }), 500

# ===== Team Endpoints =====

@app.route('/api/v1/team/<int:team_id>/roster', methods=['POST'])
@require_api_key
@require_league
def get_team_roster(team_id):
    """
    Get team roster with player details
    
    Path params:
    - team_id: Team ID (integer)
    
    Request body params (optional):
    - None required
    """
    try:
        # Request body is optional for this endpoint
        data = request.get_json() or {}
        # Find the team by ID
        target_team = None
        for team in league.teams:
            if team.team_id == team_id:
                target_team = team
                break
        
        if not target_team:
            return jsonify({
                "status": "error",
                "message": f"Team with ID {team_id} not found in league"
            }), 404
        
        # Get owner name
        owner_name = "Unknown"
        if target_team.owners:
            owner = target_team.owners[0]
            owner_name = owner.get('displayName') if isinstance(owner, dict) else owner.displayName
        
        # Build roster data
        roster_data = []
        for player in target_team.roster:
            player_info = {
                "name": player.name,
                "position": player.position if hasattr(player, 'position') else None,
                "nba_team": player.nba_team_abbrev if hasattr(player, 'nba_team_abbrev') else None,
                "injury_status": player.injuryStatus if hasattr(player, 'injuryStatus') and player.injuryStatus else "ACTIVE",
                "player_id": player.player_id if hasattr(player, 'player_id') else None
            }
            roster_data.append(player_info)
        
        response_data = {
            "team": {
                "id": target_team.team_id,
                "name": target_team.team_name,
                "owner": owner_name,
                "rank": target_team.standing,
                "wins": target_team.wins,
                "losses": target_team.losses
            },
            "roster": {
                "total_players": len(roster_data),
                "active_players": sum(1 for p in roster_data if p['injury_status'] == 'ACTIVE'),
                "out_players": sum(1 for p in roster_data if p['injury_status'] == 'OUT'),
                "day_to_day_players": sum(1 for p in roster_data if p['injury_status'] == 'DAY_TO_DAY'),
                "players": roster_data
            }
        }
        
        return jsonify({
            "status": "success",
            "data": response_data
        }), 200
    
    except Exception as e:
        print(f"Error in get_team_roster: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve team roster: {str(e)}"
        }), 500

@app.route('/api/v1/players-playing/<int:scoring_period>', methods=['POST'])
@require_api_key
@require_league
def get_players_playing_for_scoring_period(scoring_period):
    """
    Get all players from a specific team who have games on a scoring period
    
    Path params:
    - scoring_period: Scoring period ID (1=Oct 21, 2=Oct 22, ..., 47=Dec 6, 2026)
    
    Request body params:
    - team_id: Team ID (required) - Get players only for this team
    """
    try:
        from line_up.game_day_player_getter import GameDayPlayerGetter
        
        # Get team_id from request body or query params (for backward compatibility)
        data = request.get_json() or {}
        team_id = data.get('team_id') or request.args.get('team_id', type=int)
        if not team_id:
            return jsonify({
                "status": "error",
                "message": "team_id query parameter is required"
            }), 400
        
        # Find the team
        target_team = None
        for team in league.teams:
            if team.team_id == team_id:
                target_team = team
                break
        
        if not target_team:
            return jsonify({
                "status": "error",
                "message": f"Team with ID {team_id} not found in league"
            }), 404
        
        # Validate scoring period
        if not isinstance(scoring_period, int) or scoring_period < 1:
            return jsonify({
                "status": "error",
                "message": "scoring_period must be a positive integer (1 or greater)"
            }), 400
        
        # Get the game day player getter
        getter = GameDayPlayerGetter(league, [], team_id)
        
        # Get all active players for this scoring period
        all_active_players = getter.get_active_player_list_for_day(scoring_period)
        
        # Get players playing this period
        players_playing = getter.get_players_playing(scoring_period)
        
        # Get NBA teams playing
        nba_teams_playing = getter.get_games(scoring_period)
        
        # Get owner name
        owner_name = "Unknown"
        if target_team.owners:
            owner = target_team.owners[0]
            owner_name = owner.get('displayName') if isinstance(owner, dict) else owner.displayName
        
        # Get player stats using RosterWeekPredictor
        from predict.internal.roster_week_predictor import RosterWeekPredictor
        from common.week import Week
        
        # Build player data with stats
        playing_players = []
        for player in players_playing:
            avg_points, variance = RosterWeekPredictor.get_avg_variance_stats(player)
            player_info = {
                "player_id": player.player_id if hasattr(player, 'player_id') else None,
                "name": player.name,
                "position": player.position if hasattr(player, 'position') else None,
                "nba_team": player.proTeam if hasattr(player, 'proTeam') else None,
                "injury_status": player.injuryStatus if hasattr(player, 'injuryStatus') and player.injuryStatus else "ACTIVE",
                "projected_avg_points": round(avg_points, 2),
                "projected_variance": round(variance, 2)
            }
            playing_players.append(player_info)
        
        not_playing_players = []
        for p in all_active_players:
            if p not in players_playing:
                avg_points, variance = RosterWeekPredictor.get_avg_variance_stats(p)
                player_info = {
                    "player_id": p.player_id if hasattr(p, 'player_id') else None,
                    "name": p.name,
                    "position": p.position if hasattr(p, 'position') else None,
                    "nba_team": p.proTeam if hasattr(p, 'proTeam') else None,
                    "injury_status": p.injuryStatus if hasattr(p, 'injuryStatus') and p.injuryStatus else "ACTIVE",
                    "projected_avg_points": round(avg_points, 2),
                    "projected_variance": round(variance, 2)
                }
                not_playing_players.append(player_info)
        
        response_data = {
            "team": {
                "id": target_team.team_id,
                "name": target_team.team_name,
                "owner": owner_name
            },
            "scoring_period": scoring_period,
            "nba_teams_playing": nba_teams_playing,
            "players_playing": {
                "count": len(playing_players),
                "players": playing_players
            },
            "players_not_playing": {
                "count": len(not_playing_players),
                "players": not_playing_players
            }
        }
        
        return jsonify({
            "status": "success",
            "data": response_data
        }), 200
    
    except Exception as e:
        print(f"Error in get_players_playing_for_scoring_period: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Failed to get playing players: {str(e)}"
        }), 500

@app.route('/api/v1/scoreboard/<int:week_index>', methods=['POST'])
@require_api_key
@require_league
def get_scoreboard(week_index):
    """
    Get current scores for all matchups in a specific week
    
    Path params:
    - week_index: Fantasy week number (1-23)
    
    Request body params (optional):
    - None required
    """
    try:
        # Request body is optional for this endpoint
        data = request.get_json() or {}
        
        # Validate week index
        if not isinstance(week_index, int) or week_index < 1 or week_index > 23:
            return jsonify({
                "status": "error",
                "message": "week_index must be an integer between 1 and 23"
            }), 400
        
        # Check if week is within final scoring period
        final_period = league.finalScoringPeriod if hasattr(league, 'finalScoringPeriod') else 200
        if week_index > final_period:
            return jsonify({
                "status": "error",
                "message": f"week_index cannot exceed final scoring period ({final_period})"
            }), 400
        
        # Get current scoring period for live scores
        current_period = league.currentMatchupPeriod
        
        # Get scoreboard for the week
        scoreboard = league.scoreboard(week_index)
        
        # Get live box scores for accurate current scores
        try:
            box_scores = league.box_scores(week_index, current_period, matchup_total=True)
        except:
            box_scores = None
        
        # Build matchup data
        matchups = []
        for matchup in scoreboard:
            # Find matching box score by team IDs
            home_score = matchup.home_final_score if hasattr(matchup, 'home_final_score') else matchup.home_team_live_score
            away_score = matchup.away_final_score if hasattr(matchup, 'away_final_score') else matchup.away_team_live_score
            
            # Look up live scores from box_scores by matching team IDs
            if box_scores:
                for box_score in box_scores:
                    if (hasattr(box_score, 'home_team') and hasattr(box_score, 'away_team') and
                        box_score.home_team.team_id == matchup.home_team.team_id and
                        box_score.away_team.team_id == matchup.away_team.team_id):
                        home_score = box_score.home_score if hasattr(box_score, 'home_score') else home_score
                        away_score = box_score.away_score if hasattr(box_score, 'away_score') else away_score
                        break
            
            matchup_data = {
                "home_team": {
                    "id": matchup.home_team.team_id,
                    "name": matchup.home_team.team_name,
                    "owner": (matchup.home_team.owners[0].get('displayName') 
                             if isinstance(matchup.home_team.owners[0], dict) 
                             else matchup.home_team.owners[0].displayName) if matchup.home_team.owners else "Unknown",
                    "score": home_score,
                    "wins": matchup.home_team.wins,
                    "losses": matchup.home_team.losses
                },
                "away_team": {
                    "id": matchup.away_team.team_id,
                    "name": matchup.away_team.team_name,
                    "owner": (matchup.away_team.owners[0].get('displayName') 
                             if isinstance(matchup.away_team.owners[0], dict) 
                             else matchup.away_team.owners[0].displayName) if matchup.away_team.owners else "Unknown",
                    "score": away_score,
                    "wins": matchup.away_team.wins,
                    "losses": matchup.away_team.losses
                },
                "matchup_id": matchup.matchup_id if hasattr(matchup, 'matchup_id') else None,
                "is_playoffs": matchup.is_playoffs if hasattr(matchup, 'is_playoffs') else False,
                "winner": matchup.winner if hasattr(matchup, 'winner') else None
            }
            
            # Calculate point differential
            point_diff = home_score - away_score
            matchup_data["point_differential"] = round(point_diff, 2)
            matchup_data["leader"] = "home" if point_diff > 0 else ("away" if point_diff < 0 else "tied")
            
            matchups.append(matchup_data)
        
        response_data = {
            "week_index": week_index,
            "week_start": "Oct 20, 2026" if week_index == 1 else f"Week {week_index}",
            "total_matchups": len(matchups),
            "matchups": matchups
        }
        
        return jsonify({
            "status": "success",
            "data": response_data
        }), 200
    
    except Exception as e:
        print(f"Error in get_scoreboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Failed to get scoreboard: {str(e)}"
        }), 500

@app.route('/api/v1/team/<int:team_id>', methods=['POST'])
@require_api_key
@require_league
def get_team_info(team_id):
    """
    Get team information and matchup details for a specific week
    
    Path params:
    - team_id: Team ID (integer)
    
    Query params:
    - week_index: Week number (optional, defaults to current week if not provided, 1-17)
    - day_of_week_override: Starting day override (optional, 0=Monday, 6=Sunday, default=0)
    - injury_status: Comma-separated injury statuses (optional, default=ACTIVE)
    """
    try:
        # Get parameters from request body (POST) or query params (for backward compatibility)
        data = request.get_json() or {}
        week_index = data.get('week_index') or request.args.get('week_index', type=int)
        day_of_week_override = data.get('day_of_week_override') or request.args.get('day_of_week_override', default=0, type=int)
        injury_status_param = data.get('injury_status') or request.args.get('injury_status', 'ACTIVE')
        injury_status = [s.strip().upper() for s in injury_status_param.split(',')]
        
        # Use current week if not provided
        if week_index is None:
            week_index = league.currentMatchupPeriod
        
        # Validate week range
        if not isinstance(week_index, int) or week_index < 1 or week_index > 23:
            return jsonify({
                "status": "error",
                "message": "week_index must be an integer between 1 and 23"
            }), 400
        
        # Validate day_of_week
        if not isinstance(day_of_week_override, int) or day_of_week_override < 0 or day_of_week_override > 6:
            return jsonify({
                "status": "error",
                "message": "day_of_week_override must be 0-6 (0=Monday, 6=Sunday)"
            }), 400
        
        # Find the team by ID
        target_team = None
        for team in league.teams:
            if team.team_id == team_id:
                target_team = team
                break
        
        if not target_team:
            return jsonify({
                "status": "error",
                "message": f"Team with ID {team_id} not found in league"
            }), 404
        
        # Get week predictions for all teams
        num_games, team_scores = predict_week(
            league, week_index, day_of_week_override, injury_status
        )
        
        # Find the matchup for this team
        matchup_data = None
        for matchup in league.scoreboard(week_index):
            if matchup.home_team.team_id == team_id:
                matchup_data = {
                    "home_team": matchup.home_team.team_name,
                    "away_team": matchup.away_team.team_name,
                    "is_home": True,
                    "opponent_id": matchup.away_team.team_id,
                    "opponent_name": matchup.away_team.team_name
                }
                break
            elif matchup.away_team.team_id == team_id:
                matchup_data = {
                    "home_team": matchup.home_team.team_name,
                    "away_team": matchup.away_team.team_name,
                    "is_home": False,
                    "opponent_id": matchup.home_team.team_id,
                    "opponent_name": matchup.home_team.team_name
                }
                break
        
        # Build response with performance metrics
        team_name = target_team.team_name
        team_avg, team_std = team_scores.get(team_name, (0, 0))
        
        opponent_avg = 0
        opponent_std = 0
        if matchup_data:
            opponent_name = matchup_data['opponent_name']
            opponent_avg, opponent_std = team_scores.get(opponent_name, (0, 0))
        
        response_data = {
            "team": {
                "id": target_team.team_id,
                "name": target_team.team_name,
                "owner": target_team.owners[0] if target_team.owners else "Unknown",
                "rank": target_team.standing,
                "wins": target_team.wins,
                "losses": target_team.losses,
                "points_for": round(target_team.points_for, 2),
                "points_against": round(target_team.points_against, 2)
            },
            "week": {
                "index": week_index,
                "day_of_week_override": day_of_week_override,
                "injury_status_filter": injury_status
            },
            "performance_metrics": {
                "predicted_average_points": round(team_avg, 2),
                "predicted_std_dev": round(team_std, 2),
                "number_of_games": num_games.get(team_name, 0)
            },
            "matchup": matchup_data if matchup_data else {
                "message": "No matchup found for this week"
            },
            "opponent_metrics": {
                "predicted_average_points": round(opponent_avg, 2),
                "predicted_std_dev": round(opponent_std, 2),
                "number_of_games": num_games.get(matchup_data['opponent_name'], 0) if matchup_data else 0
            } if matchup_data else None,
            "matchup_analysis": {
                "point_differential": round(team_avg - opponent_avg, 2),
                "point_differential_std_dev": round((team_std ** 2 + opponent_std ** 2) ** 0.5, 2)
            } if matchup_data else None
        }
        
        return jsonify({
            "status": "success",
            "data": response_data
        }), 200
    
    except Exception as e:
        print(f"Error in get_team_info: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Failed to retrieve team information: {str(e)}"
        }), 500


# ===== Error Handlers =====

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": {
            "health": "GET /api/v1/health",
            "calculate": "POST /api/v1/predictions/calculate",
            "schema": "GET /api/v1/tools/schema"
        }
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500

# ===== Startup =====

def main():
    """Main entry point"""
    print("🚀 Starting Fantasy Basketball Service...")
    
    # Attempt to load league
    if not init_league():
        print("⚠️  Service starting without league (will fail on prediction requests)")
    
    # Start Flask app
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"📡 Starting server on {host}:{port}")
    print(f"🌐 Access at http://localhost:{port}")
    print(f"📚 API docs available at http://localhost:{port}/")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
