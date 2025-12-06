# Fantasy Basketball Service Architecture Roadmap

## Current Architecture

```
GitHub Repository (fantasy_basketball_tools)
  ↓ Push to master
  ↓ GitHub Actions (publish_html.yml)
    ├─ Run calculations (predict_week.py)
    ├─ Generate HTML/forecasts
    └─ Push to website repo (dev branch)
        ↓
Website Repository (static files)
  ↓
AWS Amplify
  ↓
Static Website Deployment
```

**Current Limitations:**
- Calculations run on a schedule (Monday 2 PM)
- Static HTML output
- Can't easily re-run with current data on-demand
- No real-time updates
- Limited to scheduled deployments

---

## Short-Term Goal: On-Demand Calculations

### Phase 1: RESTful API Service (Weeks 1-2)

**Goal:** Make calculations executable on-demand with current data

#### 1.1 Create Flask/FastAPI Backend

```
fantasy_basketball_service/
├── app.py                          # Main Flask/FastAPI app
├── api/
│   ├── __init__.py
│   ├── routes.py                   # API endpoints
│   └── schemas.py                  # Request/response models
├── services/
│   ├── __init__.py
│   ├── prediction_service.py       # Wrapper around predict_week
│   └── cache_service.py            # Caching layer
├── models/
│   ├── __init__.py
│   └── prediction.py               # Data models
├── config.py                       # Configuration
├── requirements.txt
└── Dockerfile                      # For containerization
```

#### 1.2 Key API Endpoints

```
POST /api/v1/predictions/calculate
  Request: {
    "week_index": 1,
    "day_of_week_override": 0,
    "injury_status": ["ACTIVE", "DAY_TO_DAY"]
  }
  Response: {
    "status": "success",
    "data": {
      "predictions": {...},
      "remaining_days": {...},
      "matchups": {...}
    },
    "timestamp": "2025-01-15T10:30:00Z"
  }

GET /api/v1/predictions/:week_id
  - Retrieve cached prediction
  
GET /api/v1/predictions/latest
  - Get most recent prediction
  
POST /api/v1/predictions/refresh
  - Force re-calculation with fresh data
```

#### 1.3 Implementation Strategy

```python
# api/routes.py
from flask import Flask, request, jsonify
from services.prediction_service import PredictionService
from services.cache_service import CacheService

app = Flask(__name__)
cache = CacheService()
prediction_service = PredictionService()

@app.route('/api/v1/predictions/calculate', methods=['POST'])
def calculate_prediction():
    """Calculate predictions on-demand"""
    data = request.json
    
    # Check cache first
    cache_key = f"prediction_{data.get('week_index')}"
    cached = cache.get(cache_key)
    if cached and not request.args.get('force_refresh'):
        return jsonify({"status": "cached", "data": cached})
    
    # Calculate fresh
    try:
        result = prediction_service.predict_week(
            week_index=data['week_index'],
            day_of_week_override=data.get('day_of_week_override', 0),
            injury_status=data.get('injury_status', ['ACTIVE'])
        )
        
        # Cache result
        cache.set(cache_key, result, ttl=3600)  # 1 hour TTL
        
        return jsonify({
            "status": "success",
            "data": result,
            "cached": False
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400
```

#### 1.4 Deploy as AWS Lambda + API Gateway

```yaml
# serverless.yml
service: fantasy-basketball-api

provider:
  name: aws
  runtime: python3.9
  region: us-west-2
  environment:
    ESPN_S2: ${ssm:/fantasy-basketball/espn_s2}
    SWID: ${ssm:/fantasy-basketball/swid}
    LEAGUE_ID: ${ssm:/fantasy-basketball/league_id}

functions:
  predict:
    handler: app.predict_handler
    events:
      - http:
          path: predictions/calculate
          method: post
          cors: true
      - http:
          path: predictions/{week_id}
          method: get
          cors: true
```

---

## Mid-Term Goal: Full Service Platform (Weeks 3-8)

### Phase 2: Database + State Management

**Add persistent storage for predictions**

```python
# Database schema
class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    week_index = db.Column(db.Integer, nullable=False)
    league_id = db.Column(db.String, nullable=False)
    team_predictions = db.Column(JSON, nullable=False)
    remaining_days = db.Column(JSON, nullable=False)
    matchups = db.Column(JSON, nullable=False)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    injury_status = db.Column(JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
```

### Phase 3: WebSocket Real-Time Updates

**Push updates to web clients**

```python
# Real-time updates when data changes
@socketio.on('subscribe_week')
def on_subscribe(data):
    week_id = data['week_id']
    join_room(f'week_{week_id}')
    emit('subscribed', {'week_id': week_id})

# When prediction updates
def notify_subscribers(week_id, prediction_data):
    socketio.emit('prediction_update', 
                  prediction_data, 
                  room=f'week_{week_id}')
```

### Phase 4: Multi-League Support

**Support multiple leagues**

```
/api/v1/leagues
/api/v1/leagues/:league_id/predictions
/api/v1/leagues/:league_id/teams
/api/v1/leagues/:league_id/schedules
```

---

## Long-Term Vision: Full SaaS Platform (3-6 months)

### Phase 5: Web Dashboard

```
Frontend (React/Vue):
├── Predictions Dashboard
├── Team Analysis
├── Schedule View
├── Comparison Tools
├── Historical Trends
└── Admin Panel
```

### Phase 6: Advanced Features

- **Machine Learning:** Improve predictions
- **Historical Data:** Track accuracy over time
- **Alerts & Notifications:** Notify on injury/roster changes
- **Integrations:** Slack, Discord, Email
- **Monetization:** Tiered API access

