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

### Step 1: Get Current Week Scoreboard
**Endpoint:** `GET /api/v1/scoreboard/{week_index}`

**Purpose:** Retrieve all current matchups and scores for the week

**Query:**
```bash
GET /api/v1/scoreboard/7?api_key={API_KEY}
```

**Response Data Used:**
- Current score for your team
- Current score for opponent
- Point differential
- Opponent ID and name

### Step 2: Get Players Playing Tomorrow
**Endpoint:** `GET /api/v1/players-playing/{scoring_period}?team_id={team_id}`

**Purpose:** Get projections for players with games in the next scoring period

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

### Step 3: Calculate Final Projections
**Calculation Logic:**
```
Your Final Score = Current Score + Tomorrow's Projection
Opponent Final Score = Opponent Current + Opponent Tomorrow
Point Differential = Your Final - Opponent Final
Winner = "YES" if Point Differential > 0 else "NO"
```

## Results Example

### Current Status (Week 7, Dec 6)
```
Your Team (SEA MoNeYPro):     1,027.00
Opponent (Dragon City Tiedan):  943.00
Current Lead:                    +84.00
```

### Tomorrow's Projections (Dec 7)
```
Your Projection:      +95.33 pts (3 players with games)
Opponent Projection:  +119.43 pts (5 players with games)
```

### Projected Final
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

1. `GET /api/v1/scoreboard/{week_index}` - Current scores
2. `GET /api/v1/players-playing/{scoring_period}?team_id={team_id}` - Tomorrow's projections
3. Repeated for opponent team (same endpoint, different team_id)

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
- Current week is week 7 (Nov 30 - Dec 6, 2026)
- Season ends at week 23 (Dec 6 - Dec 13, 2026)

## Success Metrics

✅ Accurate current score retrieval
✅ Proper player projection lookup
✅ Correct final score calculation
✅ Clear win/loss determination
✅ Individual player breakdown
✅ Opponent comparison included
