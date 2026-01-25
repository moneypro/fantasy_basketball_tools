# Matchup Prediction Endpoint

## Overview

The **Current Matchup Prediction** endpoint provides comprehensive matchup analysis with predicted scores, remaining days, and player game schedules for a specific fantasy basketball matchup.

## Endpoint

```
POST /api/v1/matchup/current-prediction
```

**Authentication**: Requires API key (query parameter or Bearer token)

---

## Features

1. **Predicted Scores**: Mean and standard deviation for both teams
2. **Remaining Days**: Shows how many days are left in the matchup week
3. **Date Translation**: Accepts dates (YYYY-MM-DD) or matchup week numbers
4. **Players Playing**: Lists all players with games, including game counts
5. **Daily Predictions**: Remaining days cumulative score predictions
6. **Injury Status Filtering**: Filter predictions by player injury status

---

## Request Parameters

All parameters are optional and sent in the request body as JSON:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `week_index` | integer | Current week | Matchup week number (1-23) |
| `date` | string | - | Date in YYYY-MM-DD format (alternative to week_index) |
| `team_id` | integer | First matchup | Team ID to get matchup for |
| `day_of_week_override` | integer | 0 | Starting day (0=Monday, 6=Sunday) |
| `injury_status` | array | `['ACTIVE']` | Injury statuses to include |

### Injury Status Options

- `ACTIVE` - Healthy players only
- `DAY_TO_DAY` - Include day-to-day players
- `OUT` - Include players listed as out
- `QUESTIONABLE` - Include questionable players

---

## Request Examples

### 1. Get Current Week Matchup (Default)

```bash
curl -X POST "https://hcheng.ngrok.app/api/v1/matchup/current-prediction?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 2. Get Specific Week by Number

```bash
curl -X POST "https://hcheng.ngrok.app/api/v1/matchup/current-prediction?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "week_index": 5
  }'
```

### 3. Get Matchup by Date

```bash
curl -X POST "https://hcheng.ngrok.app/api/v1/matchup/current-prediction?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024-11-20"
  }'
```

### 4. Get Specific Team's Matchup

```bash
curl -X POST "https://hcheng.ngrok.app/api/v1/matchup/current-prediction?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "week_index": 5,
    "team_id": 1
  }'
```

### 5. Include Day-to-Day Players

```bash
curl -X POST "https://hcheng.ngrok.app/api/v1/matchup/current-prediction?api_key=YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "week_index": 5,
    "injury_status": ["ACTIVE", "DAY_TO_DAY"]
  }'
```

---

## Response Format

### Success Response (200 OK)

```json
{
  "status": "success",
  "data": {
    "week_index": 5,
    "date_range": {
      "start_date": "2024-11-19",
      "end_date": "2024-11-25",
      "remaining_days": 3
    },
    "matchup": {
      "home_team": {
        "id": 1,
        "name": "Team Alpha",
        "owner": "John Doe",
        "current_score": 450.5,
        "predicted_score": {
          "mean": 892.45,
          "std_dev": 45.23
        },
        "total_games": 42,
        "players_playing": [
          {
            "name": "LeBron James",
            "position": "SF",
            "pro_team": "Lakers",
            "injury_status": "ACTIVE",
            "games_this_week": 4,
            "game_days": [0, 2, 4, 6]
          },
          {
            "name": "Stephen Curry",
            "position": "PG",
            "pro_team": "Warriors",
            "injury_status": "ACTIVE",
            "games_this_week": 3,
            "game_days": [1, 3, 5]
          }
        ],
        "remaining_days_predictions": [
          {
            "day": 0,
            "mean": 892.45,
            "std_dev": 45.23
          },
          {
            "day": 1,
            "mean": 650.30,
            "std_dev": 38.50
          },
          {
            "day": 2,
            "mean": 420.15,
            "std_dev": 28.75
          }
        ]
      },
      "away_team": {
        "id": 2,
        "name": "Team Beta",
        "owner": "Jane Smith",
        "current_score": 435.0,
        "predicted_score": {
          "mean": 875.20,
          "std_dev": 42.10
        },
        "total_games": 40,
        "players_playing": [
          {
            "name": "Kevin Durant",
            "position": "SF",
            "pro_team": "Suns",
            "injury_status": "ACTIVE",
            "games_this_week": 4,
            "game_days": [0, 2, 4, 6]
          }
        ],
        "remaining_days_predictions": [
          {
            "day": 0,
            "mean": 875.20,
            "std_dev": 42.10
          },
          {
            "day": 1,
            "mean": 630.50,
            "std_dev": 35.20
          }
        ]
      },
      "predicted_margin": 17.25,
      "predicted_winner": "Team Alpha"
    },
    "injury_status_filter": ["ACTIVE"]
  }
}
```

### Error Response (400 Bad Request)

```json
{
  "status": "error",
  "message": "week_index must be an integer between 1 and 23"
}
```

### Error Response (404 Not Found)

```json
{
  "status": "error",
  "message": "Team 5 not found in week 5 matchups"
}
```

---

## Response Fields Explained

### Date Range
- `start_date`: First day of the matchup week (YYYY-MM-DD)
- `end_date`: Last day of the matchup week (YYYY-MM-DD)
- `remaining_days`: Number of days left in the week (0 if week is over)

### Team Data
- `id`: Team ID in the league
- `name`: Team name
- `owner`: Team owner's display name
- `current_score`: Current actual score for the week
- `predicted_score.mean`: Average predicted total score
- `predicted_score.std_dev`: Standard deviation of prediction
- `total_games`: Total number of NBA games for this team this week

### Players Playing
- `name`: Player name
- `position`: Fantasy position (PG, SG, SF, PF, C)
- `pro_team`: NBA team name
- `injury_status`: Current injury status
- `games_this_week`: Total games this player has this week
- `game_days`: Array of day indices when player has games (0=Monday, 6=Sunday)

### Remaining Days Predictions
- `day`: Day index (0=start of week, 6=end of week)
- `mean`: Predicted cumulative score from this day through end of week
- `std_dev`: Standard deviation of the prediction

### Matchup Summary
- `predicted_margin`: Difference in predicted scores (positive = home team ahead)
- `predicted_winner`: Name of team predicted to win

---

## Date and Period Conversion

The endpoint automatically converts between dates and matchup periods:

### Season Information
- **Season**: 2024-25 NBA Season
- **Season Start**: October 22, 2024
- **Scoring Period 1**: October 22, 2024
- **Each Scoring Period**: Represents one calendar day

### Matchup Week to Date Mapping

| Week | Start Date | End Date | Scoring Periods |
|------|------------|----------|-----------------|
| 1 | 2024-10-22 | 2024-10-29 | 1-8 |
| 2 | 2024-10-29 | 2024-11-04 | 8-14 |
| 3 | 2024-11-05 | 2024-11-11 | 15-21 |
| 4 | 2024-11-12 | 2024-11-18 | 22-28 |
| 5 | 2024-11-19 | 2024-11-25 | 29-35 |
| ... | ... | ... | ... |

---

## Use Cases

### 1. Pre-Week Planning
Get predictions before the week starts to plan your lineup:
```bash
# Check next week's matchup
curl -X POST ".../matchup/current-prediction?api_key=KEY" \
  -d '{"week_index": 6}'
