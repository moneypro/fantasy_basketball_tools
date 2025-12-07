# Team Information Endpoint

## Overview
The new team endpoint provides detailed performance metrics and matchup information for a specific fantasy basketball team.

## Endpoint

```
GET /api/v1/team/{team_id}
```

## Authentication
All requests require an API key:
```
GET /api/v1/team/{team_id}?api_key=<your_api_key>
```

## Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | integer | Yes | The fantasy team ID |

## Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `week_index` | integer | Current week | Fantasy week number (1-17) |
| `day_of_week_override` | integer | 0 | Starting day override (0=Monday, 6=Sunday) |
| `injury_status` | string | ACTIVE | Comma-separated injury statuses (e.g., "ACTIVE,PROBABLE") |

## Response

### Success Response (200 OK)

```json
{
  "status": "success",
  "data": {
    "team": {
      "id": 1,
      "name": "Team Name",
      "owner": "Owner Name",
      "rank": 1,
      "wins": 5,
      "losses": 2,
      "points_for": 1234.56,
      "points_against": 1100.25
    },
    "week": {
      "index": 1,
      "day_of_week_override": 0,
      "injury_status_filter": ["ACTIVE"]
    },
    "performance_metrics": {
      "predicted_average_points": 145.5,
      "predicted_std_dev": 12.3,
      "number_of_games": 9
    },
    "matchup": {
      "home_team": "Team A",
      "away_team": "Team B",
      "is_home": true,
      "opponent_id": 2,
      "opponent_name": "Opponent Team"
    },
    "opponent_metrics": {
      "predicted_average_points": 142.1,
      "predicted_std_dev": 11.8,
      "number_of_games": 9
    },
    "matchup_analysis": {
      "point_differential": 3.4,
      "point_differential_std_dev": 17.2
    }
  }
}
```

### Error Responses

#### Invalid Team ID (404)
```json
{
  "status": "error",
  "message": "Team with ID 999999 not found in league"
}
```

#### Invalid Week Index (400)
```json
{
  "status": "error",
  "message": "week_index must be an integer between 1 and 17"
}
```

#### Invalid Day of Week (400)
```json
{
  "status": "error",
  "message": "day_of_week_override must be 0-6 (0=Monday, 6=Sunday)"
}
```

#### League Not Initialized (503)
```json
{
  "status": "error",
  "message": "League not initialized. Check environment variables."
}
```

## Usage Examples

### Get current week matchup for team with ID 1
```bash
curl "http://localhost:5000/api/v1/team/1?api_key=your_api_key"
```

### Get week 5 matchup for team with ID 1
```bash
curl "http://localhost:5000/api/v1/team/1?week_index=5&api_key=your_api_key"
```

### Get week 3 matchup with multiple injury statuses
```bash
curl "http://localhost:5000/api/v1/team/1?week_index=3&injury_status=ACTIVE,PROBABLE&api_key=your_api_key"
```

### Get week 7 matchup starting from Wednesday (day 2)
```bash
curl "http://localhost:5000/api/v1/team/1?week_index=7&day_of_week_override=2&api_key=your_api_key"
```

## Response Fields Explanation

### Team Section
- **id**: Fantasy team ID
- **name**: Team name
- **owner**: Team owner name
- **rank**: Current position in league standings
- **wins/losses**: Season record
- **points_for**: Total points scored this season
- **points_against**: Total points allowed this season

### Performance Metrics
- **predicted_average_points**: Expected points for the specified week
- **predicted_std_dev**: Standard deviation of point prediction
- **number_of_games**: Number of games scheduled for the team in that week

### Matchup
- **home_team**: Home team name
- **away_team**: Away team name
- **is_home**: Boolean indicating if the requested team is home (true) or away (false)
- **opponent_id**: Opponent's team ID
- **opponent_name**: Opponent's team name

### Matchup Analysis
- **point_differential**: Predicted point difference (team - opponent)
- **point_differential_std_dev**: Standard deviation of the point differential prediction

## Notes

- If no matchup exists for the specified week, the `matchup` field will contain a message instead of matchup data
- If no matchup exists, `opponent_metrics` and `matchup_analysis` will be null
- All point predictions are based on the active roster and specified injury status filters
- The endpoint requires API key authentication
