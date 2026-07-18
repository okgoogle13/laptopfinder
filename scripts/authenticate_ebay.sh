#!/bin/bash
# scripts/authenticate_ebay.sh
# eBay OAuth authentication wrapper supporting both User-level (Trading API Watchlist)
# and Application-level (public Browse API) token flows.

# If EBAY_CLIENT_ID starts with op:// (or is unset) and .env exists, re-exec via op run
if [ -z "$EBAY_CLIENT_ID" ] || [[ "$EBAY_CLIENT_ID" == op://* ]]; then
    if [ -f .env ] && command -v op >/dev/null 2>&1; then
        exec op run --env-file=.env -- "$0" "$@"
    elif [ -f .env ]; then
        set -a
        source .env
        set +a
    fi
fi

if [ -z "$EBAY_CLIENT_ID" ] || [ -z "$EBAY_CLIENT_SECRET" ]; then
    echo "Error: EBAY_CLIENT_ID or EBAY_CLIENT_SECRET not found in environment/.env" >&2
    exit 1
fi

# Determine token URL based on environment/base URL
API_BASE="https://api.ebay.com"
if [ "$EBAY_ENVIRONMENT" = "sandbox" ]; then
    API_BASE="https://api.sandbox.ebay.com"
elif [ -n "$EBAY_API_BASE_URL" ]; then
    API_BASE="$EBAY_API_BASE_URL"
fi
TOKEN_URL="${API_BASE}/identity/v1/oauth2/token"

PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# Parse arguments / route flows
if [ "$1" = "--user" ] || [ "$1" = "--login" ] || [ "$1" = "--browser" ] || [ "$1" = "--refresh" ] || [[ "$1" == http://* ]] || [[ "$1" == https://* ]] || [[ "$1" == *code=* ]]; then
    exec "$PYTHON_BIN" scripts/authenticate_ebay_user.py "$@"
elif [ "$1" = "--app" ] || [ "$1" = "--client" ] || [ "$1" = "--client-credentials" ]; then
    echo "Authenticating application-level token with eBay at ${TOKEN_URL}..."
else
    # Default behavior when called without args:
    # If .ebay_refresh_token exists, refresh User-level token so Trading API & Browse API both work.
    if [ -f .ebay_refresh_token ]; then
        echo "Found existing .ebay_refresh_token. Refreshing User-level access token..."
        exec "$PYTHON_BIN" scripts/authenticate_ebay_user.py --refresh
    fi
    echo "No .ebay_refresh_token found or --app specified. Requesting Application-level token..."
    echo "ℹ️ Note: App tokens allow public Browse API queries but cannot read personal Trading API Watchlist."
    echo "   To log in for personal Watchlist access, run: bash scripts/authenticate_ebay.sh --user"
fi

# Application-level Client Credentials Grant
CREDENTIALS=$(printf "%s:%s" "${EBAY_CLIENT_ID}" "${EBAY_CLIENT_SECRET}" | base64 | tr -d '\n\r')

RESPONSE=$(curl -s -X POST "${TOKEN_URL}" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H "Authorization: Basic ${CREDENTIALS}" \
  -d 'grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope')

TOKEN=$(echo "$RESPONSE" | jq -r .access_token)

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "✅ Application authentication successful!"
    echo "$TOKEN" > .ebay_access_token
    echo "Token securely saved to .ebay_access_token (Valid for 2 hours)"
else
    echo "❌ Authentication failed!" >&2
    echo "$RESPONSE" >&2
    exit 1
fi
