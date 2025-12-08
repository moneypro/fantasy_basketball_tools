# Use Case: Predict Remaining Week

## Overview
This use case demonstrates how to combine multiple API endpoints to get a comprehensive prediction of the remaining week in a fantasy basketball matchup. It answers the question: "Will I win this week and by how much?"

## Problem Statement
A fantasy basketball player wants to know:
1. What is their current score this week?
2. Who is their opponent?
3. What is the current point differential?
4. How many days are left in the week?
5. How many points will they score in the remaining days?
6. How many points will their opponent score in the remaining days?
7. What is the projected final score and will they win?

## Solution Flow

### Step 1: Get Current Week Scoreboard (with Live Scores)
**Endpoint:** `GET /api/v1/scoreboard/{week_index}`

**Purpose:** Retrieve all current matchups and **live** scores for the week

**Query:**
```bash
GET /api/v1/scoreboard/7?api_key={API_KEY}
```

**Important Implementation Detail:**
The endpoint uses `league.box_scores(week, current_scoring_period, matchup_total=True)` to get live scores as games progress, not final scores. Scores are matched to matchups by comparing team IDs, not array index, ensuring accuracy regardless of box_scores ordering.

**Response Data Used:**
- Current **live** score for your team (updated as games progress)
- Current **live** score for opponent
- Point differential
- Opponent ID and name

### Step 2: Get Comprehensive Week Analysis (Recommended)
**Endpoint:** `POST /api/v1/predictions/week-analysis`

**Purpose:** Get all week predictions, remaining days breakdown, and injury status in one call

**Query:**
```bash
POST /api/v1/predictions/week-analysis?api_key={API_KEY}
{
  "week_index": 7,
  "day_of_week_override": 0
}
```

**Response Data Used:**
- Full week projections for all teams (active-only, day-to-day included, out included)
- Remaining days breakdown by team (remaining points for each day of week)
- Injury status summary (DAY_TO_DAY and OUT players for each team)
- Point differentials and matchup analysis

**Response Structure:**
```json
{
  "active_only": {
    "predictions": [
      {
        "Team Name": "SEA MoNeYPro",
        "Week 7 Mean": 1102,
        "Week 7 Standard Deviation": 24,
        "# of games": 32
      }
    ],
    "remaining_days": [
      {
        "Team Name": "SEA MoNeYPro",
        "Thursday (...)": "650 ± 18",
        "Friday (...)": "548 ± 17",
        "Saturday (...)": "305 ± 13",
        "Sunday (...)": "96 ± 8",
        "Monday (...)": "1102 ± 24"
      }
    ]
  },
  "day_to_day_included": { /* Same structure with day-to-day players */ },
  "out_included": { /* Same structure with all injured players */ },
  "summary": {
    "non_healthy_players": [
      {
        "Team Name": "SEA MoNeYPro",
        "DAY_TO_DAY": "Davion Mitchell",
        "OUT": "Stephen Curry, Stephon Castle"
      }
    ]
  }
}
```

**Advantages:**
- Single API call for complete analysis
- Includes all three injury status scenarios
- Shows remaining days breakdown
- Includes injury information
- Compares all teams at once

### Step 3: (Alternative) Get Players Playing Tomorrow
**Endpoint:** `GET /api/v1/players-playing/{scoring_period}?team_id={team_id}`

**Purpose:** Get detailed player-level projections for the next scoring period

**Query (Your Team):**
```bash
GET /api/v1/players-playing/48?team_id=2&api_key={API_KEY}
```

**Response Data Used:**
- Your projected points for tomorrow
- List of players with games
- Individual player projections

**Query (Opponent Team):**
```bash
GET /api/v1/players-playing/48?team_id=15&api_key={API_KEY}
```

**Response Data Used:**
- Opponent's projected points for tomorrow
- Opponent's players with games

### Step 3: Get Detailed Player Matchup Analysis
**Endpoint:** `GET /api/v1/players-playing/{scoring_period}?team_id={team_id}`

**Purpose:** See exactly which players have games and their individual projections

**Queries:**
```bash
# Your team's players tomorrow
GET /api/v1/players-playing/48?team_id=5&api_key={API_KEY}

# Opponent's players tomorrow
GET /api/v1/players-playing/48?team_id=10&api_key={API_KEY}
```

**Response Data Used:**
- List of players with games (and without)
- Individual projected points per player
- Injury status for each player
- Total projected points for the team

**Insight:** This reveals the **matchup quality** - if opponent has 7 top-tier players vs your 5, they'll likely outscore you even if you're currently winning.

### Step 4: Calculate Final Projections
**Calculation Logic:**
```
Your Final Score = Current Score + Tomorrow's Projection
Opponent Final Score = Opponent Current + Opponent Tomorrow
Point Differential = Your Final - Opponent Final
Winner = "YES" if Point Differential > 0 else "NO"
```