---

## Implementation Roadmap Summary

### Week 1-2: MVP (On-Demand API)
- ✅ Create Flask/FastAPI app
- ✅ Refactor predict_week for service use
- ✅ Create basic API endpoints
- ✅ Add in-memory caching
- ✅ Deploy to AWS Lambda
- ✅ Create simple web frontend

### Week 3-4: Database Integration
- ✅ Set up PostgreSQL (RDS)
- ✅ Create data models
- ✅ Store predictions persistently
- ✅ Add query APIs

### Week 5-6: Real-Time Features
- ✅ Add WebSocket support
- ✅ Implement live updates
- ✅ Add push notifications

### Week 7-8: Multi-League
- ✅ Support multiple leagues
- ✅ Add league management APIs
- ✅ Create user accounts

### Week 9+: Advanced Features
- ✅ Web dashboard
- ✅ Advanced analytics
- ✅ ML improvements

---

## Tech Stack Recommendation

### Backend
- **Framework:** FastAPI (modern, fast, great for APIs)
  - Alternative: Flask (simpler, more mature)
- **Database:** PostgreSQL (RDS) + Redis (caching)
- **Deployment:** AWS Lambda + API Gateway
  - Alternative: EC2 with Docker
- **Message Queue:** SQS for async tasks
- **Monitoring:** CloudWatch + Sentry

### Frontend
- **Framework:** React or Vue.js
- **Hosting:** AWS Amplify or Vercel
- **State Management:** Redux or Vuex
- **Real-time:** Socket.io or native WebSockets

### Infrastructure
```yaml
AWS Services:
  - Lambda: API execution
  - API Gateway: HTTP endpoints
  - RDS: PostgreSQL database
  - ElastiCache: Redis caching
  - S3: Static files/exports
  - CloudWatch: Logging & monitoring
  - Secrets Manager: Credentials
  - SQS: Async jobs
```

---

## Immediate Action Items (This Week)

### 1. Create FastAPI Service Wrapper

```python
# services/prediction_service.py
from predict.predict_week import (
    predict_week,
    get_remaining_days_cumulative_scores,
    get_remaining_days_table_output
)

class PredictionService:
    def __init__(self):
        self.league = create_league()  # Load once
    
    def predict_week(self, week_index, day_of_week_override=0, injury_status=None):
        """Wrapper around predict_week for service use"""
        if injury_status is None:
            injury_status = ['ACTIVE']
        
        num_games, team_scores = predict_week(
            self.league, week_index, day_of_week_override, injury_status
        )
        
        remaining_days = get_remaining_days_cumulative_scores(
            self.league, week_index, day_of_week_override, injury_status
        )
        
        return {
            "team_scores": team_scores,
            "remaining_days": remaining_days,
            "num_games": num_games
        }
```

### 2. Create Flask App

```python
# app.py
from flask import Flask, request, jsonify
from services.prediction_service import PredictionService

app = Flask(__name__)
service = PredictionService()

@app.route('/api/v1/predictions/calculate', methods=['POST'])
def calculate():
    data = request.json
    result = service.predict_week(
        week_index=data['week_index'],
        day_of_week_override=data.get('day_of_week_override', 0),
        injury_status=data.get('injury_status', ['ACTIVE'])
    )
    return jsonify({"status": "success", "data": result})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 3. Create Docker Setup

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### 4. Create Docker Compose for Local Development

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      ESPN_S2: ${ESPN_S2}
      SWID: ${SWID}
      LEAGUE_ID: ${LEAGUE_ID}
    volumes:
      - .:/app
```

### 5. Test Locally

```bash
docker-compose up
curl -X POST http://localhost:5000/api/v1/predictions/calculate \
  -H "Content-Type: application/json" \
  -d '{"week_index": 1}'
```

---

## Migration from Current Setup

### Step 1: Keep Current GitHub Actions
- Still push to static site
- Also push to new API service

### Step 2: Add API Service Deployment
- New GitHub Action for API deployment
- Deploy to AWS Lambda or EC2

### Step 3: Migrate Website Gradually
- Add API calls alongside static HTML
- Show "Last updated" timestamp
- Add "Refresh" button to re-calculate

### Step 4: Eventually Replace
- Remove static HTML generation
- Use only API for calculations
- Generate HTML from API responses

---

## Cost Estimation

### AWS Costs (Monthly)
- **Lambda:** $0.20 per 1M requests (~$2-5/month)
- **API Gateway:** $3.50 per 1M requests (~$3-5/month)
- **RDS (PostgreSQL):** $20-50 (t3.micro - t3.small)
- **ElastiCache (Redis):** $15-25
- **NAT Gateway:** $32 (if needed)
- **Total:** ~$70-150/month for SaaS platform

### Competitors
- Sleeper API: Free tier available
- ESPN: No official API
- Your service: Could be freemium

---

## Questions to Consider

1. **Multi-user Support?**
   - Just your league? → Simple service
   - Multiple users' leagues? → Complex, need auth

2. **Real-time Updates?**
   - Weekly forecasts only? → Simple caching
   - Real-time player updates? → Complex with WebSocket

3. **Monetization?**
   - Free service for friends?
   - Paid API tiers?
   - Ad-supported?

4. **Accuracy Tracking?**
   - Store historical predictions?
   - Compare against actual scores?

---

## Next Steps

1. **This week:** Create basic Flask service (Phase 1)
2. **Next week:** Deploy to AWS Lambda
3. **Week 3:** Add database (PostgreSQL + Redis)
4. **Week 4:** Create simple web dashboard
5. **Week 5+:** Add advanced features

Would you like me to help implement Phase 1 (Flask API) right now?

