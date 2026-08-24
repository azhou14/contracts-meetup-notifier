"""
Entrypoint. Run daily; sends reminder emails for any lunch/coffee event
happening tomorrow (Pacific time).

Designed to be triggered hourly by GitHub Actions (cron is UTC-only and
DST-unaware) and self-gate on "is it ~5PM Pacific right now" - see
--force to bypass that gate for manual/dry runs.

Env vars required (see README / .env.example):
    GOOGLE_SHEET_ID
    GOOGLE_SERVICE_ACCOUNT_JSON
    SMTP_USER
    SMTP_PASSWORD
    PROFESSOR_EMAIL
    DEBUG_EMAIL

Flags:
    --dry-run   parse + build messages but never call smtplib; prints instead
    --force     skip the "is it currently 5PM Pacific" time gate
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo

from mailer import build_message, send_message
from sheet_parser import events_on, parse_workbook
from sheets_client import download_sheet_as_xlsx

PACIFIC = ZoneInfo("America/Los_Angeles")
TARGET_HOUR_PACIFIC = 17  # 5 PM
DOWNLOAD_PATH = "/tmp/sheet_download.xlsx"


def is_send_window(now_pacific: datetime) -> bool:
    """True if we're within the same hour as 5 PM Pacific (since this is
    triggered hourly, not at a precise minute)."""
    return now_pacific.hour == TARGET_HOUR_PACIFIC


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    now_pacific = datetime.now(PACIFIC)

    if not args.force and not is_send_window(now_pacific):
        print(f"Not the 5PM Pacific window (now: {now_pacific.strftime('%H:%M %Z')}); skipping.")
        return 0

    tomorrow = (now_pacific + timedelta(days=1)).date()
    print(f"Checking for events on {tomorrow} ...")

    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    download_sheet_as_xlsx(sheet_id, DOWNLOAD_PATH)

    all_events = parse_workbook(DOWNLOAD_PATH, today=now_pacific.date())
    matches = events_on(all_events, tomorrow)

    if not matches:
        print("No lunch/coffee events tomorrow. Nothing to send.")
        return 0

    from_addr = os.environ["SMTP_USER"]
    professor_addr = os.environ["PROFESSOR_EMAIL"]
    debug_addr = os.environ["DEBUG_EMAIL"]

    for event in matches:
        msg = build_message(event, from_addr, professor_addr, debug_addr)
        print(f"--- {event.kind} on {event.event_date} @ {event.location_display} ---")
        print(f"To: {msg['To']}")
        print(f"Cc: {msg['Cc']}")
        print(f"Subject: {msg['Subject']}")

        if args.dry_run:
            print(msg.get_payload()[0].get_payload())
            print("(dry run - not sent)\n")
            continue

        smtp_user = os.environ["SMTP_USER"]
        smtp_password = os.environ["SMTP_PASSWORD"]
        send_message(msg, smtp_user, smtp_password)
        print("Sent.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
