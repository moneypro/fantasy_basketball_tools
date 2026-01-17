# Using Claude with Fantasy Basketball Tools

## Overview

This Fantasy Basketball Service can be used with **Claude**, Anthropic's AI assistant, as an alternative or complement to the existing GPT integration. Claude offers powerful code understanding, API interaction, and data analysis capabilities that work well with this basketball analytics service.

**Current Setup:**
- Flask API service with Docker support
- GPT custom actions integrated (see `gpt_actions/` directory)
- Remote service: `https://hcheng.ngrok.app`
- API authentication via API keys

**Claude Integration Options:**
1. **Claude Code CLI** - Use Claude to develop and test this codebase
2. **Claude API** - Integrate Claude directly into your application
3. **Claude Chat** - Use Claude web interface with API endpoints

---

## Table of Contents

1. [Quick Start with Claude](#quick-start-with-claude)
2. [Using Claude Code CLI](#using-claude-code-cli)
3. [Integrating Claude API](#integrating-claude-api)
4. [Claude vs GPT for Fantasy Basketball](#claude-vs-gpt-for-fantasy-basketball)
5. [Example Prompts and Workflows](#example-prompts-and-workflows)
6. [API Endpoints for Claude](#api-endpoints-for-claude)
7. [Best Practices](#best-practices)

---

## Quick Start with Claude

### Option 1: Claude Code CLI (Development)

If you're using Claude Code to develop this project:

```bash
# Claude can help you:
# - Understand the codebase structure
# - Add new features to the API
# - Write and run tests
# - Debug issues
# - Deploy with Docker

# Example: Ask Claude to run tests
"Run the integration tests and fix any failures"

# Example: Ask Claude to add a feature
"Add an endpoint to get player injury history"
```

### Option 2: Claude API (Production Integration)

```python
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

# Use Claude to analyze basketball data
message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[{
        "role": "user",
        "content": "Analyze this player's stats and predict their performance: ..."
    }]
)
```

### Option 3: Claude Chat (Interactive Analysis)

Use Claude web interface at https://claude.ai with your API endpoints:

```
You: I have a fantasy basketball API at https://hcheng.ngrok.app
     Can you help me analyze my team for this week?

Claude: I'd be happy to help! I can call your API to get team data.
        What's your API key and team ID?
```

---

## Using Claude Code CLI

### Setup

1. **Install Claude Code** (if not already installed):
   ```bash
   npm install -g @anthropic-ai/claude-code
   # or
   brew install claude-code
   ```

2. **Navigate to project**:
   ```bash
   cd /home/user/fantasy_basketball_tools
   ```

3. **Start Claude Code**:
   ```bash
   claude
   ```

### Common Development Tasks

#### Understanding the Codebase

```
You: "Explain how the prediction system works"
Claude: [Analyzes predict/ directory and explains the logic]

You: "What's the relationship between teams and rosters?"
Claude: [Searches code and explains the data model]
```

#### Adding Features

```
You: "Add an endpoint to compare two players statistically"
Claude: [Creates new endpoint, adds tests, updates documentation]

You: "Implement caching for ESPN API calls"
Claude: [Adds Redis/in-memory caching with proper invalidation]
```

#### Testing and Debugging

```
You: "Run all tests and fix any failures"
Claude: [Runs pytest, identifies issues, fixes them]

You: "Debug why the /predictions endpoint is slow"
Claude: [Profiles code, identifies bottleneck, optimizes]
```

#### Docker and Deployment

```
You: "Update Dockerfile to use Python 3.11"
Claude: [Updates Dockerfile, tests build, ensures compatibility]

You: "Add health check endpoint with detailed diagnostics"
Claude: [Implements comprehensive health check]
```

### Agent Development with Claude

The `.agent.md` file provides guidelines for Claude when working on this project. Key points:

- **Authentication**: API keys managed via `auth/api_key.py`
- **Testing**: Integration tests in `tests/` directory
- **Remote Service**: `https://hcheng.ngrok.app`
- **Branch Strategy**: Development on feature branches
- **No Credentials in Code**: Always load from environment/files

---

## Integrating Claude API

### Why Use Claude API?

- **Advanced reasoning** for complex basketball analytics
- **Large context window** (200K+ tokens) for analyzing entire season data
- **Tool use** for structured API calls and data processing
- **Code generation** for dynamic analysis scripts

### Installation

```bash
pip install anthropic
```

### Basic Integration Example

Create a new file: `tools/claude_analyzer.py`

```python
import anthropic
import os
from typing import Dict, Any

class ClaudeAnalyzer:
    """Use Claude for advanced basketball analytics"""

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

    def analyze_matchup(self, team1_data: Dict, team2_data: Dict) -> str:
        """Analyze a matchup between two teams"""

        prompt = f"""
        Analyze this fantasy basketball matchup:

        Team 1: {team1_data}
        Team 2: {team2_data}

        Provide:
        1. Win probability for each team
        2. Key statistical advantages
        3. Players to watch
        4. Recommended lineup changes
        """

        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def predict_player_performance(self, player_stats: Dict,
                                   upcoming_games: list) -> Dict[str, Any]:
        """Predict player performance for upcoming games"""

        prompt = f"""
        Based on this player's stats and upcoming schedule, predict their
        performance for the next week:

        Historical Stats: {player_stats}
        Upcoming Games: {upcoming_games}

        Return predictions in JSON format with statistical categories.
        """

        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text

    def scout_free_agents(self, roster: Dict, available_players: list,
                         team_needs: list) -> str:
        """Get recommendations for free agent pickups"""

        prompt = f"""
        Scout the best free agent pickups for this fantasy team:

        Current Roster: {roster}
        Available Players: {available_players}
        Team Needs: {team_needs}

        Recommend top 5 pickups with rationale.
        """

        message = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text
```

### Using Claude with Tool Use (Structured API Calls)

```python
import anthropic
import json
import requests

class ClaudeAPIAssistant:
    """Claude assistant that can call your Fantasy Basketball API"""

    def __init__(self, api_base_url: str, api_key: str, anthropic_key: str):
        self.api_base = api_base_url
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=anthropic_key)

        # Define tools Claude can use
        self.tools = [
            {
                "name": "get_team_roster",
                "description": "Get the roster for a fantasy basketball team",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "integer",
                            "description": "The team ID"
                        }
                    },
                    "required": ["team_id"]
                }
            },
            {
                "name": "get_week_predictions",
                "description": "Get predictions for a specific week",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "week_index": {
                            "type": "integer",
                            "description": "The week number (1-23)"
                        }
                    },
                    "required": ["week_index"]
                }
            }
        ]

    def call_api(self, endpoint: str, method: str = "POST",
                 data: dict = None) -> dict:
        """Make API call to Fantasy Basketball service"""
        url = f"{self.api_base}{endpoint}?api_key={self.api_key}"

        if method == "POST":
            response = requests.post(url, json=data or {})
        else:
            response = requests.get(url)

        return response.json()

    def chat(self, user_message: str) -> str:
        """Chat with Claude, allowing it to call your API"""

        messages = [{"role": "user", "content": user_message}]

        # Initial request
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            tools=self.tools,
            messages=messages
        )

        # Handle tool use
        while response.stop_reason == "tool_use":
            tool_use = next(
                block for block in response.content
                if block.type == "tool_use"
            )

            # Execute the tool
            if tool_use.name == "get_team_roster":
                result = self.call_api(
                    f"/api/v1/team/{tool_use.input['team_id']}/roster"
                )
            elif tool_use.name == "get_week_predictions":
                result = self.call_api(
                    "/api/v1/predictions/week-analysis",
                    data={"week_index": tool_use.input["week_index"]}
                )

            # Send result back to Claude
            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": json.dumps(result)
                }]
            })

            # Continue conversation
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                tools=self.tools,
                messages=messages
            )

        # Return final text response
        return response.content[0].text


# Usage example
assistant = ClaudeAPIAssistant(
    api_base_url="https://hcheng.ngrok.app",
    api_key="your-fantasy-api-key",
    anthropic_key="your-anthropic-api-key"
)

response = assistant.chat(
    "Should I pick up player ID 5211175? Compare them to my current roster."
)
print(response)
```

---

## Claude vs GPT for Fantasy Basketball

### Feature Comparison

| Feature | Claude | GPT |
|---------|--------|-----|
| **Context Window** | 200K tokens | 128K tokens |
| **Code Understanding** | Excellent | Excellent |
| **Reasoning** | Strong analytical reasoning | Strong pattern recognition |
| **Tool Use** | Native support | Function calling |
| **Pricing** | $3/$15 per million tokens | $2.50/$10 per million tokens |
| **Speed** | Fast | Very fast |
| **Best For** | Complex analysis, large datasets | Quick responses, well-defined tasks |

### When to Use Claude

1. **Complex Multi-Step Analysis**
   - Analyzing entire season trends
   - Evaluating trade scenarios with multiple factors
   - Strategic planning for playoffs

2. **Large Context Needs**
   - Processing all players' season stats at once
   - Comparing multiple weeks of data
   - Analyzing league-wide patterns

3. **Development and Debugging**
   - Understanding large codebases
   - Refactoring complex systems
   - Writing comprehensive tests

### When to Use GPT

1. **Quick Queries**
   - "Who should I start tonight?"
   - "What's my team's projection?"

2. **Real-Time Interactions**
   - Live draft assistance
   - Quick lineup decisions

3. **Cost-Sensitive Operations**
   - High-volume simple queries
   - Basic data lookups

### Migration from GPT to Claude

If you have existing GPT custom actions, here's how to adapt them for Claude:

**GPT Custom Action (existing):**
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Fantasy Basketball API"
  },
  "paths": {
    "/api/v1/predictions/week-analysis": {
      "post": {
        "operationId": "getWeekAnalysis",
        ...
      }
    }
  }
}
```

**Claude Tool Definition (equivalent):**
```python
{
    "name": "get_week_analysis",
    "description": "Get detailed week analysis with team predictions",
    "input_schema": {
        "type": "object",
        "properties": {
            "week_index": {
                "type": "integer",
                "description": "Fantasy week number (1-23)"
            }
        },
        "required": ["week_index"]
    }
}
```

---

## Example Prompts and Workflows

### For Claude Code CLI (Development)

```
# Code Analysis
"Walk me through how the prediction algorithm works"
"Find all places where we call the ESPN API"
"What would break if we changed the scoring_period_id format?"

# Feature Development
"Add rate limiting to all API endpoints"
"Create a caching layer for ESPN data with 5-minute TTL"
"Implement a /compare-players endpoint"

# Testing and Quality
"Write integration tests for the scout module"
"Check for security vulnerabilities in authentication"
"Optimize the database queries in team roster fetching"

# Documentation
"Update the API documentation to include the new endpoints"
"Generate example curl commands for all endpoints"
"Create a troubleshooting guide for common errors"
```

### For Claude API (Production)

```python
# Advanced Analytics
"Analyze my team's performance over the last 5 weeks and identify trends"

# Strategy Planning
"Given my current roster and available free agents, what moves should I make
 for the playoffs?"

# Opponent Analysis
"My opponent this week has these players. What's their likely lineup and
 how can I counter it?"

# Trade Evaluation
"I'm offered Player A for Player B. Analyze ROS (rest of season) value
 considering schedules and historical performance"

# Draft Assistance
"Here's my current draft board. Who should I pick next considering team needs
 and value?"
```

### For Claude Chat (Interactive)

```
You: I'm connected to my Fantasy Basketball API at https://hcheng.ngrok.app
     My API key is xxx. Can you help me analyze my matchup for week 5?

Claude: I can help with that! Let me call your API to get the week 5 analysis.
        [Calls API]
        Here's what I found...

        Your strongest categories this week are:
        - 3-pointers made (projected 45 vs opponent's 38)
        - Free throw percentage (projected .847 vs .812)

        Areas to improve:
        - Rebounds: You're down by ~15. Consider...
```

---

## API Endpoints for Claude

### Quick Reference

All endpoints require authentication via `api_key` parameter or Bearer token.

**Base URL**: `https://hcheng.ngrok.app`

#### Health and Info
```bash
GET /api/v1/health
GET /api/v1/tools/schema
```

#### Predictions and Analysis
```bash
POST /api/v1/predictions/calculate
POST /api/v1/predictions/week-analysis
```

#### Team and Roster
```bash
POST /api/v1/team/{team_id}
POST /api/v1/team/{team_id}/roster
```

#### League and Scoring
```bash
POST /api/v1/scoreboard/{week_index}
POST /api/v1/players-playing/{scoring_period}
```

### Example: Using Claude to Call Your API

```python
# Save this as: tools/claude_cli_helper.py

import anthropic
import requests
import json
import os

def ask_claude_about_api(question: str, api_key: str):
    """
    Ask Claude a question and let it call your Fantasy Basketball API
    """

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    tools = [
        {
            "name": "call_fantasy_api",
            "description": "Call the Fantasy Basketball API",
            "input_schema": {
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "method": {"type": "string", "enum": ["GET", "POST"]},
                    "data": {"type": "object"}
                },
                "required": ["endpoint", "method"]
            }
        }
    ]

    messages = [{"role": "user", "content": question}]

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        tools=tools,
        messages=messages
    )

    # Handle tool calls
    while response.stop_reason == "tool_use":
        tool_use = next(b for b in response.content if b.type == "tool_use")

        # Make API call
        url = f"https://hcheng.ngrok.app{tool_use.input['endpoint']}"
        params = {"api_key": api_key}

        if tool_use.input['method'] == "POST":
            result = requests.post(url, params=params,
                                 json=tool_use.input.get('data', {}))
        else:
            result = requests.get(url, params=params)

        # Send result back
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result.text
            }]
        })

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

    return response.content[0].text


# Usage
if __name__ == "__main__":
    result = ask_claude_about_api(
        "What's my team's outlook for this week?",
        api_key="your-fantasy-api-key"
    )
    print(result)
```

---

## Best Practices

### Security

1. **API Keys**
   - Never commit API keys to git
   - Use environment variables: `ANTHROPIC_API_KEY`
   - Rotate keys regularly

2. **Authentication**
   - Always pass your Fantasy API key securely
   - Use Bearer tokens in production
   - Implement rate limiting

### Performance

1. **Context Management**
   - Even with 200K context, be selective
   - Summarize large datasets before sending
   - Use streaming for long responses

2. **Caching**
   - Cache Claude responses for repeated queries
   - Cache API data to reduce ESPN calls
   - Implement TTL based on data freshness needs

### Cost Optimization

1. **Model Selection**
   - Use `claude-sonnet-4-5` for most tasks (balanced)
   - Use `claude-haiku-4` for simple queries (faster, cheaper)
   - Use `claude-opus-4-5` for complex analysis (best quality)

2. **Prompt Engineering**
   - Be specific to get concise responses
   - Use system prompts to set context once
   - Request structured output (JSON) when appropriate

### Error Handling

```python
import anthropic
from anthropic import APIError, APITimeoutError

try:
    response = client.messages.create(...)
except APITimeoutError:
    # Handle timeout
    print("Request timed out, retrying...")
except APIError as e:
    # Handle API errors
    print(f"API error: {e}")
except Exception as e:
    # Handle other errors
    print(f"Unexpected error: {e}")
```

---

## Next Steps

### Getting Started with Claude Code

1. **Install Claude Code CLI**
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Start Development**
   ```bash
   cd /home/user/fantasy_basketball_tools
   claude
   ```

3. **Try Example Tasks**
   - "Explain how the Docker setup works"
   - "Add tests for the prediction endpoints"
   - "Help me debug why predictions are slow"

### Integrating Claude API

1. **Get API Key**
   - Sign up at https://console.anthropic.com
   - Create an API key

2. **Install SDK**
   ```bash
   pip install anthropic
   ```

3. **Test Integration**
   ```python
   # See examples above
   ```

4. **Deploy**
   - Add to Docker environment variables
   - Update `docker-compose.yml`
   - Test in production

### Building Custom Features

1. **Claude-Powered Insights**
   - Add `/api/v1/claude/analyze-team` endpoint
   - Use Claude for natural language queries
   - Generate weekly reports automatically

2. **Chat Interface**
   - Build a chat UI that talks to your API
   - Use Claude to interpret user questions
   - Return formatted basketball insights

3. **Automation**
   - Daily lineup optimization with Claude
   - Automated trade analysis
   - Weekly performance reports

---

## Resources

### Documentation
- **Claude API Docs**: https://docs.anthropic.com
- **Claude Code CLI**: https://github.com/anthropics/claude-code
- **This Project's Docs**: See `INDEX.md` for full documentation index

### Support
- **Anthropic Discord**: https://discord.gg/anthropic
- **API Status**: https://status.anthropic.com

### Related Files
- `.agent.md` - Agent development guidelines
- `QUICKSTART_SERVICE.md` - Service setup guide
- `AUTHZ_AND_LOGGING_GUIDE.md` - Authentication details
- `gpt_actions/` - Existing GPT integration examples

---

## Contributing

If you build cool Claude integrations for this project, please document them here!

```bash
# To update this documentation
git add CLAUDE.md
git commit -m "Update Claude integration docs"
git push origin claude/add-claude-md-docker-hVuRz
```

---

**Last Updated**: January 17, 2026
**Claude Models**: Sonnet 4.5, Opus 4.5, Haiku 4
**API Version**: 1.0.0
