#!/usr/bin/env python3
"""
scripts/refresh_ebay_user.py

Refreshes an eBay User Access Token using a saved Refresh Token.
Reads `.ebay_refresh_token` and writes to `.ebay_access_token`.
"""

import base64
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request


def main():
    client_id = os.environ.get("EBAY_CLIENT_ID")
    client_secret = os.environ.get("EBAY_CLIENT_SECRET")

    if not all([client_id, client_secret]):
        print("ERROR: EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set.", file=sys.stderr)
        sys.exit(1)

    refresh_token_path = pathlib.Path(".ebay_refresh_token")
    if not refresh_token_path.exists():
        print("ERROR: .ebay_refresh_token not found.", file=sys.stderr)
        sys.exit(1)

    refresh_token = refresh_token_path.read_text().strip()

    # Determine environment
    env = os.environ.get("EBAY_ENVIRONMENT", "production").lower()
    if env == "sandbox":
        api_base = "https://api.sandbox.ebay.com"
    else:
        api_base = os.environ.get("EBAY_API_BASE_URL", "https://api.ebay.com")

    token_url = f"{api_base}/identity/v1/oauth2/token"
    scopes = "https://api.ebay.com/oauth/api_scope"

    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    b64_creds = base64.b64encode(credentials).decode("utf-8")

    body_params = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": scopes,
    }
    body_data = urllib.parse.urlencode(body_params).encode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {b64_creds}",
    }

    req = urllib.request.Request(token_url, data=body_data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"ERROR: Token refresh failed with HTTP {e.code}", file=sys.stderr)
        error_body = e.read().decode("utf-8", errors="ignore")
        print(error_body, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Token refresh failed: {e}", file=sys.stderr)
        sys.exit(1)

    access_token = response_data.get("access_token")

    if not access_token:
        print("ERROR: Response did not contain an access_token.", file=sys.stderr)
        print(json.dumps(response_data, indent=2), file=sys.stderr)
        sys.exit(1)

    with open(".ebay_access_token", "w") as f:
        f.write(access_token)
    
    print("✅ Successfully refreshed User Access Token.")


if __name__ == "__main__":
    main()
