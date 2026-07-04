#!/bin/bash

# Load environment variables from .env
set -a
source .env
set +a

if [ -z "$EBAY_CLIENT_ID" ] || [ -z "$EBAY_CLIENT_SECRET" ]; then
    echo "Error: EBAY_CLIENT_ID or EBAY_CLIENT_SECRET not found in .env"
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
echo "Authenticating with eBay at ${TOKEN_URL}..."

# Combine and Base64 encode the credentials without trailing newlines
CREDENTIALS=$(printf "%s:%s" "${EBAY_CLIENT_ID}" "${EBAY_CLIENT_SECRET}" | base64 | tr -d '\n\r')

# Request the Application Access Token
RESPONSE=$(curl -s -X POST "${TOKEN_URL}" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -H "Authorization: Basic ${CREDENTIALS}" \
  -d 'grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope')

# Extract token (requires 'jq' to be installed)
TOKEN=$(echo $RESPONSE | jq -r .access_token)

if [ "$TOKEN" != "null" ] && [ -n "$TOKEN" ]; then
    echo "✅ Authentication successful!"
    # Save the token to a hidden local file
    echo "$TOKEN" > .ebay_access_token
    echo "Token securely saved to .ebay_access_token (Valid for 2 hours)"
else
    echo "❌ Authentication failed!"
    echo "$RESPONSE"
    exit 1
fi
