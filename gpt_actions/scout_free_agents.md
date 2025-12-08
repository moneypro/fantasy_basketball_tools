# Use Case: Scout Free Agents for Optimal Pickups

## Overview
Identify the best free agents to add to your roster by analyzing:
1. **Current Performance**: Average points (last 30 days, year average)
2. **Future Potential**: Projected points for the season
3. **Next 5 Days Schedule**: Exactly which days they're playing and how many games
4. **Position Value**: How they fill gaps in your roster based on position scarcity
5. **Gap-to-Fill Analysis**: Whether their NBA team has significant OUT/DAY_TO_DAY players (increased usage opportunity)

## Problem Statement
When adding free agents, managers need to understand not just raw talent, but:
- **Immediate Impact**: Are they playing the next 5 days when I need them?
- **Position Fit**: Do I have roster spots that need specific positions?
- **Usage Opportunity**: Is their team missing key players, creating more touches for bench players?

Example:
- LeBron James (PF) goes OUT on Lakers
- Rui Hachimura (PF) on Lakers gets MORE usage → Higher value for PF-needy teams
- Gabe Vincent (SG) on Lakers sees minimal benefit → Lower value for SG-needy teams

## Key Insights
1. **Scoring Period Matters More Than General Stats**
   - A player averaging 20 pts/game is only valuable if they play in the next 5 days
   - Must show exact schedule: "Playing Dec 8 & Dec 10" vs "Playing Dec 8, 9, 10, 11, 12"

2. **Position Scarcity Creates Value**
   - If user has only 1 Guard spot left but 2 Forward spots, a bench Guard is more valuable than bench Forward
   - If user already has 4+ players playing tomorrow, adding anyone is risky

3. **Injury-Driven Opportunity**
   - Only matters if the injured player is significant (avg >= 15 pts or team impact)
   - DAY_TO_DAY = ~30% usage boost expected
   - OUT = ~60% usage boost expected

## Data Requirements

### Free Agent Data to Collect
For each free agent, gather:

```json
{
  "player_id": 12345,
  "name": "Rui Hachimura",
  "nba_team": "LAL",
  "position_eligible": ["PF", "SF", "F"],
  
  "current_stats": {
    "avg_last_30": 18.5,
    "avg_year": 17.2,
    "total_30": 370,
    "gp_30": 20
  },
  
  "projected_stats": {
    "avg_projected": 16.8,
    "gp_projected": 50
  },
  
  "next_5_days_schedule": [
    {
      "scoring_period": 49,
      "date": "Dec 8, 2025",
      "opponent": "DEN",
      "is_playing": true,
      "projected_points": 16.8
    },
    {
      "scoring_period": 50,
      "date": "Dec 9, 2025",
      "opponent": "GSW",
      "is_playing": true,
      "projected_points": 16.8
    },
    {
      "scoring_period": 51,
      "date": "Dec 10, 2025",
      "opponent": "POR",
      "is_playing": false,
      "projected_points": 0
    },
    {
      "scoring_period": 52,
      "date": "Dec 11, 2025",
      "opponent": "ATL",
      "is_playing": true,
      "projected_points": 16.8
    },
    {
      "scoring_period": 53,
      "date": "Dec 12, 2025",
      "opponent": "LAL",
      "is_playing": false,
      "projected_points": 0
    }
  ],
  
  "gap_to_fill_analysis": {
    "team": "LAL",
    "injured_players": [
      {
        "name": "LeBron James",
        "position": "PF",
        "injury_status": "OUT",
        "avg_points": 24.5,
        "usage_boost": "60%"
      }
    ],
    "usage_boost_percentage": 60,
    "relevance": "HIGH"  // Only if injured player matches position and has high avg
  }
}
```

### User Roster Context (From `/api/v1/players-playing` Endpoint)
To determine position gaps for a SPECIFIC day, use the existing endpoint:

```
POST /api/v1/players-playing/{scoring_period}?api_key={API_KEY}
{
  "team_id": 2
}
```

This returns which of your roster players are playing that day. You can call this for each scoring period (49-53) to get:
- Players playing on Dec 8 (period 49)
- Players playing on Dec 9 (period 50)
- Players playing on Dec 10 (period 51)
- etc.

Then the free-agents endpoint just returns raw free agent data, and the LLM combines:
1. Free agent stats from `/api/v1/scout/free-agents`
2. Your daily lineup from `/api/v1/players-playing/{period}`
3. Position gaps for that specific day
4. To make the recommendation: "On Dec 8, you only have 2 Guards playing, so this SG free agent would be valuable"

## Algorithm: Ranking Free Agents (For LLM to Reason About)

**Important:** The service returns raw data. The LLM calling the endpoint does the reasoning and ranking.

### Data the Service Returns

For each free agent, return:

1. **Current Performance Data**
   - avg_last_30 (actual recent production)
   - avg_year (season average)
   - total_30 and gp_30 (games played in last 30)
   - avg_projected (season projection)

2. **Next 5 Days Schedule** (as-is, no modification)
   - Exact dates and opponents
   - Playing (true/false) for each day
   - Count of games in next 5 days

