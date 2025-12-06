# Quick Start: Run Your Fantasy Basketball Service

## TL;DR (30 seconds)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit with your ESPN credentials
nano .env
# Fill in: ESPN_S2, SWID, LEAGUE_ID

# 3. Start the service
docker-compose up

# 4. Test it
curl http://localhost:8000/api/v1/health
```

Done! Your service is running at `http://localhost:8000`

---

## Getting Your ESPN Credentials

1. Go to https://fantasy.espn.com and log in
2. Open Browser DevTools (F12 or Cmd+Option+I)
3. Go to **Application** → **Cookies** → **fantasy.espn.com**
4. Find and copy:
   - `ESPN_S2` value
   - `SWID` value
5. Your league ID is in the URL: `leagueId=XXXXX`

---

## API Endpoints

Once running, these endpoints are available:

### Health Check
```bash
curl http://localhost:8000/api/v1/health
```

### Get Available Tools (for AI)
```bash
curl http://localhost:8000/api/v1/tools/schema
```

### Calculate Predictions
```bash
curl -X POST http://localhost:8000/api/v1/predictions/calculate \
  -H "Content-Type: application/json" \
  -d '{"week_index": 1}'
```

### Week Analysis
```bash
curl -X POST http://localhost:8000/api/v1/predictions/week-analysis \
  -H "Content-Type: application/json" \
  -d '{"week_index": 1}'
```

---

## Common Commands

```bash
# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Rebuild (if you change code)
docker-compose up --build

# View running containers
docker-compose ps

# Execute command in container
docker-compose exec fantasy-api bash
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "League not initialized" | Check ESPN credentials in .env |
| "Port 8000 already in use" | Kill process: `sudo lsof -i :8000` |
| "Connection refused" | Make sure `docker-compose up` is running |
| Docker not found | Install Docker first (see `ai/DOCKER_INSTALLATION_GUIDE.md`) |

---

## Full Documentation

For detailed setup: `ai/FLASK_DOCKER_STARTUP_GUIDE.md`

---

## What's Running

- **Flask API** - Handles prediction requests
- **Gunicorn** - Production WSGI server (4 workers)
- **Health Checks** - Auto-restarts if unhealthy
- **Logging** - Full request/response logs

All running in a Docker container with proper isolation!
