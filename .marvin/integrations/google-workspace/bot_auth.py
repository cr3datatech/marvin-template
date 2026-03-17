#!/usr/bin/env python3
"""
Two-step Google OAuth setup for Groot bots (headless-friendly).

Step 1 — get the URL:
    python bot_auth.py url

Step 2 — exchange the code:
    python bot_auth.py exchange <code>
"""

import os
import sys
from pathlib import Path

TOKEN_PATH = Path.home() / ".config" / "groot" / "google_token.json"

SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
])


def _load_credentials():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    if not client_id or not client_secret:
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GOOGLE_OAUTH_CLIENT_ID="):
                    client_id = line.split("=", 1)[1].strip()
                elif line.startswith("GOOGLE_OAUTH_CLIENT_SECRET="):
                    client_secret = line.split("=", 1)[1].strip()

    if not client_id or not client_secret:
        print("ERROR: credentials not found in env or .env file")
        sys.exit(1)

    return client_id, client_secret


def cmd_url():
    """Print the auth URL. No PKCE — code can be exchanged later."""
    client_id, _ = _load_credentials()
    scope_encoded = SCOPES.replace(" ", "+").replace(":", "%3A").replace("/", "%2F")
    url = (
        "https://accounts.google.com/o/oauth2/auth"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob"
        f"&scope={scope_encoded}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    print(url)


def cmd_exchange(code: str):
    """Exchange an auth code for tokens and save to TOKEN_PATH."""
    import urllib.request
    import urllib.parse
    import json

    client_id, client_secret = _load_credentials()

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR: token exchange failed: {body}")
        sys.exit(1)

    # Build token file in google-auth format
    token = {
        "token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES.split(),
        "expiry": None,
    }

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(token, indent=2))
    print(f"Token saved to {TOKEN_PATH}")
    print("Restart groot-telegram and groot-slack to activate Google tools.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "url":
        cmd_url()
    elif command == "exchange" and len(sys.argv) == 3:
        cmd_exchange(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
