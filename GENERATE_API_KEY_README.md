# Generate API Key Script

A bash script to easily generate Fantasy Basketball API keys with custom descriptions and rate limits.

## Overview

The `generate_api_key.sh` script automates the process of creating API keys for the Fantasy Basketball Service API. It handles:
- Making authenticated requests to the API key generation endpoint
- Parsing JSON responses
- Displaying key information clearly
- Warnings about key security

## Requirements

- `bash` shell
- `curl` command-line tool
- `jq` JSON parser (for parsing API responses)

### Install Dependencies

**macOS:**
```bash
brew install curl jq
```

**Ubuntu/Debian:**
```bash
sudo apt-get install curl jq
```

**CentOS/RHEL:**
```bash
sudo yum install curl jq
```

## Usage

### Basic Usage

Generate an API key with a simple description:

```bash
./generate_api_key.sh "My Integration"
```

### Advanced Usage

Generate with custom API base URL:

```bash
./generate_api_key.sh "My Integration" "https://api.example.com"
```

Generate with custom rate limit (default is 100):

```bash
./generate_api_key.sh "My Integration" "https://api.example.com" 500
```

### Examples

```bash
# OpenAI Integration
./generate_api_key.sh "OpenAI ChatGPT Integration"

# GitHub Actions CI/CD
./generate_api_key.sh "GitHub Actions Pipeline" "https://leanora-unmumbling-noncontroversially.ngrok-free.dev" 1000

# Development Environment
./generate_api_key.sh "Local Development" "http://localhost:5000" 50
```

## Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `$1` | API Key Description/Name | "API Key" | No |
| `$2` | API Base URL | `https://hcheng.ngrok.app` | No |
| `$3` | Rate Limit (requests) | 100 | No |

## Output

The script provides clear, color-coded output:

```
========================================
Fantasy Basketball API Key Generator
========================================

Configuration:
  API Base URL:   https://hcheng.ngrok.app
  Description:    OpenAI Integration
  Rate Limit:     100 requests/period

Generating API key...

✅ API Key Generated Successfully!

════════════════════════════════════════
API Key:
fba_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
════════════════════════════════════════

⚠️  IMPORTANT: Save this key now - you won't see it again!

Key Details:
  Name:        OpenAI Integration
  Rate Limit:  100 requests

Usage Example:
  curl -X GET 'https://your-api.com/api/v1/health?api_key=fba_xxxxx'

Or in request headers:
  curl -X GET 'https://your-api.com/api/v1/health' \
    -H 'X-API-Key: fba_xxxxx'
```

## Authentication

The script uses an embedded admin token for authentication:

```
ADMIN_TOKEN="fba_mjfwAOKGkneKbFLai7NyGwejuBxyrogBcMCndiww8x0"
```

**Security Note:** This token is embedded in the script. Ensure you:
- Keep this script in a secure location
- Don't share the script with untrusted parties
- Consider rotating the admin token periodically
- Use this script only in trusted environments

## API Endpoint

The script calls:

```
POST /api/v1/auth/keys/generate
```

With the following payload:

```json
{
  "name": "API Key Description",
  "rate_limit": 100
}
```

## Error Handling

The script includes error handling for common issues:

- **No description provided:** Uses default "API Key"
- **Invalid API response:** Displays error message from API
- **Connection errors:** Reports curl errors
- **Invalid JSON:** Shows raw response for debugging

### Common Errors

**Error: "curl: (7) Failed to connect"**
- Check that the API base URL is correct
- Verify the service is running
- Check network connectivity

**Error: "api_key is required in request body"**
- The admin token may be invalid or expired
- Verify `ADMIN_TOKEN` in the script

**Error: "jq: command not found"**
- Install jq: `brew install jq` (macOS) or `sudo apt-get install jq` (Linux)

## Making the Script Executable

The script should already be executable, but if needed:

```bash
chmod +x generate_api_key.sh
```

## Using Generated Keys

Once you have an API key, use it in requests:

### Query Parameter Method

```bash
curl -X GET 'https://api.example.com/api/v1/health?api_key=fba_xxxxx'
```

### Header Method

```bash
curl -X GET 'https://api.example.com/api/v1/health' \
  -H 'X-API-Key: fba_xxxxx'
```

### Python Example

```python
import requests

api_key = "fba_xxxxx"
headers = {"X-API-Key": api_key}
response = requests.get(
    "https://api.example.com/api/v1/health",
    headers=headers
)
```

### JavaScript/Node.js Example

```javascript
const apiKey = "fba_xxxxx";
const headers = { "X-API-Key": apiKey };

fetch("https://api.example.com/api/v1/health", { headers })
  .then(response => response.json())
  .then(data => console.log(data));
```

## Key Management

### Listing Keys

To see all generated keys:

```bash
curl -X GET 'https://api.example.com/api/v1/auth/keys' \
  -H 'Authorization: Bearer fba_mjfwAOKGkneKbFLai7NyGwejuBxyrogBcMCndiww8x0'
```

### Revoking Keys

To revoke/delete a key:

```bash
curl -X POST 'https://api.example.com/api/v1/auth/keys/revoke' \
  -H 'Authorization: Bearer fba_mjfwAOKGkneKbFLai7NyGwejuBxyrogBcMCndiww8x0' \
  -H 'Content-Type: application/json' \
  -d '{"api_key": "fba_xxxxx"}'
```

## Troubleshooting

### Script doesn't run

```bash
# Check if executable
ls -l generate_api_key.sh

# Make executable
chmod +x generate_api_key.sh

# Run with explicit bash
bash generate_api_key.sh "My Key"
```

### No output or error

- Check if the API service is running
- Verify the API base URL is accessible
- Check network connectivity: `curl https://api.example.com/api/v1/health`

### Response parsing errors

- Ensure `jq` is installed
- Check API response manually:
```bash
curl -X POST 'https://api.example.com/api/v1/auth/keys/generate' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer fba_mjfwAOKGkneKbFLai7NyGwejuBxyrogBcMCndiww8x0' \
  -d '{"name": "Test", "rate_limit": 100}' | jq .
```

## Security Best Practices

1. **Never commit keys to version control**
   - Add API keys to `.gitignore`
   - Use environment variables for sensitive data

2. **Rotate tokens regularly**
   - Change the admin token periodically
   - Revoke unused keys

3. **Use rate limiting**
   - Set appropriate rate limits for each key
   - Monitor usage patterns

4. **Keep script secure**
   - Store in a protected location
   - Limit file permissions: `chmod 700 generate_api_key.sh`
   - Don't share with untrusted users

5. **Use HTTPS only**
   - Ensure API URLs use HTTPS
   - Verify SSL certificates in production

## Integration Examples

### GitHub Actions

Create `.github/workflows/generate-key.yml`:

```yaml
name: Generate API Key
on: workflow_dispatch

jobs:
  generate-key:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Generate API Key
        run: |
          bash generate_api_key.sh "GitHub Actions Integration"
```

### Docker

In your Dockerfile:

```dockerfile
RUN chmod +x /app/generate_api_key.sh
CMD bash /app/generate_api_key.sh "Docker Container"
```

### Cron Job

Generate a new key daily:

```bash
0 0 * * * /path/to/generate_api_key.sh "Daily Backup Key" 2>&1 | mail -s "API Key Generated" admin@example.com
```

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review API logs at the service
3. Verify admin token is current
4. Check network connectivity and API endpoint

---

**Version:** 1.0  
**Last Updated:** January 2025  
**Compatible With:** Fantasy Basketball API v1.0+
