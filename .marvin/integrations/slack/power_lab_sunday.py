#!/usr/bin/env python3
"""
Power Lab Sunday Reminder

Runs every Sunday morning. Sends Craig a Slack DM with:
- Next upcoming calendar event (title, time, description)
- Full Power Lab Idea Bank (numbered list to pick from)

Cron: 0 10 * * 0 (Sunday 10am Helsinki time)
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
GROOT_ROOT = SCRIPT_DIR.parent.parent.parent

load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(GROOT_ROOT / ".env")

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_USER_ID = "U083MA2K6US"

JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
CONFLUENCE_PAGE_ID = "1245118465"
IDEA_BANK_URL = f"{JIRA_BASE_URL}/wiki/spaces/CLOUD/pages/{CONFLUENCE_PAGE_ID}/AI_PowerLab_Idea_Bank_Notion"

GOOGLE_TOKEN_PATH = Path.home() / ".config" / "groot" / "google_token.json"

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
]


def get_next_calendar_event() -> dict | None:
    """Return the next upcoming calendar event with full details."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), GOOGLE_SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                logger.error("Google credentials invalid — re-run bot_auth.sh")
                return None

        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow()
        result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat() + "Z",
            timeMax=(now + timedelta(days=14)).isoformat() + "Z",
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = result.get("items", [])
        if not events:
            return None

        e = events[0]
        return {
            "title": e.get("summary", "(no title)"),
            "start": e["start"].get("dateTime", e["start"].get("date", "")),
            "end": e["end"].get("dateTime", e["end"].get("date", "")),
            "description": e.get("description", ""),
            "location": e.get("location", ""),
        }
    except Exception as ex:
        logger.error(f"Calendar error: {ex}")
        return None


def fetch_idea_bank_content() -> str:
    """Fetch the latest idea bank content from Confluence (markdown body)."""
    try:
        url = f"{JIRA_BASE_URL}/wiki/rest/api/content/{CONFLUENCE_PAGE_ID}"
        resp = requests.get(
            url,
            auth=(JIRA_EMAIL, JIRA_API_TOKEN),
            headers={"Accept": "application/json"},
            params={"expand": "body.view"},
            timeout=15,
        )
        if resp.ok:
            return "fetched"  # We use the static list below for reliable formatting
        logger.warning(f"Confluence fetch warning: {resp.status_code}")
        return "fallback"
    except Exception as ex:
        logger.warning(f"Confluence fetch error: {ex}")
        return "fallback"


def build_event_block(event: dict | None) -> str:
    if not event:
        return "_No upcoming events in the next 14 days._\n"

    lines = [
        "*📅 Next Calendar Event:*",
        f"*{event['title']}*",
        f"🕐 {event['start']}",
    ]
    if event.get("location"):
        lines.append(f"📍 {event['location']}")
    if event.get("description"):
        desc = event["description"].strip()
        lines += ["", "*Description:*", desc]
    return "\n".join(lines)


IDEA_LIST = """\
*A. AI Productivity & Knowledge Work*
`1` AI Meeting Intelligence Pipeline — transcribe meetings, extract actions, push to Jira/Notion
`2` AI Email Triage & Smart Reply System — categorize, summarize, propose replies via LLM
`3` Internal RAG Knowledge Assistant — chatbot over Confluence/Drive/SharePoint
`4` AI Document Summarizer for Execs — turn long reports into short exec digests

*B. Operations, DevOps & SRE*
`5` AI Log Insights & Incident Triage — CloudWatch/Azure Monitor → daily anomaly summary
`6` Release Note Generator from Commits — Git commits → human-readable release notes to Slack/Confluence
`7` Cost Optimization AI Advisor — billing data → anomalies + cost-saving proposals
`8` Incident Response AI Co-Pilot — alarm fires → auto-gather logs/metrics + suggested actions

*C. Backoffice & Business Process*
`9` Invoice Parsing, Validation & Routing — OCR + LLM extraction + audit log
`10` Customer Feedback Analyzer — support tickets/surveys → themes + product recommendations
`11` AI-Based Document Classifier — classify and route documents with metadata tags

*D. Sales, Pre-Sales & Consulting*
`12` AI Proposal & SoW Generator — CRM data → tailored draft proposals
`13` AI Demo Environment Auto-Configurator — inputs → provisioned cloud demo stack + script
`14` Customer-Facing FAQ Chatbot — RAG assistant for an app (e.g. Tourno)

*E. Personal Workflow Automations*
`15` AI Chief of Staff System — calendar + tasks + notes → daily priority brief
`16` Weekly Reflection & Growth Coach — reflection prompts → LLM pattern summary + focus suggestions

*F. Identity, Access Control & Guardrails*
`17` AI Automation IAM Boundary — least-privilege IAM roles/policies for automations
`18` Secure API Gateway for Bots — OIDC auth, rate limiting, IP restrictions on bot endpoints
`19` Human-in-the-Loop Approval Layer — AI suggests, human approves, decision history logged

*G. Transaction Safety, Governance & Audit*
`20` Guardrail Policy Engine — threshold/policy checks before automation executes
`21` Automation Audit Trail System — log every step: inputs, prompts, outputs, actions
`22` Secrets & Token Management Pipeline — automate rotation via Secrets Manager / Key Vault

*H. Networking & Safe Cloud Connectivity*
`23` AI Bot Network Isolation Architecture — isolated subnets, private endpoints, traffic inspection
`24` Cross-Cloud Automation Router — orchestrate AWS Lambda, GCP Cloud Run, Azure Functions via central router
`25` Secure Multi-Cloud Webhook Gateway — mTLS, JWT, rate limiting, input sanitization"""


def build_message(event: dict | None) -> str:
    today = datetime.now().strftime("%A, %-d %B %Y")
    event_block = build_event_block(event)

    return f""":sunrise: *Good morning! Sunday Power Lab Reminder — {today}*

{event_block}

---

:brain: *Power Lab — Pick Your Idea for This Week*
Reply with the number and I'll research it, build a full Confluence doc (architecture, implementation steps, risks, follow-ups) and draft your LinkedIn post.

{IDEA_LIST}

:point_right: *Reply with a number (1–25), or `skip` to come back later.*
Full Idea Bank: {IDEA_BANK_URL}"""


def send_slack_dm(message: str) -> bool:
    resp = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "channel": SLACK_USER_ID,
            "text": message,
            "mrkdwn": True,
        },
        timeout=10,
    )
    data = resp.json()
    if not data.get("ok"):
        logger.error(f"Slack API error: {data.get('error')}")
        return False
    logger.info("Sunday Power Lab reminder sent successfully.")
    return True


def main():
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN not set")
        raise SystemExit(1)

    fetch_idea_bank_content()  # Refresh check (warns if Confluence unreachable)
    event = get_next_calendar_event()
    message = build_message(event)
    success = send_slack_dm(message)
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
