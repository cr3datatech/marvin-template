#!/usr/bin/env python3
"""
Tourno Error Log Analyser

Runs every Tuesday and Thursday at 9am Helsinki time.
- Checks Google Drive for error_log files in tourno_error_logs/frontend and backend
- Reads, parses and deduplicates errors
- Sends HTML summary email to support@tourno.fi
- Renames processed files to error_log_YYYYMMDDHHmm

Cron: 3 9 * * 2,4 TZ=Europe/Helsinki
"""

import base64
import json
import logging
import re
from collections import Counter
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
GROOT_ROOT = SCRIPT_DIR.parent.parent.parent

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

GOOGLE_TOKEN_PATH = Path.home() / ".config" / "groot" / "google_token.json"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.send",
]

GOOGLE_EMAIL = "cr3data.tech@gmail.com"
RECIPIENT_EMAIL = "support@tourno.fi"

FRONTEND_FOLDER_ID = "1UEaoIvi98G__7L03rpeRF6cN-r2Phsdo"
BACKEND_FOLDER_ID = "141Q31L5FaZLwWqR0SOId-U085ASi8iVQ"


# ── Google auth ────────────────────────────────────────────────────────────────

def get_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), GOOGLE_SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed token
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
    """Return file metadata if error_log exists in folder, else None."""
    result = drive_service.files().list(
        q=f"name = 'error_log' and '{folder_id}' in parents and trashed = false",
        fields="files(id, name, size)",
        pageSize=1,
    ).execute()
    files = result.get("files", [])
    return files[0] if files else None


def read_file_content(drive_service, file_id: str) -> str:
    """Download and return file content as string."""
    content = drive_service.files().get_media(fileId=file_id).execute()
    return content.decode("utf-8", errors="replace")


def rename_file(drive_service, file_id: str, timestamp: str):
    """Rename file to error_log_YYYYMMDDHHmm."""
    new_name = f"error_log_{timestamp}"
    drive_service.files().update(fileId=file_id, body={"name": new_name}).execute()
    logger.info(f"Renamed file {file_id} → {new_name}")


# ── Log parsing ────────────────────────────────────────────────────────────────

def parse_log(content: str) -> list[dict]:
    """
    Parse PHP error log lines. Returns list of unique errors with counts.
    Each entry: {count, severity, message, location}
    """
    # Match log lines: [date] PHP <severity>: <message> in <file> on line <n>
    line_pattern = re.compile(
        r"\[\d{2}-\w{3}-\d{4} [\d:]+[^\]]*\] (PHP \w[\w ]+?):\s+(.+?)(?:\s+in\s+(/[^\s]+)\s+on\s+line\s+(\d+))?$"
    )

    raw_errors: Counter = Counter()
    dates = []

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        # Capture date range
        date_match = re.match(r"\[(\d{2}-\w{3}-\d{4})", line)
        if date_match:
            dates.append(date_match.group(1))

        m = line_pattern.match(line)
        if not m:
            continue

        severity = m.group(1).strip()       # e.g. "PHP Warning", "PHP Fatal error"
        message = m.group(2).strip()
        file_path = m.group(3) or ""
        line_no = m.group(4) or ""

        # Normalize: strip full server path prefix
        file_short = re.sub(r"^/home/[^/]+/public_html/", "", file_path)

        # Deduplicate key: severity + message + file + line
        key = (severity, message, file_short, line_no)
        raw_errors[key] += 1

    errors = []
    for (severity, message, file_short, line_no), count in raw_errors.most_common():
        location = f"{file_short}:{line_no}" if file_short else ""
        errors.append({
            "count": count,
            "severity": severity,
            "message": message,
            "location": location,
        })

    date_range = ""
    if dates:
        date_range = f"{dates[0]} – {dates[-1]}"

    return errors, date_range


# ── Email building ─────────────────────────────────────────────────────────────

SEVERITY_COLOUR = {
    "PHP Fatal error": "#c0392b",
    "PHP Warning": "#e67e22",
    "PHP Notice": "#2980b9",
}

def severity_label(sev: str) -> str:
    colour = SEVERITY_COLOUR.get(sev, "#555")
    short = sev.replace("PHP ", "")
    return f'<span style="color:{colour};font-weight:bold">{short}</span>'


