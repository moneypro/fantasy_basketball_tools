#!/usr/bin/env bash
#
# Builds the deployment bundle for the fantasy basketball API Lambda.
#
# Layout produced in webapp/lambda/build:
#   handler.py + anything else from webapp/lambda/api/
#   predict/ common/ utils/ config.py   (copied from the repo root)
#   third-party packages from webapp/lambda/api/requirements.txt
#
# Environment overrides:
#   PYTHON_BIN            python interpreter used to drive pip (default: python3)
#   FB_ALLOW_PLACEHOLDER  when 1, write a stub handler.py if the backend source
#                         is not present yet (useful for `cdk synth` only)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC_DIR="$REPO_ROOT/webapp/lambda/api"
BUILD_DIR="$REPO_ROOT/webapp/lambda/build"
REQUIREMENTS="$SRC_DIR/requirements.txt"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Repo packages the handler reuses.
SHARED_PACKAGES=(predict common utils)
SHARED_FILES=(config.py)

echo "==> Building lambda bundle in $BUILD_DIR"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# --- dependencies ---------------------------------------------------------
# Installed first so that repo code copied afterwards always wins if a
# third-party package happens to ship a colliding top-level module name.
if [[ -f "$REQUIREMENTS" ]]; then
  echo "==> Installing dependencies from $REQUIREMENTS"
  if ! "$PYTHON_BIN" -m pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    --upgrade \
    --target "$BUILD_DIR" \
    --platform manylinux2014_x86_64 \
    --python-version 3.12 \
    --only-binary=:all: \
    -r "$REQUIREMENTS"; then
    echo "    manylinux-pinned install failed; retrying without platform pins"
    echo "    (only safe on a linux/x86_64 builder - CI runs ubuntu-latest)"
    "$PYTHON_BIN" -m pip install \
      --disable-pip-version-check \
      --no-cache-dir \
      --upgrade \
      --target "$BUILD_DIR" \
      -r "$REQUIREMENTS"
  fi
else
  echo "    warning: $REQUIREMENTS not found, skipping dependency install"
fi

# --- security patch: espn_api's own access-denied exception ---------------
# espn-api==0.45.1 builds its 401 exception out of the LIVE session cookies:
#   raise ESPNAccessDenied(f"League {id} cannot be accessed with "
#                           f"espn_s2={self.cookies.get('espn_s2')} and "
#                           f"swid={self.cookies.get('SWID')}")
# (webapp/lambda/build/espn_api/requests/espn_requests.py). That means the
# league owner's ESPN session lives inside the exception's own message the
# moment ESPN answers 401 -- before handler.py's _redact()/fixed-error-message
# layer (see webapp/lambda/api/handler.py) ever gets a chance to touch it.
# _redact() stays as defense in depth for anything else that might leak
# credentials into a log or response, but the cookie should never be
# assembled into a string in the first place. Patch it out of the installed
# package at build time.
#
# This MUST fail the build loudly, not silently no-op, if a future espn-api
# version changes this line -- see the PATTERN check in the inline patch
# script below.
ESPN_REQUESTS_FILE="$BUILD_DIR/espn_api/requests/espn_requests.py"
if [[ -f "$REQUIREMENTS" ]] && grep -q '^espn-api' "$REQUIREMENTS"; then
  if [[ ! -f "$ESPN_REQUESTS_FILE" ]]; then
    echo "ERROR: espn-api is in $REQUIREMENTS but $ESPN_REQUESTS_FILE" >&2
    echo "       does not exist after pip install. Package layout changed?" >&2
    exit 1
  fi

  echo "==> Patching espn_api's ESPNAccessDenied to drop the session cookies"
  "$PYTHON_BIN" - "$ESPN_REQUESTS_FILE" <<'PATCH_ESPN_REQUESTS'
import re
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fh:
    src = fh.read()

# Matches the exact vulnerable statement in espn-api==0.45.1. Deliberately
# specific (not just "raise ESPNAccessDenied(...)") so that if a dependency
# bump reflows, renames, or otherwise changes this line, the pattern stops
# matching and the build fails below instead of silently shipping the
# original credential-leaking code.
PATTERN = re.compile(
    r"raise ESPNAccessDenied\(f\"League \{self\.league_id\} cannot be accessed "
    r"with espn_s2=\{self\.cookies\.get\('espn_s2'\)\} and "
    r"swid=\{self\.cookies\.get\('SWID'\)\}\"\)"
)

