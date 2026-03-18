"""Google Workspace tools - Gmail, Calendar, Drive, Photos."""

import base64
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

TOOL_DEFINITIONS = [
    {
        "name": "gmail_list_emails",
        "description": "List recent emails from Gmail inbox",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Number of emails to return (default 10)",
                    "default": 10,
                },
                "unread_only": {
                    "type": "boolean",
                    "description": "Only return unread emails",
                    "default": False,
                },
                "query": {
                    "type": "string",
                    "description": "Optional Gmail search query (e.g. 'from:boss@company.com')",
                },
            },
            "required": [],
        },
    },
    {
        "name": "gmail_read_email",
        "description": "Read the full content of a specific email by ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "email_id": {
                    "type": "string",
                    "description": "The email message ID from gmail_list_emails",
                }
            },
            "required": ["email_id"],
        },
    },
    {
        "name": "gmail_send_email",
        "description": "Send an email via Gmail",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body (plain text)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "calendar_list_events",
        "description": "List Google Calendar events. Supports past, present and future events, date ranges, and filtering by name/title.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "How many days ahead to look (default 7). Ignored if time_min is set.",
                    "default": 7,
                },
                "days_back": {
                    "type": "integer",
                    "description": "How many days in the past to look (default 0). Set to fetch past events.",
                    "default": 0,
                },
                "time_min": {
                    "type": "string",
                    "description": "Start of date range in ISO 8601 format (e.g. 2025-01-01T00:00:00). Overrides days_back.",
                },
                "time_max": {
                    "type": "string",
                    "description": "End of date range in ISO 8601 format. Overrides days_ahead.",
                },
                "search": {
                    "type": "string",
                    "description": "Filter events by title/name (case-insensitive substring match).",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max number of events to return (default 50)",
                    "default": 50,
                },
            },
            "required": [],
        },
    },
    {
        "name": "calendar_create_event",
        "description": "Create a new event in Google Calendar",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Event title"},
                "start_datetime": {
                    "type": "string",
                    "description": "Start time in ISO 8601 format (e.g. 2026-03-20T10:00:00)",
                },
                "end_datetime": {
                    "type": "string",
                    "description": "End time in ISO 8601 format",
                },
                "description": {
                    "type": "string",
                    "description": "Optional event description",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of attendee email addresses",
                },
            },
            "required": ["title", "start_datetime", "end_datetime"],
        },
    },
    {
        "name": "calendar_update_event",
        "description": "Update an existing Google Calendar event. Get the event ID from calendar_list_events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID from calendar_list_events"},
                "title": {"type": "string", "description": "New event title"},
                "start_datetime": {"type": "string", "description": "New start time in ISO 8601 format"},
                "end_datetime": {"type": "string", "description": "New end time in ISO 8601 format"},
                "description": {"type": "string", "description": "New event description"},
                "location": {"type": "string", "description": "New event location"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_delete_event",
        "description": "Delete a Google Calendar event. Get the event ID from calendar_list_events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event ID to delete"},
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "calendar_get_event",
        "description": "Get full details of a single Google Calendar event by ID, including full description, attendees, conferencing info, and all metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "The event ID from calendar_list_events",
                }
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "drive_search_files",
        "description": "Search for files in Google Drive by name or content",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (filename keywords or content)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default 10)",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "drive_read_file",
        "description": "Read the content of a Google Drive file (Docs, Sheets, plain text)",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The file ID from drive_search_files",
                }
            },
            "required": ["file_id"],
        },
    },
    {
        "name": "photos_list_albums",
        "description": "List albums in Google Photos",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Max albums to list (default 20)",
                    "default": 20,
                }
            },
            "required": [],
        },
    },
    {
        "name": "photos_search",
        "description": "Search for photos in Google Photos",
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default 10)",
                    "default": 10,
                },
                "date_from": {
                    "type": "string",
                    "description": "Optional start date filter (YYYY-MM-DD)",
                },
                "date_to": {
                    "type": "string",
                    "description": "Optional end date filter (YYYY-MM-DD)",
                },
            },
            "required": [],
        },
    },
]

TOKEN_PATH = Path.home() / ".config" / "groot" / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]

_AUTH_ERROR = (
    "Not authenticated with Google. Run: "
    ".marvin/integrations/google-workspace/bot_auth.sh"
)