3. **Injury Context** (raw facts for LLM to reason about)
   - Injured teammates on same NBA team
   - Their position, status (OUT/DAY_TO_DAY), and avg points
   - This lets the LLM decide: "LeBron (24.5 pts) OUT at PF means Rui (also PF) gets more opportunities"

4. **User Roster Context** (raw data)
   - Players playing in next 5 days
   - Open roster spots count
   - Open spots BY POSITION (PG, SG, SF, PF, C, G, F)
   - This lets the LLM decide: "User has 2 Forward spots open vs 1 Guard spot, so Forward-eligible players are higher priority"

### What the LLM Will Reason About

The LLM will receive all this data and:
- Calculate if schedule matters (3 games next 5 days = good, 1 game = not as valuable)
- Estimate usage boost from injuries (DAY_TO_DAY + position match = some boost, OUT + position match = larger boost)
- Decide position priority (more open spots = higher priority for that position)
- Rank players by relevance to THIS user's needs

**No hardcoded percentages or formulas in the code.** Just raw data.

## API Endpoint Design

### New Endpoint: `POST /api/v1/scout/free-agents`

**Request:**
```json
{
  "team_id": 2,
  "limit": 20,
  "min_avg_points": 5
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "free_agents": [
      {
        "player_id": 12345,
        "name": "Rui Hachimura",
        "nba_team": "LAL",
        "injury_status": "ACTIVE",
        "positions_eligible": ["PF", "SF", "F"],
        "scoring": {
          "avg_last_30": 18.5,
          "total_30": 370,
          "gp_30": 20,
          "avg_year": 17.2,
          "avg_projected": 16.8
        },
        "team_injuries": [
          {
            "player_name": "LeBron James",
            "position": "PF",
            "injury_status": "OUT",
            "avg_points": 24.5
          }
        ]
      },
      {
        "player_id": 12346,
        "name": "Jamal Murray",
        "nba_team": "DEN",
        "injury_status": "ACTIVE",
        "positions_eligible": ["PG", "SG", "G"],
        "scoring": {
          "avg_last_30": 17.2,
          "total_30": 344,
          "gp_30": 20,
          "avg_year": 16.5,
          "avg_projected": 15.9
        },
        "team_injuries": []
      }
    ],
    "summary": {
      "total_free_agents_analyzed": 1247,
      "returned": 20,
      "min_avg_points_filter": 5
    }
  }
}
```

**How to Use:**
1. Call this endpoint to get raw free agent data with their stats and team injury context
2. For each free agent you're interested in, call `POST /api/v1/players-playing/{scoring_period}` for periods 49-53 to see:
   - Which of your roster players are playing that day
   - Your position breakdown for that day
3. The LLM combines both data sources to recommend who to pick up based on your daily position gaps

## Implementation Steps

1. **Create `get_free_agents()` in utils/shared_player_utils.py**
   - Return all players NOT on any league team roster
   - Include their 2026 stats (avg_last_30, avg_year, total_30, gp_30, avg_projected)
   - Return positions eligible for each player

2. **Create `get_team_injuries()` helper in scout module**
   - For each free agent's NBA team
   - Find OUT and DAY_TO_DAY players
   - Return player name, position, status, avg_points

3. **Create new endpoint `/api/v1/scout/free-agents`**
   - Call `get_free_agents()` to get all eligible players
   - Filter by min_avg_points (default 5)
   - For each free agent, get team injuries from `get_team_injuries()`
   - Return raw data: stats + team_injuries
   - Sort by avg_last_30 descending
   - Return top N (limit parameter)

## Example Usage Scenario

The free-agents endpoint returns raw data like:

**Free Agent Option 1:** Rui Hachimura
- avg_last_30: 18.5, avg_year: 17.2, avg_projected: 16.8
- Positions: PF, SF, F
- Team injuries: LeBron James (PF, OUT, 24.5 avg)

**Free Agent Option 2:** Jamal Murray
- avg_last_30: 17.2, avg_year: 16.5, avg_projected: 15.9
- Positions: PG, SG, G
- Team injuries: None

**Free Agent Option 3:** Keldon Johnson
- avg_last_30: 14.3, avg_year: 13.8, avg_projected: 13.2
- Positions: SF, PF, F
- Team injuries: Devin Booker (SG, DAY_TO_DAY, 21.0 avg)

**What the LLM Reasoning Will Be:**
- Rui has the highest avg (18.5), AND his NBA team is missing LeBron (a high-value PF), so Rui gets extra opportunities
- The user (checking via `/api/v1/players-playing`) has 2 Forward spots open but only 1 Guard spot open
- Therefore: Rui > Keldon (both forwards, but Rui is better) > Jamal (guard fills smaller gap)

The endpoint just provides the facts; the LLM does the reasoning.

## Implementation Ready ✅

The document is complete. No hardcoded scoring logic in the service - just raw data for the LLM to reason about:

1. **Free agent stats** (avg_last_30, avg_year, avg_projected)
2. **Team injuries** (who's out/day-to-day on their NBA team)
3. **Position eligibility** (which positions they can fill)

The LLM calling the endpoint will:
- Combine with `/api/v1/players-playing/{period}` data for your specific daily roster
- Reason about position gaps, injury opportunities, and schedule
- Recommend the best free agents for your situation
