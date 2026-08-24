"""
Composes and sends the reminder email for a single Event.

Sends via Gmail SMTP with an App Password (not your regular password -
generate one at https://myaccount.google.com/apppasswords, requires
2FA enabled on the sending account).
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sheet_parser import Event

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

KIND_LABEL = {"lunch": "Lunch", "coffee": "Coffee"}


def build_message(
    event: Event,
    from_addr: str,
    professor_addr: str,
    debug_addr: str,
) -> MIMEMultipart:
    label = KIND_LABEL.get(event.kind, event.kind.title())
    date_str = event.event_date.strftime("%A, %B %-d")

    to_addrs = [a.email for a in event.attendees]
    cc_addrs = [professor_addr, debug_addr]

    if to_addrs:
        subject = f"Reminder: {label} tomorrow ({date_str}) at {event.location_display}"
        names = ", ".join(a.name for a in event.attendees)
        body = (
            f"Hi all,\n\n"
            f"Friendly reminder that you're signed up for {label.lower()} tomorrow, "
            f"{date_str}, at {event.location_display}.\n\n"
            f"Attendees: {names}\n\n"
        )
        if event.location is None:
            body += (
                "Note: the location was still marked TBD as of this reminder - "
                "please check the sign-up sheet for updates.\n\n"
            )
        body += "See you there!\n"
    else:
        # Nobody signed up - notify professor/debug only, no attendee To: line.
        subject = f"[No sign-ups] {label} tomorrow ({date_str})"
        body = (
            f"Heads up: no one is currently signed up for {label.lower()} tomorrow, "
            f"{date_str}. Location on file: {event.location_display}.\n"
        )

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs) if to_addrs else from_addr
    msg["Cc"] = ", ".join(cc_addrs)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    return msg


def send_message(msg: MIMEMultipart, smtp_user: str, smtp_password: str) -> None:
    all_recipients = [addr.strip() for addr in msg["To"].split(",")]
    if msg["Cc"]:
        all_recipients += [addr.strip() for addr in msg["Cc"].split(",")]

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(msg["From"], all_recipients, msg.as_string())