def _get_credentials():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None, (
            "Google libraries not installed. "
            "Run: pip install google-auth google-auth-oauthlib google-api-python-client"
        )

    if not TOKEN_PATH.exists():
        return None, _AUTH_ERROR

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                TOKEN_PATH.write_text(creds.to_json())
            except Exception as e:
                return None, f"Token refresh failed: {e}. Re-run bot_auth.sh."
        else:
            return None, _AUTH_ERROR

    return creds, None


def execute(tool_name: str, tool_input: dict, context: dict) -> str:
    creds, err = _get_credentials()
    if err:
        return err

    if tool_name == "gmail_list_emails":
        return _gmail_list(creds, tool_input)
    elif tool_name == "gmail_read_email":
        return _gmail_read(creds, tool_input["email_id"])
    elif tool_name == "gmail_send_email":
        return _gmail_send(creds, tool_input)
    elif tool_name == "calendar_list_events":
        return _calendar_list(creds, tool_input)
    elif tool_name == "calendar_create_event":
        return _calendar_create(creds, tool_input)
    elif tool_name == "calendar_update_event":
        return _calendar_update(creds, tool_input)
    elif tool_name == "calendar_delete_event":
        return _calendar_delete(creds, tool_input["event_id"])
    elif tool_name == "calendar_get_event":
        return _calendar_get_event(creds, tool_input["event_id"])
    elif tool_name == "drive_search_files":
        return _drive_search(creds, tool_input)
    elif tool_name == "drive_read_file":
        return _drive_read(creds, tool_input["file_id"])
    elif tool_name == "photos_list_albums":
        return _photos_list_albums(creds, tool_input)
    elif tool_name == "photos_search":
        return _photos_search(creds, tool_input)
    return f"Unknown tool: {tool_name}"


# ── Gmail ─────────────────────────────────────────────────────────────────────

def _gmail_list(creds, tool_input) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds)

        q_parts = []
        if tool_input.get("unread_only"):
            q_parts.append("is:unread")
        if tool_input.get("query"):
            q_parts.append(tool_input["query"])

        result = service.users().messages().list(
            userId="me",
            maxResults=tool_input.get("max_results", 10),
            q=" ".join(q_parts) if q_parts else None,
        ).execute()

        messages = result.get("messages", [])
        if not messages:
            return "No emails found."

        items = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            headers = {
                h["name"]: h["value"]
                for h in detail.get("payload", {}).get("headers", [])
            }
            snippet = detail.get("snippet", "")[:120]
            items.append(
                f"ID: {msg['id']}\n"
                f"From: {headers.get('From', 'Unknown')}\n"
                f"Subject: {headers.get('Subject', '(no subject)')}\n"
                f"Date: {headers.get('Date', '')}\n"
                f"Preview: {snippet}"
            )

        return f"Found {len(messages)} email(s):\n\n" + "\n\n---\n\n".join(items)
    except Exception as e:
        return f"Gmail error: {e}"


def _gmail_read(creds, email_id: str) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds)
        msg = service.users().messages().get(
            userId="me", id=email_id, format="full"
        ).execute()

        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        def extract_body(part):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            for p in part.get("parts", []):
                result = extract_body(p)
                if result:
                    return result
            return ""

        body = extract_body(msg.get("payload", {}))
        if not body:
            raw_data = msg.get("payload", {}).get("body", {}).get("data")
            if raw_data:
                body = base64.urlsafe_b64decode(raw_data).decode("utf-8", errors="replace")

        return (
            f"From: {headers.get('From', 'Unknown')}\n"
            f"To: {headers.get('To', '')}\n"
            f"Subject: {headers.get('Subject', '(no subject)')}\n"
            f"Date: {headers.get('Date', '')}\n\n"
            f"{body[:6000]}"
        )
    except Exception as e:
        return f"Error reading email: {e}"


def _gmail_send(creds, tool_input: dict) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds)
        message = MIMEText(tool_input["body"])
        message["to"] = tool_input["to"]
        message["subject"] = tool_input["subject"]
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email sent to {tool_input['to']} — subject: '{tool_input['subject']}'"
    except Exception as e:
        return f"Error sending email: {e}"