def build_section(label: str, file_info: dict | None) -> str:
    """Build HTML for one log section (frontend or backend)."""
    html = f"<h3>{label}</h3>\n"

    if file_info is None:
        return html + "<p>No new error log found in this folder.</p>\n"

    content = file_info.get("content", "")
    if not content or not content.strip():
        return html + "<p>Error log is empty — no errors recorded.</p>\n"

    errors, date_range = parse_log(content)
    if not errors:
        return html + "<p>Error log is empty — no errors recorded.</p>\n"

    if date_range:
        html += f'<p style="color:#888;font-size:0.9em">{date_range}</p>\n'

    html += (
        '<table border="1" cellpadding="6" cellspacing="0" '
        'style="border-collapse:collapse;width:100%">\n'
        '<tr style="background:#f5f5f5">'
        "<th>#</th><th>Severity</th><th>Error</th><th>Location</th>"
        "</tr>\n"
    )
    for e in errors:
        html += (
            f"<tr>"
            f"<td>{e['count']}x</td>"
            f"<td>{severity_label(e['severity'])}</td>"
            f"<td><code>{e['message'][:120]}</code></td>"
            f"<td>{e['location']}</td>"
            f"</tr>\n"
        )
    html += "</table>\n"
    return html


def build_top_priority(frontend_info, backend_info) -> str:
    """Build top priority section from all errors combined."""
    all_errors = []
    for info in [frontend_info, backend_info]:
        if info and info.get("content", "").strip():
            errors, _ = parse_log(info["content"])
            all_errors.extend(errors)

    if not all_errors:
        return ""

    # Sort by count, filter to fatals first, then by count
    fatals = sorted(
        [e for e in all_errors if "Fatal" in e["severity"]],
        key=lambda x: x["count"], reverse=True
    )[:3]

    if not fatals:
        top = sorted(all_errors, key=lambda x: x["count"], reverse=True)[:3]
    else:
        top = fatals

    html = "<h3>Top Priority</h3><ol>\n"
    for e in top:
        html += f"<li><strong>{e['count']}x {e['severity']}</strong> — <code>{e['message'][:100]}</code>"
        if e["location"]:
            html += f" <em>({e['location']})</em>"
        html += "</li>\n"
    html += "</ol>\n"
    return html


def build_email(frontend_info, backend_info, today: str) -> str:
    fe_section = build_section("Frontend Errors", frontend_info)
    be_section = build_section("Backend Errors", backend_info)
    priority = build_top_priority(frontend_info, backend_info)

    return f"""<p>Hi Craig,</p>
<p>Here's the error log summary for Tourno.</p>
<hr>
{fe_section}
<hr>
{be_section}
{"<hr>" + priority if priority else ""}
<hr>
<p><em>Sent by Groot</em></p>"""


# ── Gmail send ─────────────────────────────────────────────────────────────────

def send_email(gmail_service, subject: str, html_body: str):
    msg = MIMEMultipart("alternative")
    msg["To"] = RECIPIENT_EMAIL
    msg["From"] = f"Groot <{GOOGLE_EMAIL}>"
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
    logger.info(f"Email sent to {RECIPIENT_EMAIL}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    from googleapiclient.discovery import build

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M")
    today_label = now.strftime("%Y-%m-%d")

    logger.info("Tourno error log run starting...")

    creds = get_credentials()
    drive = build("drive", "v3", credentials=creds)
    gmail = build("gmail", "v1", credentials=creds)

    # Check for files
    fe_meta = find_error_log(drive, FRONTEND_FOLDER_ID)
    be_meta = find_error_log(drive, BACKEND_FOLDER_ID)

    # Read content where files exist
    frontend_info = None
    backend_info = None

    if fe_meta:
        logger.info(f"Frontend error_log found: {fe_meta['id']} ({fe_meta.get('size', 0)} bytes)")
        content = read_file_content(drive, fe_meta["id"])
        frontend_info = {"id": fe_meta["id"], "content": content}

    if be_meta:
        logger.info(f"Backend error_log found: {be_meta['id']} ({be_meta.get('size', 0)} bytes)")
        content = read_file_content(drive, be_meta["id"])
        backend_info = {"id": be_meta["id"], "content": content}

    # Build and send email
    subject = f"Tourno Error Log Summary — {today_label}"
    body = build_email(frontend_info, backend_info, today_label)
    send_email(gmail, subject, body)

    # Rename processed files
    if frontend_info:
        rename_file(drive, frontend_info["id"], timestamp)
    if backend_info:
        rename_file(drive, backend_info["id"], timestamp)

    logger.info("Done.")


if __name__ == "__main__":
    main()