REPLACEMENT = (
    "raise ESPNAccessDenied("
    'f"League {self.league_id} cannot be accessed: ESPN denied the request '
    '(credentials rejected or expired)")'
)

matches = PATTERN.findall(src)
if len(matches) != 1:
    sys.stderr.write(
        "ERROR: expected exactly 1 occurrence of the credential-leaking "
        "ESPNAccessDenied f-string in\n"
        f"       {path}\n"
        f"       found {len(matches)}. espn-api's source has changed "
        "(version bump?) in a way this\n"
        "       patch does not recognise. Update the PATTERN in "
        "webapp/scripts/build-lambda.sh to\n"
        "       match the new line before proceeding -- until then, the "
        "live ESPN session cookie\n"
        "       would ship inside this exception's message.\n"
    )
    sys.exit(1)

patched = PATTERN.sub(REPLACEMENT, src, count=1)

# Belt and suspenders: the substitution above is the only place in this file
# that reads the raw cookie values out of self.cookies for use in a message;
# confirm it actually left no such reference behind.
if "cookies.get('espn_s2')" in patched or "cookies.get('SWID')" in patched:
    sys.stderr.write(
        "ERROR: patch replaced the known line but another cookies.get('espn_s2'"
        "'/'SWID') reference remains in the file; aborting rather than shipping "
        "a partial fix.\n"
    )
    sys.exit(1)

with open(path, "w", encoding="utf-8") as fh:
    fh.write(patched)

print(f"    patched {path}")
PATCH_ESPN_REQUESTS

  # The patched file must still be valid Python before it ships.
  "$PYTHON_BIN" -m py_compile "$ESPN_REQUESTS_FILE"
  rm -rf "$BUILD_DIR/espn_api/requests/__pycache__"
else
  echo "    espn-api not in $REQUIREMENTS; skipping ESPNAccessDenied patch"
fi

# --- shared repo code -----------------------------------------------------
for pkg in "${SHARED_PACKAGES[@]}"; do
  if [[ -d "$REPO_ROOT/$pkg" ]]; then
    echo "    copying package $pkg/"
    cp -R "$REPO_ROOT/$pkg" "$BUILD_DIR/"
  else
    echo "    warning: repo package $pkg/ not found, skipping"
  fi
done

for file in "${SHARED_FILES[@]}"; do
  if [[ -f "$REPO_ROOT/$file" ]]; then
    echo "    copying $file"
    cp "$REPO_ROOT/$file" "$BUILD_DIR/"
  else
    echo "    warning: repo file $file not found, skipping"
  fi
done

# --- handler source -------------------------------------------------------
# Copied last so the backend's files win over anything above.
if [[ -d "$SRC_DIR" ]] && [[ -n "$(ls -A "$SRC_DIR" 2>/dev/null)" ]]; then
  echo "    copying handler source from webapp/lambda/api/"
  cp -R "$SRC_DIR"/. "$BUILD_DIR"/
else
  echo "    warning: $SRC_DIR is empty or missing"
fi

# Byte-code and OS cruft only; dist-info is left alone because some packages
# read their own metadata at import time.
find "$BUILD_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$BUILD_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete 2>/dev/null || true

# --- sanity check ---------------------------------------------------------
if [[ ! -f "$BUILD_DIR/handler.py" ]]; then
  if [[ "${FB_ALLOW_PLACEHOLDER:-0}" == "1" ]]; then
    echo "    warning: no handler.py found - writing PLACEHOLDER (synth only, do not deploy)"
    cat > "$BUILD_DIR/handler.py" <<'PLACEHOLDER'
"""Placeholder handler. Replaced by webapp/lambda/api/handler.py at build time."""


def handler(event, context):
    return {
        "statusCode": 503,
        "headers": {"content-type": "application/json"},
        "body": '{"error": "lambda bundle was built without a handler"}',
    }
PLACEHOLDER
  else
    echo "ERROR: $BUILD_DIR/handler.py is missing." >&2
    echo "       Expected webapp/lambda/api/handler.py to exist." >&2
    echo "       Set FB_ALLOW_PLACEHOLDER=1 to build a stub for cdk synth." >&2
    exit 1
  fi
fi

BUNDLE_KB="$(du -sk "$BUILD_DIR" | cut -f1)"
echo "==> Lambda bundle ready: $BUILD_DIR ($(du -sh "$BUILD_DIR" | cut -f1))"
if (( BUNDLE_KB > 235000 )); then
  echo "    warning: bundle is close to (or over) the 250 MB unzipped Lambda limit" >&2
fi
