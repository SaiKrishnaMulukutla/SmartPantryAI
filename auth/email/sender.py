"""SMTP email dispatcher using Gmail App Password."""
from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from string import Template

from dotenv import load_dotenv

load_dotenv()

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465
_FROM = os.environ["SMTP_EMAIL"]
_PASSWORD = os.environ["SMTP_APP_PASSWORD"].replace(" ", "")
_TEMPLATES_DIR = Path(__file__).parent / "templates"

_SUBJECTS = {
    "otp_verify":      "SmartPantryAI — Verify your email",
    "welcome":         "Welcome to SmartPantryAI 🍳",
    "password_reset":  "SmartPantryAI — Reset your password",
}


def _render(template_name: str, context: dict) -> str:
    base = (_TEMPLATES_DIR / "base.html").read_text()
    body = (_TEMPLATES_DIR / f"{template_name}.html").read_text()
    body_rendered = Template(body).safe_substitute(context)
    return Template(base).safe_substitute({"body": body_rendered, **context})


def send_email(to: str, template: str, context: dict) -> None:
    html = _render(template, context)
    subject = _SUBJECTS.get(template, "SmartPantryAI")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"SmartPantryAI <{_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT, context=ctx) as server:
        server.login(_FROM, _PASSWORD)
        server.sendmail(_FROM, to, msg.as_string())