# ── Calendar ──────────────────────────────────────────────────────────────────

def _calendar_list(creds, tool_input: dict) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow()

        if tool_input.get("time_min"):
            time_min = tool_input["time_min"]
            if not time_min.endswith("Z"):
                time_min += "Z"
        else:
            days_back = tool_input.get("days_back", 0)
            time_min = (now - timedelta(days=days_back)).isoformat() + "Z"

        if tool_input.get("time_max"):
            time_max = tool_input["time_max"]
            if not time_max.endswith("Z"):
                time_max += "Z"
        else:
            time_max = (now + timedelta(days=tool_input.get("days_ahead", 7))).isoformat() + "Z"

        result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=tool_input.get("max_results", 50),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = result.get("items", [])

        # Filter by name if requested
        search = tool_input.get("search", "").lower()
        if search:
            events = [e for e in events if search in e.get("summary", "").lower()]

        if not events:
            return "No events found."

        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            end = e["end"].get("dateTime", e["end"].get("date", ""))
            line = f"• {e.get('summary', '(no title)')}\n  Start: {start}\n  End: {end}"
            if e.get("location"):
                line += f"\n  Location: {e['location']}"
            attendees = [a["email"] for a in e.get("attendees", [])]
            if attendees:
                line += f"\n  Attendees: {', '.join(attendees)}"
            if e.get("description"):
                line += f"\n  Description: {e['description'][:300]}"
            line += f"\n  ID: {e['id']}"
            lines.append(line)

        return f"{len(events)} event(s) found:\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"Calendar error: {e}"


def _calendar_create(creds, tool_input: dict) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        event = {
            "summary": tool_input["title"],
            "start": {"dateTime": tool_input["start_datetime"], "timeZone": "Europe/Helsinki"},
            "end": {"dateTime": tool_input["end_datetime"], "timeZone": "Europe/Helsinki"},
        }
        if tool_input.get("description"):
            event["description"] = tool_input["description"]
        if tool_input.get("attendees"):
            event["attendees"] = [{"email": e} for e in tool_input["attendees"]]

        created = service.events().insert(calendarId="primary", body=event).execute()
        return (
            f"Event created: '{tool_input['title']}'\n"
            f"Start: {tool_input['start_datetime']}\n"
            f"ID: {created['id']}"
        )
    except Exception as e:
        return f"Error creating event: {e}"


def _calendar_update(creds, tool_input: dict) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        event_id = tool_input["event_id"]
        existing = service.events().get(calendarId="primary", eventId=event_id).execute()

        if tool_input.get("title"):
            existing["summary"] = tool_input["title"]
        if tool_input.get("start_datetime"):
            existing["start"] = {"dateTime": tool_input["start_datetime"], "timeZone": "Europe/Helsinki"}
        if tool_input.get("end_datetime"):
            existing["end"] = {"dateTime": tool_input["end_datetime"], "timeZone": "Europe/Helsinki"}
        if tool_input.get("description"):
            existing["description"] = tool_input["description"]
        if tool_input.get("location"):
            existing["location"] = tool_input["location"]

        updated = service.events().update(calendarId="primary", eventId=event_id, body=existing).execute()
        return f"Event updated: '{updated.get('summary')}'\nID: {updated['id']}"
    except Exception as e:
        return f"Error updating event: {e}"


def _calendar_delete(creds, event_id: str) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return f"Event {event_id} deleted."
    except Exception as e:
        return f"Error deleting event: {e}"


