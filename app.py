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

# Initialize Flask app
app = Flask(__name__)

# Global league instance (loaded once at startup)
league = None

def init_league():
    """Initialize league from environment variables"""
    global league
    try:
        league = create_league()
        print("✅ League loaded successfully")
        return True
    except Exception as e:
        print(f"⚠️  Warning: Could not load league: {e}")
        return False

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
            "week_analysis": "POST /api/v1/predictions/week-analysis"
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
                "message": "week_index is required (integer, 1-17)"
            }), 400
        
        # Validate week range
        if not isinstance(week_index, int) or week_index < 1 or week_index > 17:
            return jsonify({
                "status": "error",
                "message": "week_index must be an integer between 1 and 17"
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
@require_league
def week_analysis():
    """
    Get detailed week analysis including table output
    
    Request body:
    {
        "week_index": 1,
        "day_of_week_override": 0,
        "injury_status": ["ACTIVE"]
    }
    """
    try:
        data = request.json or {}
        week_index = data.get('week_index')
        
        if not week_index:
            return jsonify({
                "status": "error",
                "message": "week_index is required"
            }), 400
        
        day_of_week = data.get('day_of_week_override', 0)
        injury_status = data.get('injury_status', ['ACTIVE'])
        
        # Get table output
        table_output = get_table_output_for_week(
            league, week_index, day_of_week, injury_status
        )
        
        return jsonify({
            "status": "success",
            "data": {
                "week_index": week_index,
                "table_output": table_output
            }
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
    """
    return jsonify({
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "calculate_fantasy_predictions",
                    "description": "Calculate fantasy basketball predictions for a given week. Returns team scores, remaining days analysis, and game counts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "week_index": {
                                "type": "integer",
                                "description": "Fantasy week number (1-17)",
                                "minimum": 1,
                                "maximum": 17
                            },
                            "day_of_week_override": {
                                "type": "integer",
                                "description": "Override current day (0=Monday, 6=Sunday)",
                                "minimum": 0,
                                "maximum": 6,
                                "default": 0
                            },
                            "injury_status": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter players by injury status: ACTIVE, DAY_TO_DAY, OUT, etc.",
                                "default": ["ACTIVE"]
                            }
                        },
                        "required": ["week_index"]
                    }
                }
            }
        ]
    })

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