## Results Example

### Example 1: Shanghai Stretchers vs Kanagawa (Week 7, Dec 6)

#### Current Status
```
Shanghai Stretchers:        1,195.00 ✅ LEADING
Kanagawa Medical Center:    1,177.00
Current Lead:                 +18.00
```

#### Tomorrow's Player Matchup
```
Shanghai (5 players, 152.57 pts):
  - Jalen Suggs (34.15)
  - Deandre Ayton (32.75)
  - Nikola Vucevic (31.48)
  - De'Anthony Melton (28.10)
  - Ryan Kalkbrenner (26.09)

Kanagawa (7 players, 218.72 pts):
  - Josh Giddey (41.28)
  - Zach Edey (37.26)
  - Immanuel Quickley (33.76)
  - Coby White (30.78)
  - Robert Williams III (27.67)
  - Toumani Camara (24.89)
  - Brandon Miller (23.08)
```

#### Projected Final
```
Shanghai Final:    1,347.57
Kanagawa Final:    1,395.72
Result:            ❌ LOSE by 48.15 points
```

**Key Insight:** Despite leading by 18 points, Shanghai has fewer players (5 vs 7) and lower projections (152 vs 218). Kanagawa's matchup is significantly stronger, resulting in a projected loss.

### Example 2: SEA MoNeYPro vs Dragon City Tiedan (Week 7)

#### Current Status
```
SEA MoNeYPro (You):         1,027.00 ✅ LEADING
Dragon City Tiedan:           943.00
Current Lead:                 +84.00
```

#### Tomorrow's Projections (Dec 7)
```
Your Projection:      +95.33 pts (3 players with games)
Opponent Projection:  +119.43 pts (5 players with games)
```

#### Projected Final
```
Your Final:           1,122.33
Opponent Final:       1,062.43
Result:               ✅ WIN by 59.90 points
```

## Key Insights

1. **Real-Time Data:** Uses current scores from the league scoreboard
2. **Player-Level Projections:** Breaks down projections by individual players
3. **Opponent Analysis:** Compares your projections to opponent's
4. **Win Probability:** Calculates final outcome based on remaining days
5. **Actionable:** Helps users understand their week status at a glance

## Data Dependencies

- Week number (current week)
- Team ID (your team)
- Scoring period (days remaining)
- Current league standings
- Player projection statistics

## API Endpoints Used

**Recommended Single-Call Approach:**
1. `POST /api/v1/predictions/week-analysis` - Complete week analysis with all scenarios and injury status

**Alternative Multi-Call Approach:**
1. `GET /api/v1/scoreboard/{week_index}` - Current live scores (uses league.box_scores() for accuracy)
2. `GET /api/v1/players-playing/{scoring_period}?team_id={team_id}` - Players with games and projections
3. Repeat endpoint 2 for opponent team with their team_id
4. Calculate final scores by adding projections to current scores

## Implementation Details

### Prerequisites
- Valid API key
- Current week number
- Your team ID
- Current scoring period (day within week)

### Calculation Details
```python
# Days left in week calculation
current_scoring_period = 47  # Dec 6
week_start_period = 41  # Week 7 starts Dec 1 (period 41)
days_left = (week_start_period + 7) - current_scoring_period  # 1 day

# Score calculation
your_tomorrow = sum(player.projected_avg_points for player in your_players_with_games)
opponent_tomorrow = sum(player.projected_avg_points for player in opp_players_with_games)

your_final = current_your_score + your_tomorrow
opp_final = current_opp_score + opponent_tomorrow

differential = your_final - opp_final
```

## Use Case Benefits

1. **Quick Decision Making:** Know your week status without checking ESPN manually
2. **Player Awareness:** See which specific players are contributing
3. **Opponent Awareness:** Understand opponent's remaining strength
4. **Win Probability:** Clear yes/no answer on likely outcome
5. **Planning:** Decide if roster changes are needed based on projections

## Variations

### Weekly Outlook
Instead of just tomorrow, extend to full week remaining:
- Query multiple scoring periods ahead
- Sum all remaining projections
- Get true week-end prediction

### Head-to-Head Comparison
Add opponent roster details:
- Query opponent's full roster
- Compare player-by-player matchups
- Identify key battles

### Bench Impact
Check bench players with games:
- Query both active and bench roster
- See if benching decisions matter for final score

## Notes

- Projections are based on historical stats and recent performance
- Variance/std dev provides confidence intervals
- Scoring period = 1 day, Week = 7 days
- Current week is week 7 (Dec 1 - Dec 7 2025)
- Season ends at week 23 (March 30 - April 5, 2026)

## Success Metrics

✅ Accurate current score retrieval
✅ Proper player projection lookup
✅ Correct final score calculation
✅ Clear win/loss determination
✅ Individual player breakdown
✅ Opponent comparison included
