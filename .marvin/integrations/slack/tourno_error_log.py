#!/usr/bin/env python3
"""
Tourno Error Log Analyser

Runs every Tuesday and Thursday at 9am Helsinki time.
- Checks Google Drive for error_log files in tourno_error_logs/frontend and backend
- Reads, parses and deduplicates errors
- Sends summary to Slack DM and Telegram
- Renames processed files to error_log_YYYYMMDDHHmm

Cron: 3 9 * * 2,4 TZ=Europe/Helsinki
"""

import json
import logging
import os
import re
import requests
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
GROOT_ROOT = SCRIPT_DIR.parent.parent.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(GROOT_ROOT / ".env")

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_TOKEN_PATH = Path.home() / ".config" / "groot" / "google_token.json"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/drive"]

FRONTEND_FOLDER_ID = "1UEaoIvi98G__7L03rpeRF6cN-r2Phsdo"
BACKEND_FOLDER_ID = "141Q31L5FaZLwWqR0SOId-U085ASi8iVQ"

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_USER_ID = "U083MA2K6US"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = "1684738468"


# ── Google auth ────────────────────────────────────────────────────────────────

def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), GOOGLE_SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data = json.loads(GOOGLE_TOKEN_PATH.read_text())
            token_data["token"] = creds.token
            token_data["expiry"] = creds.expiry.isoformat() if creds.expiry else ""
            GOOGLE_TOKEN_PATH.write_text(json.dumps(token_data, indent=2))
            logger.info("Google token refreshed.")
        else:
            raise RuntimeError("Google credentials invalid — re-run OAuth flow via Groot.")
    return creds


# ── Drive helpers ──────────────────────────────────────────────────────────────

def find_error_log(drive_service, folder_id: str) -> dict | None:
    result = drive_service.files().list(
        q=f"name = 'error_log' and '{folder_id}' in parents and trashed = false",
        fields="files(id, name, size)",
        pageSize=1,
    ).execute()
    files = result.get("files", [])
    return files[0] if files else None


def read_file_content(drive_service, file_id: str) -> str:
    content = drive_service.files().get_media(fileId=file_id).execute()
    return content.decode("utf-8", errors="replace")


def rename_file(drive_service, file_id: str, timestamp: str):
    new_name = f"error_log_{timestamp}"
    drive_service.files().update(fileId=file_id, body={"name": new_name}).execute()
    logger.info(f"Renamed file {file_id} → {new_name}")


# ── Log parsing ────────────────────────────────────────────────────────────────

def parse_log(content: str):
    line_pattern = re.compile(
        r"\[\d{2}-\w{3}-\d{4} [\d:]+[^\]]*\] (PHP \w[\w ]+?):\s+(.+?)(?:\s+in\s+(/[^\s]+)\s+on\s+line\s+(\d+))?$"
    )
    raw_errors: Counter = Counter()
    dates = []

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        date_match = re.match(r"\[(\d{2}-\w{3}-\d{4})", line)
        if date_match:
            dates.append(date_match.group(1))
        m = line_pattern.match(line)
        if not m:
            continue
        severity = m.group(1).strip()
        message = m.group(2).strip()
        file_path = m.group(3) or ""
        line_no = m.group(4) or ""
        file_short = re.sub(r"^/home/[^/]+/public_html/", "", file_path)
        raw_errors[(severity, message, file_short, line_no)] += 1

    errors = []
    for (severity, message, file_short, line_no), count in raw_errors.most_common():
        location = f"{file_short}:{line_no}" if file_short else ""
        errors.append({"count": count, "severity": severity, "message": message, "location": location})

    date_range = f"{dates[0]} – {dates[-1]}" if dates else ""
    return errors, date_range


# ── Message building ───────────────────────────────────────────────────────────

def build_message(frontend_info, backend_info, today_label: str) -> str:
    lines = [f"*Tourno Error Log — {today_label}*\n"]

    for label, info in [("Frontend", frontend_info), ("Backend", backend_info)]:
        lines.append(f"*{label}:*")
        if info is None:
            lines.append("  No error log found.")
        elif not info.get("content", "").strip():
            lines.append("  Error log is empty.")
        else:
            errors, date_range = parse_log(info["content"])
            if not errors:
                lines.append("  Error log is empty.")
            else:
                fatals = sum(e["count"] for e in errors if "Fatal" in e["severity"])
                warnings = sum(e["count"] for e in errors if "Warning" in e["severity"])
                lines.append(f"  {len(errors)} unique errors — {fatals} fatals, {warnings} warnings")
                for e in errors[:3]:
                    lines.append(f"  • [{e['count']}x] {e['severity'].replace('PHP ', '')} — {e['message'][:80]}")
                if len(errors) > 3:
                    lines.append(f"  …and {len(errors) - 3} more")
        lines.append("")

    return "\n".join(lines)


# ── Notifications ──────────────────────────────────────────────────────────────

def send_slack(message: str):
    if not SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN not set — skipping Slack")
        return
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"},
        json={"channel": SLACK_USER_ID, "text": message, "mrkdwn": True},
        timeout=10,
    )
    data = resp.json()
    if data.get("ok"):
        logger.info("Slack message sent.")
    else:
        logger.error(f"Slack error: {data.get('error')}")


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram")
        return
    resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=10,
    )
    if resp.ok:
        logger.info("Telegram message sent.")
    else:
        logger.error(f"Telegram error: {resp.text}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    from googleapiclient.discovery import build

    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Europe/Helsinki"))
    timestamp = now.strftime("%Y%m%d%H%M")
    today_label = now.strftime("%Y-%m-%d")

    logger.info("Tourno error log run starting...")

    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)

    fe_meta = find_error_log(drive, FRONTEND_FOLDER_ID)
    be_meta = find_error_log(drive, BACKEND_FOLDER_ID)

    frontend_info = None
    backend_info = None

    if fe_meta:
        logger.info(f"Frontend error_log found ({fe_meta.get('size', 0)} bytes)")
        frontend_info = {"id": fe_meta["id"], "content": read_file_content(drive, fe_meta["id"])}

    if be_meta:
        logger.info(f"Backend error_log found ({be_meta.get('size', 0)} bytes)")
        backend_info = {"id": be_meta["id"], "content": read_file_content(drive, be_meta["id"])}

    message = build_message(frontend_info, backend_info, today_label)
    send_slack(message)
    send_telegram(message)

    if frontend_info:
        rename_file(drive, frontend_info["id"], timestamp)
    if backend_info:
        rename_file(drive, backend_info["id"], timestamp)

    logger.info("Done.")


if __name__ == "__main__":
    main()