def _calendar_get_event(creds, event_id: str) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("calendar", "v3", credentials=creds)
        e = service.events().get(calendarId="primary", eventId=event_id).execute()

        start = e["start"].get("dateTime", e["start"].get("date", ""))
        end = e["end"].get("dateTime", e["end"].get("date", ""))

        lines = [
            f"Title: {e.get('summary', '(no title)')}",
            f"Start: {start}",
            f"End: {end}",
            f"Status: {e.get('status', '')}",
        ]
        if e.get("location"):
            lines.append(f"Location: {e['location']}")
        if e.get("description"):
            lines.append(f"Description:\n{e['description']}")
        attendees = e.get("attendees", [])
        if attendees:
            att_lines = [f"  - {a.get('displayName', a['email'])} <{a['email']}> ({a.get('responseStatus', '?')})" for a in attendees]
            lines.append("Attendees:\n" + "\n".join(att_lines))
        conf = e.get("conferenceData", {})
        if conf:
            entry_points = conf.get("entryPoints", [])
            for ep in entry_points:
                if ep.get("entryPointType") == "video":
                    lines.append(f"Video call: {ep.get('uri', '')}")
        lines.append(f"ID: {e['id']}")
        lines.append(f"Created: {e.get('created', '')}")
        lines.append(f"Updated: {e.get('updated', '')}")
        lines.append(f"Organizer: {e.get('organizer', {}).get('email', '')}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching event: {e}"


# ── Drive ─────────────────────────────────────────────────────────────────────

def _drive_search(creds, tool_input: dict) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("drive", "v3", credentials=creds)
        q = tool_input["query"]
        result = service.files().list(
            q=f"(name contains '{q}' or fullText contains '{q}') and trashed=false",
            pageSize=tool_input.get("max_results", 10),
            fields="files(id, name, mimeType, modifiedTime)",
        ).execute()

        files = result.get("files", [])
        if not files:
            return f"No files found matching '{q}'"

        lines = [
            f"• {f['name']}\n  Type: {f['mimeType']}\n  Modified: {f.get('modifiedTime', '')}\n  ID: {f['id']}"
            for f in files
        ]
        return f"Found {len(files)} file(s):\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"Drive error: {e}"


def _drive_read(creds, file_id: str) -> str:
    try:
        from googleapiclient.discovery import build

        service = build("drive", "v3", credentials=creds)
        meta = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime = meta.get("mimeType", "")
        name = meta.get("name", "unknown")

        export_map = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
            "application/vnd.google-apps.presentation": "text/plain",
        }

        if mime in export_map:
            content = service.files().export(fileId=file_id, mimeType=export_map[mime]).execute()
        else:
            content = service.files().get_media(fileId=file_id).execute()

        text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else str(content)
        if len(text) > 8000:
            text = text[:8000] + f"\n\n[Truncated — {len(text)} total chars]"

        return f"File: {name}\n\n{text}"
    except Exception as e:
        return f"Error reading file: {e}"


# ── Photos ────────────────────────────────────────────────────────────────────

def _photos_list_albums(creds, tool_input: dict) -> str:
    try:
        import requests

        resp = requests.get(
            "https://photoslibrary.googleapis.com/v1/albums",
            headers={"Authorization": f"Bearer {creds.token}"},
            params={"pageSize": tool_input.get("max_results", 20)},
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            return f"Photos error: {data['error']['message']}"

        albums = data.get("albums", [])
        if not albums:
            return "No albums found."

        lines = [
            f"• {a.get('title', '(untitled)')}\n"
            f"  Items: {a.get('mediaItemsCount', '?')}\n"
            f"  ID: {a['id']}"
            for a in albums
        ]
        return f"Albums ({len(albums)}):\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"Photos error: {e}"


def _photos_search(creds, tool_input: dict) -> str:
    try:
        import requests

        body: dict = {"pageSize": tool_input.get("max_results", 10)}

        if tool_input.get("date_from") or tool_input.get("date_to"):
            date_filter: dict = {}
            if tool_input.get("date_from"):
                d = tool_input["date_from"].split("-")
                date_filter["startDate"] = {"year": int(d[0]), "month": int(d[1]), "day": int(d[2])}
            if tool_input.get("date_to"):
                d = tool_input["date_to"].split("-")
                date_filter["endDate"] = {"year": int(d[0]), "month": int(d[1]), "day": int(d[2])}
            body["filters"] = {"dateFilter": {"ranges": [date_filter]}}

        resp = requests.post(
            "https://photoslibrary.googleapis.com/v1/mediaItems:search",
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            return f"Photos error: {data['error']['message']}"

        items = data.get("mediaItems", [])
        if not items:
            return "No photos found."

        lines = [
            f"• {item.get('filename', 'unknown')}\n"
            f"  Created: {item.get('mediaMetadata', {}).get('creationTime', '?')}\n"
            f"  View: {item.get('productUrl', '')}\n"
            f"  ID: {item['id']}"
            for item in items
        ]
        return f"Photos ({len(items)}):\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"Photos search error: {e}"
