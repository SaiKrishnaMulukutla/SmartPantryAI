"""OTP generation, sending, and verification."""
from __future__ import annotations

import random
import string

from auth.email.sender import send_email
from db.otp_tokens import store_otp, verify_otp as _db_verify


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def send_otp(email: str, purpose: str) -> str:
    """Generate OTP, persist it, send email. Returns the OTP (for testing)."""
    otp = generate_otp()
    store_otp(email, otp)

    if purpose == "register":
        send_email(email, template="otp_verify", context={"otp": otp, "email": email})
    elif purpose == "reset_password":
        send_email(email, template="password_reset", context={"otp": otp, "email": email})

    return otp


def verify(email: str, otp: str) -> bool:
    return _db_verify(email, otp.strip())
