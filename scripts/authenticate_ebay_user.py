#!/usr/bin/env python3
"""
scripts/authenticate_ebay_user.py

Generates an eBay Consent URL, asks the user to visit it and authenticate,
and then exchanges the resulting authorization code for an Access Token
and a Refresh Token. Saves them to `.ebay_access_token` and `.ebay_refresh_token`.

Requires:
  - EBAY_CLIENT_ID
  - EBAY_CLIENT_SECRET
  - EBAY_RU_NAME
in the environment (usually injected via op run).
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request


def main():
    client_id = os.environ.get("EBAY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "").strip()
    ru_name = os.environ.get("EBAY_RU_NAME", "").strip()

    if not all([client_id, client_secret, ru_name]):
        print("ERROR: EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, and EBAY_RU_NAME must be set.", file=sys.stderr)
        print("Make sure you run this via: op run --env-file=.env -- .venv/bin/python scripts/authenticate_ebay_user.py", file=sys.stderr)
        sys.exit(1)

    # Determine environment
    env = os.environ.get("EBAY_ENVIRONMENT", "production").strip().lower()
    if env == "sandbox":
        auth_base = "https://auth.sandbox.ebay.com/oauth2/authorize"
        api_base = "https://api.sandbox.ebay.com"
    else:
        auth_base = "https://auth.ebay.com/oauth2/authorize"
        api_base = os.environ.get("EBAY_API_BASE_URL", "https://api.ebay.com").strip()

    token_url = f"{api_base}/identity/v1/oauth2/token"

    # Scopes needed for Watchlist (and general Browse/Trading API read)
    scopes = "https://api.ebay.com/oauth/api_scope"

    # 1. Build Consent URL
    params = {
        "client_id": client_id,
        "redirect_uri": ru_name,
        "response_type": "code",
        "scope": scopes,
    }
    consent_url = f"{auth_base}?{urllib.parse.urlencode(params)}"

    print("=" * 80)
    print("ACTION REQUIRED: eBay User Authentication")
    print("=" * 80)
    print("Please visit the following URL in your browser, log in to your eBay account,")
    print("and click 'I agree' to grant application access:\n")
    print(consent_url)
    print("\nAfter you agree, eBay will redirect you to a blank page or an error page.")
    print("Copy the ENTIRE URL of that page from your browser's address bar and paste it below.")
    print("-" * 80)

    # 2. Get redirected URL from user
    redirected_url = input("Paste the redirected URL here:\n> ").strip()

    if not redirected_url:
        print("No URL provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    # 3. Extract the authorization code
    parsed_url = urllib.parse.urlparse(redirected_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    code = query_params.get("code", [None])[0]

    if not code:
        print("ERROR: Could not find 'code' parameter in the provided URL.", file=sys.stderr)
        sys.exit(1)

    print("\nExchanging authorization code for tokens...")
    print(f"[DEBUG] Calling token URL: {token_url}")

    # 4. Exchange code for token
    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    b64_creds = base64.b64encode(credentials).decode("utf-8")

    body_params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ru_name,
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
        print(f"ERROR: Token exchange failed with HTTP {e.code}", file=sys.stderr)
        error_body = e.read().decode("utf-8", errors="ignore")
        print(error_body, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Token exchange failed: {e}", file=sys.stderr)
        sys.exit(1)

    access_token = response_data.get("access_token")
    refresh_token = response_data.get("refresh_token")

    if not access_token:
        print("ERROR: Response did not contain an access_token.", file=sys.stderr)
        print(json.dumps(response_data, indent=2), file=sys.stderr)
        sys.exit(1)

    # 5. Save tokens
    with open(".ebay_access_token", "w") as f:
        f.write(access_token)
    
    if refresh_token:
        with open(".ebay_refresh_token", "w") as f:
            f.write(refresh_token)
        print("✅ Successfully generated and saved User Access Token & Refresh Token.")
        print("The refresh token is valid for 18 months and will be used to automatically renew the access token.")
    else:
        print("✅ Successfully generated User Access Token (but no refresh token was provided by eBay).")


if __name__ == "__main__":
    main()
