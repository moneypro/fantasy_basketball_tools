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