```

### 2. In-Week Monitoring
Track your matchup progress and remaining potential:
```bash
# See remaining days and predictions
curl -X POST ".../matchup/current-prediction?api_key=KEY" \
  -d '{}'
```

### 3. Waiver Wire Planning
Identify which players have games remaining:
```bash
# Check players playing and game counts
curl -X POST ".../matchup/current-prediction?api_key=KEY" \
  -d '{"week_index": 5, "team_id": 1}'
```

### 4. Risk Analysis
Include questionable players to see upside/downside:
```bash
# Include DTD players to see potential
curl -X POST ".../matchup/current-prediction?api_key=KEY" \
  -d '{"injury_status": ["ACTIVE", "DAY_TO_DAY"]}'
```

---

## Integration with Other Endpoints

This endpoint complements existing endpoints:

1. **Week Analysis** (`/api/v1/predictions/week-analysis`): Get league-wide predictions
2. **Scoreboard** (`/api/v1/scoreboard/{week_index}`): Get current scores
3. **Team Roster** (`/api/v1/team/{team_id}/roster`): Get detailed roster info
4. **Players Playing** (`/api/v1/players-playing/{scoring_period}`): Get players for specific day

### Example Workflow

```bash
# 1. Get current matchup prediction
MATCHUP=$(curl -X POST ".../matchup/current-prediction?api_key=KEY" -d '{}')

# 2. Get specific day's players
curl -X POST ".../players-playing/50?api_key=KEY" \
  -d '{"team_id": 1}'

# 3. Get updated scoreboard
curl -X POST ".../scoreboard/5?api_key=KEY" -d '{}'
```

---

## Notes

- **Caching**: League data is cached for performance
- **Prediction Accuracy**: Based on projected stats and historical variance
- **Injury Updates**: Refresh league data to get latest injury information
- **Time Zones**: All dates are in local time (season starts Oct 22, 2024)

---

## Errors and Troubleshooting

### Common Errors

1. **"League not initialized"** (503)
   - ESPN credentials not configured
   - Check environment variables

2. **"week_index must be between 1 and 23"** (400)
   - Invalid week number provided
   - Check your week_index parameter

3. **"Team X not found in week Y matchups"** (404)
   - Team ID doesn't exist or has a bye week
   - Verify team ID and week number

4. **"Invalid date"** (400)
   - Date format incorrect (must be YYYY-MM-DD)
   - Date is before season start

---

## Version History

- **v1.0.0** (2026-01-24): Initial release
  - Matchup predictions with scores
  - Remaining days calculation
  - Date/period translation
  - Player game listings
  - Daily cumulative predictions

---

**Last Updated**: January 24, 2026
