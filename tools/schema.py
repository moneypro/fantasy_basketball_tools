"""AI Agent Tools Schema - Defines available tools and endpoints for AI integration"""

from datetime import date


def get_tools_schema():
    """
    Generate tool schema for AI agents (Claude, ChatGPT, etc.)
    Describes what tools this service provides and how to call them.
    
    Returns:
        dict: Complete tool schema with all available endpoints and parameters
    """
    base_url = "https://hcheng.ngrok.app"
    
    # Calculate current week
    season_start = date(2025, 10, 20)  # Week 1 starts Oct 20
    today = date.today()
    days_since_start = (today - season_start).days
    current_week = max(1, (days_since_start // 7) + 1)
    current_week = min(23, current_week)  # Cap at week 23
    
    return {
        "info": {
            "service": "Fantasy Basketball Predictions API",
            "base_url": base_url,
            "authentication": "Query parameter: ?api_key=<your_api_key>",
            "note": "All endpoints require the api_key query parameter for authentication",
            "api_endpoint": f"{base_url}/api/v1",
            "week_info": {
                "season_start_date": "2025-10-20",
                "current_week": current_week,
                "week_explanation": "Week 1 starts on Oct 20, 2025 (Monday). Each week is 7 days. Week index must be 1-23.",
                "how_to_calculate": "Week = floor((days since Oct 20) / 7) + 1",
                "example": f"Today is week {current_week}",
                "scoring_period_clarification": "Scoring periods are different from weeks. Scoring period 1 = Oct 21, 2025 (Tuesday). Each scoring period = 1 day."
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
    }
