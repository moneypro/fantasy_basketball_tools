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
            "team_info": "GET /api/v1/team/{team_id}"
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

@app.route('/api/v1/predictions/week-analysis', methods=['GET'])
@require_api_key
@require_league
def week_analysis():
    """
    Get detailed week analysis with HTML tables for all injury statuses
    
    Query params:
    - week_index: Week number (required, 1-17)
    """
    try:
        from predict.predict_week import build_week_json
        
        data = request.args.to_dict()
        week_index = int(data.get('week_index', 0)) if data.get('week_index') else None
        
        if not week_index:
            return jsonify({
                "status": "error",
                "message": "week_index is required"
            }), 400
        
        # day_of_week_override is always 0 for current analysis
        day_of_week_override = 0
        
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
                                "description": "Fantasy week number (1-23), defaults to current week",
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

@app.route('/api/v1/team/<int:team_id>', methods=['GET'])
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
        # Get query parameters
        week_index = request.args.get('week_index', type=int)
        day_of_week_override = request.args.get('day_of_week_override', default=0, type=int)
        injury_status_param = request.args.get('injury_status', 'ACTIVE')
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
