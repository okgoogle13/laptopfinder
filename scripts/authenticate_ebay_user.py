#!/usr/bin/env python3
"""
scripts/authenticate_ebay_user.py

Two-step, non-interactive eBay OAuth flow.

  Step 1 (no args):  Opens the consent page in your browser. That's it.
  Step 2 (with URL): Pass the callback URL as an argument to exchange it
                     for tokens.

Usage:
  op run --env-file=.env -- .venv/bin/python scripts/authenticate_ebay_user.py
  op run --env-file=.env -- .venv/bin/python scripts/authenticate_ebay_user.py "https://auth.ebay.com/auth/oauth2?code=..."
"""

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser


def _get_config():
    client_id = os.environ.get("EBAY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "").strip()
    ru_name = os.environ.get("EBAY_RU_NAME", "").strip()

    if not all([client_id, client_secret, ru_name]):
        print("ERROR: EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, and EBAY_RU_NAME must be set.", file=sys.stderr)
        sys.exit(1)

    env = os.environ.get("EBAY_ENVIRONMENT", "production").strip().lower()
    if env == "sandbox":
        api_base = "https://api.sandbox.ebay.com"
    else:
        api_base = os.environ.get("EBAY_API_BASE_URL", "https://api.ebay.com").strip()

    return client_id, client_secret, ru_name, api_base


def step1_open_browser():
    """Open the eBay consent page. No terminal output of the URL."""
    client_id, _, ru_name, api_base = _get_config()

    env = os.environ.get("EBAY_ENVIRONMENT", "production").strip().lower()
    auth_base = ("https://auth.sandbox.ebay.com/oauth2/authorize"
                 if env == "sandbox"
                 else "https://auth.ebay.com/oauth2/authorize")

    scopes = "https://api.ebay.com/oauth/api_scope"
    params = {
        "client_id": client_id,
        "redirect_uri": ru_name,
        "response_type": "code",
        "scope": scopes,
    }
    consent_url = f"{auth_base}?{urllib.parse.urlencode(params)}"

    webbrowser.open(consent_url)
    print("✓ Browser opened with eBay consent page.")
    print()
    print("  1. Log in to your eBay account")
    print("  2. Click 'I agree' / 'Agree and Continue'")
    print("  3. You'll be redirected to a page (may look blank/broken)")
    print("  4. Copy the ENTIRE URL from the address bar")
    print("  5. Run this command, pasting the URL at the end:")
    print()
    print('  op run --env-file=.env -- .venv/bin/python scripts/authenticate_ebay_user.py "PASTE_URL_HERE"')


def step2_exchange(callback_url):
    """Exchange the callback URL's auth code for tokens."""
    client_id, client_secret, ru_name, api_base = _get_config()
    token_url = f"{api_base}/identity/v1/oauth2/token"

    parsed = urllib.parse.urlparse(callback_url)
    qs = urllib.parse.parse_qs(parsed.query)
    code = qs.get("code", [None])[0]

    if not code:
        print("ERROR: No 'code' parameter found in the URL.", file=sys.stderr)
        print(f"  URL: {callback_url[:200]}", file=sys.stderr)
        sys.exit(1)

    print(f"Found auth code: {code[:20]}...")
    print("Exchanging for tokens...")

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ru_name,
    }).encode()

    req = urllib.request.Request(
        token_url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {creds}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        print(e.read().decode("utf-8", errors="ignore"), file=sys.stderr)
        sys.exit(1)

    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        print("ERROR: No access_token in response.", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)

    with open(".ebay_access_token", "w") as f:
        f.write(access_token)

    if refresh_token:
        with open(".ebay_refresh_token", "w") as f:
            f.write(refresh_token)

    print("✅ Token saved to .ebay_access_token")
    if refresh_token:
        print("✅ Refresh token saved to .ebay_refresh_token (valid ~18 months)")


def step_refresh():
    """Refresh the access token using the saved refresh token."""
    if not os.path.exists(".ebay_refresh_token"):
        print("ERROR: .ebay_refresh_token not found. Run step 1 to log in via browser.", file=sys.stderr)
        sys.exit(1)

    with open(".ebay_refresh_token", "r") as f:
        refresh_token = f.read().strip()

    if not refresh_token:
        print("ERROR: .ebay_refresh_token is empty. Run step 1 to log in via browser.", file=sys.stderr)
        sys.exit(1)

    client_id, client_secret, ru_name, api_base = _get_config()
    token_url = f"{api_base}/identity/v1/oauth2/token"

    print("Refreshing user access token via refresh_token...")
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://api.ebay.com/oauth/api_scope",
    }).encode()

    req = urllib.request.Request(
        token_url,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {creds}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code}", file=sys.stderr)
        print(e.read().decode("utf-8", errors="ignore"), file=sys.stderr)
        sys.exit(1)

    access_token = data.get("access_token")
    new_refresh_token = data.get("refresh_token")

    if not access_token:
        print("ERROR: No access_token in response.", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)

    with open(".ebay_access_token", "w") as f:
        f.write(access_token)

    if new_refresh_token:
        with open(".ebay_refresh_token", "w") as f:
            f.write(new_refresh_token)

    print("✅ User token refreshed and saved to .ebay_access_token (Valid for 2 hours)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg in ("--refresh", "refresh"):
            step_refresh()
        elif arg.startswith("http://") or arg.startswith("https://") or "code=" in arg:
            step2_exchange(arg)
        elif arg in ("--login", "--browser", "login"):
            step1_open_browser()
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            print("Usage: authenticate_ebay_user.py [--refresh | --login | <callback_url>]", file=sys.stderr)
            sys.exit(1)
    else:
        # Default behavior: if refresh token exists, refresh; otherwise open browser
        if os.path.exists(".ebay_refresh_token"):
            step_refresh()
        else:
            step1_open_browser()

