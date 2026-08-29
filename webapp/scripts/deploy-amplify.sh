#!/usr/bin/env bash
#
# Zips webapp/site, injects config.js with the deployed API URL, uploads it to
# Amplify as a manual deployment and waits for the job to finish.
#
# Environment overrides:
#   AWS_PROFILE  aws profile to use (defaults to "default" outside GitHub Actions)
#   AWS_REGION   defaults to us-west-2
#   STACK_NAME   defaults to FantasyBasketballSiteStack
#   POLL_TIMEOUT seconds to wait for the Amplify job (default 900)
#
set -euo pipefail

PROFILE="${AWS_PROFILE:-}"
REGION="${AWS_REGION:-us-west-2}"
STACK_NAME="${STACK_NAME:-FantasyBasketballSiteStack}"
POLL_TIMEOUT="${POLL_TIMEOUT:-900}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SITE_DIR="$REPO_ROOT/webapp/site"
BUILD_DIR="$REPO_ROOT/webapp/dist/site"
ZIP_PATH="$REPO_ROOT/webapp/dist/fantasy-basketball-site.zip"

if [[ -z "$PROFILE" && "${GITHUB_ACTIONS:-}" != "true" ]]; then
  PROFILE="default"
fi

AWS_ARGS=(--region "$REGION")
if [[ -n "$PROFILE" ]]; then
  AWS_ARGS+=(--profile "$PROFILE")
fi

for tool in aws jq zip curl; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: $tool is required" >&2; exit 1; }
done

if [[ ! -d "$SITE_DIR" ]] || [[ -z "$(ls -A "$SITE_DIR" 2>/dev/null)" ]]; then
  echo "ERROR: $SITE_DIR is empty or missing - nothing to deploy" >&2
  exit 1
fi

get_output() {
  local key="$1"
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    "${AWS_ARGS[@]}" \
    --query "Stacks[0].Outputs[?OutputKey=='$key'].OutputValue | [0]" \
    --output text
}

APP_ID="$(get_output AmplifyAppId)"
BRANCH_NAME="$(get_output AmplifyBranchName)"
API_URL="$(get_output ApiUrl)"

for value in "$APP_ID" "$BRANCH_NAME" "$API_URL"; do
  if [[ -z "$value" || "$value" == "None" ]]; then
    echo "ERROR: could not read outputs from stack $STACK_NAME" >&2
    exit 1
  fi
done

# Frontend contract: window.FB_CONFIG.apiBaseUrl, no trailing slash.
API_BASE_URL="${API_URL%/}"

echo "==> Stack:  $STACK_NAME"
echo "    app:    $APP_ID"
echo "    branch: $BRANCH_NAME"
echo "    api:    $API_BASE_URL"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cp -R "$SITE_DIR"/. "$BUILD_DIR"/

cat > "$BUILD_DIR/config.js" <<CONFIG
window.FB_CONFIG = {
  apiBaseUrl: "$API_BASE_URL"
};
CONFIG

rm -f "$ZIP_PATH"
mkdir -p "$(dirname "$ZIP_PATH")"
(cd "$BUILD_DIR" && zip -qr "$ZIP_PATH" .)

DEPLOYMENT_JSON="$(aws amplify create-deployment \
  --app-id "$APP_ID" \
  --branch-name "$BRANCH_NAME" \
  "${AWS_ARGS[@]}")"

JOB_ID="$(jq -r '.jobId' <<<"$DEPLOYMENT_JSON")"
UPLOAD_URL="$(jq -r '.zipUploadUrl' <<<"$DEPLOYMENT_JSON")"

curl --fail --silent --show-error -T "$ZIP_PATH" "$UPLOAD_URL" >/dev/null

aws amplify start-deployment \
  --app-id "$APP_ID" \
  --branch-name "$BRANCH_NAME" \
  --job-id "$JOB_ID" \
  "${AWS_ARGS[@]}" >/dev/null

echo "==> Started Amplify deployment $JOB_ID for app $APP_ID branch $BRANCH_NAME"

DEADLINE=$(( SECONDS + POLL_TIMEOUT ))
STATUS="PENDING"
while (( SECONDS < DEADLINE )); do
  STATUS="$(aws amplify get-job \
    --app-id "$APP_ID" \
    --branch-name "$BRANCH_NAME" \
    --job-id "$JOB_ID" \
    "${AWS_ARGS[@]}" \
    --query 'job.summary.status' \
    --output text)"

  case "$STATUS" in
    SUCCEED)
      echo "==> Amplify job $JOB_ID succeeded"
      echo "    https://$BRANCH_NAME.$(get_output AmplifyDefaultDomain)"
      echo "    $(get_output WebsiteUrl)"
      exit 0
      ;;
    FAILED|CANCELLED|CANCELLING)
      echo "ERROR: Amplify job $JOB_ID finished with status $STATUS" >&2
      aws amplify get-job \
        --app-id "$APP_ID" \
        --branch-name "$BRANCH_NAME" \
        --job-id "$JOB_ID" \
        "${AWS_ARGS[@]}" >&2 || true
      exit 1
      ;;
    *)
      echo "    job $JOB_ID status: $STATUS"
      sleep "$POLL_INTERVAL"
      ;;
  esac
done

echo "ERROR: timed out after ${POLL_TIMEOUT}s waiting for Amplify job $JOB_ID (last status: $STATUS)" >&2
exit 1
