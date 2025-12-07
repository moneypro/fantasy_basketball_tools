#!/bin/bash

# Generate Fantasy Basketball API Key
# Usage: ./generate_api_key.sh "My API Key Description"
# or: ./generate_api_key.sh "My API Key Description" "https://custom-domain.com"

set -e

# Configuration
API_BASE_URL="${2:-https://hcheng.ngrok.app}"
ADMIN_TOKEN="1YecDR4wYXp4l64B1s0SZFrInNKyhWeIrvTUO7lgIho"
KEY_DESCRIPTION="${1:-API Key}"
RATE_LIMIT="${3:-100}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Fantasy Basketball API Key Generator${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Validate inputs
if [ -z "$1" ]; then
    echo -e "${YELLOW}⚠️  No description provided. Using default: 'API Key'${NC}"
    KEY_DESCRIPTION="API Key"
fi

# Display configuration
echo -e "${BLUE}Configuration:${NC}"
echo -e "  API Base URL:   ${BLUE}${API_BASE_URL}${NC}"
echo -e "  Description:    ${BLUE}${KEY_DESCRIPTION}${NC}"
echo -e "  Rate Limit:     ${BLUE}${RATE_LIMIT} requests/period${NC}"
echo ""

# Make the API request
echo -e "${BLUE}Generating API key...${NC}"
echo ""

RESPONSE=$(curl -s -X POST \
  "${API_BASE_URL}/api/v1/auth/keys/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d "{
    \"name\": \"${KEY_DESCRIPTION}\",
    \"rate_limit\": ${RATE_LIMIT}
  }")

# Parse response - handle potential jq errors gracefully
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq is not installed${NC}"
    echo "Please install jq: brew install jq (macOS) or sudo apt-get install jq (Linux)"
    exit 1
fi

STATUS=$(echo "$RESPONSE" | jq -r '.status // "error"' 2>/dev/null || echo "error")
API_KEY=$(echo "$RESPONSE" | jq -r '.data.api_key // empty' 2>/dev/null || echo "")
ERROR_MESSAGE=$(echo "$RESPONSE" | jq -r '.message // empty' 2>/dev/null || echo "")

# Handle response
if [ "$STATUS" = "success" ] && [ -n "$API_KEY" ]; then
    echo -e "${GREEN}✅ API Key Generated Successfully!${NC}"
    echo ""
    echo -e "${YELLOW}════════════════════════════════════════${NC}"
    echo -e "${GREEN}API Key:${NC}"
    echo -e "${BLUE}${API_KEY}${NC}"
    echo -e "${YELLOW}════════════════════════════════════════${NC}"
    echo ""
    echo -e "${RED}⚠️  IMPORTANT: Save this key now - you won't see it again!${NC}"
    echo ""
    echo -e "${BLUE}Key Details:${NC}"
    echo -e "  Name:        ${BLUE}${KEY_DESCRIPTION}${NC}"
    echo -e "  Rate Limit:  ${BLUE}${RATE_LIMIT} requests${NC}"
    echo ""
    echo -e "${BLUE}Usage Example:${NC}"
    echo -e "  curl -X GET 'https://your-api.com/api/v1/health?api_key=${API_KEY}'"
    echo ""
    echo -e "${BLUE}Or in request headers:${NC}"
    echo -e "  curl -X GET 'https://your-api.com/api/v1/health' \\"
    echo -e "    -H 'X-API-Key: ${API_KEY}'"
    echo ""
else
    echo -e "${RED}❌ Failed to generate API key${NC}"
    echo ""
    if [ -n "$ERROR_MESSAGE" ]; then
        echo -e "${RED}Error: ${ERROR_MESSAGE}${NC}"
    fi
    echo -e "${RED}Response: ${RESPONSE}${NC}"
    exit 1
fi
