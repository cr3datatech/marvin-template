#!/usr/bin/env python3
"""
Two-step Google OAuth setup for Groot bots (headless-friendly).

Automatic flow (recommended):
    python bot_auth.py auto

Manual flow (if auto doesn't work):
    Step 1 — get the URL:
        python bot_auth.py url

    Step 2 — exchange the code:
        python bot_auth.py exchange <code>
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

TOKEN_PATH = Path.home() / ".config" / "groot" / "google_token.json"
REDIRECT_URI = "http://localhost:8585"

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


def _build_auth_url(client_id, login_hint=None):
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


def _exchange_code(code, client_id, client_secret):
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR: token exchange failed: {body}")
        sys.exit(1)


def _save_token(token_data, client_id, client_secret):
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


def cmd_auto(login_hint="cr3data.tech@gmail.com"):
    """Start a local server, open browser, capture code automatically."""
    import http.server
    import threading
    import webbrowser

    client_id, client_secret = _load_credentials()
    auth_url = _build_auth_url(client_id, login_hint=login_hint)

    captured = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                captured["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Auth complete! You can close this tab.</h2>")
            elif "error" in params:
                captured["error"] = params["error"][0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(f"<h2>Error: {params['error'][0]}</h2>".encode())
            else:
                self.send_response(400)
                self.end_headers()

        def log_message(self, *args):
            pass  # silence request logs

    server = http.server.HTTPServer(("localhost", 8585), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    print(f"Opening browser for Google auth ({login_hint})...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for callback on http://localhost:8585 ...")
    while "code" not in captured and "error" not in captured:
        import time
        time.sleep(0.5)

    server.shutdown()

    if "error" in captured:
        print(f"ERROR: {captured['error']}")
        sys.exit(1)

    print("Code received, exchanging for tokens...")
    token_data = _exchange_code(captured["code"], client_id, client_secret)
    _save_token(token_data, client_id, client_secret)


def cmd_url(login_hint="cr3data.tech@gmail.com"):
    """Print the auth URL for manual use."""
    client_id, _ = _load_credentials()
    print(_build_auth_url(client_id, login_hint=login_hint))


def cmd_exchange(code: str):
    """Exchange an auth code for tokens and save to TOKEN_PATH."""
    client_id, client_secret = _load_credentials()
    token_data = _exchange_code(code, client_id, client_secret)
    _save_token(token_data, client_id, client_secret)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    if command == "auto":
        login_hint = sys.argv[2] if len(sys.argv) > 2 else "cr3data.tech@gmail.com"
        cmd_auto(login_hint)
    elif command == "url":
        login_hint = sys.argv[2] if len(sys.argv) > 2 else "cr3data.tech@gmail.com"
        cmd_url(login_hint)
    elif command == "exchange" and len(sys.argv) == 3:
        cmd_exchange(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
