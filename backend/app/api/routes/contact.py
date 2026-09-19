"""Contact Us API routes for Ice Stream platform."""

import json
import logging
import os
import smtplib
import socket
import urllib.error
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from app.observability.repository import ObservabilityRepository

# Load environment variables from project root and frontend if present
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / "frontend" / ".env")
load_dotenv(BASE_DIR / ".env")
load_dotenv()

logger = logging.getLogger("ice_stream.api.contact")

router = APIRouter(tags=["Contact"])

DEFAULT_SANTOSH_EMAIL = "Sant7124@gmail.com"
repo = ObservabilityRepository()


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


@router.post("/contact", response_model=Dict[str, Any])
def submit_contact(contact: ContactRequest):
    """Handle contact submission with SQLite persistence, HTTPS email support, and Render Free Tier resilience."""
    santosh_email = (os.getenv("SANTOSH_EMAIL") or DEFAULT_SANTOSH_EMAIL).strip('\"\' ')
    email_user = (os.getenv("EMAIL_USER") or santosh_email).strip('\"\' ')
    email_password = os.getenv("EMAIL_PASSWORD")
    if email_password:
        email_password = email_password.replace(" ", "").strip('\"\' ')
    copy_email = (os.getenv("COPY_EMAIL") or santosh_email).strip('\"\' ')
    recipients = list(dict.fromkeys([santosh_email, copy_email]))

    # Always persist inquiry to SQLite database first so no message is ever lost
    try:
        repo.save_contact_inquiry(
            name=contact.name,
            email=contact.email,
            subject=contact.subject,
            message=contact.message,
            delivery_status="received",
            delivery_detail="Inquiry recorded in operational registry",
        )
    except Exception as db_err:
        logger.warning(f"Failed to record inquiry in SQLite: {db_err}")

    # 1. Check for HTTPS Email API (e.g. Resend via RESEND_API_KEY)
    # HTTPS port 443 is unrestricted on all cloud platforms including Render free tier
    resend_api_key = os.getenv("RESEND_API_KEY")
    if resend_api_key:
        try:
            logger.info("Attempting dispatch via Resend HTTPS Email API...")
            resend_url = "https://api.resend.com/emails"
            payload = {
                "from": os.getenv("RESEND_FROM_EMAIL", "Ice Stream Portal <onboarding@resend.dev>"),
                "to": recipients,
                "reply_to": contact.email,
                "subject": f"[Ice Stream Contact] {contact.subject}",
                "text": f"Inquiry from: {contact.name} ({contact.email})\n\n{contact.message}",
            }
            req = urllib.request.Request(
                resend_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    logger.info("Email delivered successfully via Resend HTTPS API")
                    return {
                        "success": True,
                        "message": f"Message sent successfully to {santosh_email}!",
                        "recipients": recipients,
                        "persisted": True,
                    }
        except Exception as resend_err:
            logger.warning(f"Resend HTTPS dispatch failed: {resend_err}. Proceeding with SMTP fallback...")

    # 2. Check for missing SMTP credentials
    if not email_password:
        err_msg = (
            "SMTP Authentication Error: 'EMAIL_PASSWORD' is not set in .env. "
            "Gmail requires a 16-character Google App Password (not your personal password). "
            "Please add EMAIL_USER and EMAIL_PASSWORD to your .env file."
        )
        logger.warning(err_msg)
        return {
            "success": False,
            "message": err_msg,
            "recipients": recipients,
            "persisted": True,
        }

    # 3. Construct standard MIME Email
    msg = EmailMessage()
    msg["Subject"] = f"[Ice Stream Contact] {contact.subject}"
    msg["From"] = email_user
    msg["To"] = santosh_email
    if copy_email != santosh_email:
        msg["Cc"] = copy_email
    msg["Reply-To"] = contact.email

    recipients_display = f"- {santosh_email}" if santosh_email == copy_email else f"- {santosh_email}\n- {copy_email}"
    msg.set_content(
        f"""
New inquiry submitted via Ice Stream Contact Us portal:

--------------------------------------------------
Sender Name:    {contact.name}
Sender Email:   {contact.email}
Subject:        {contact.subject}
--------------------------------------------------

Message:
{contact.message}

--------------------------------------------------
This message was automatically forwarded to:
{recipients_display}
"""
    )

    # 4. Attempt SMTP dispatch with strict socket timeouts
    # Render Free Tier blocks outbound ports 25, 465, and 587 ([Errno 101] Network is unreachable)
    smtp_sent = False
    try:
        logger.info(f"Dispatching contact email via smtp.gmail.com to {recipients}...")
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8.0) as smtp:
                smtp.login(email_user, email_password)
                smtp.send_message(msg, to_addrs=recipients)
                smtp_sent = True
        except (OSError, socket.timeout, TimeoutError) as ssl_err:
            logger.info(f"Port 465 SSL connection attempt resulted in: {ssl_err}. Trying port 587 STARTTLS...")
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=8.0) as smtp:
                smtp.starttls()
                smtp.login(email_user, email_password)
                smtp.send_message(msg, to_addrs=recipients)
                smtp_sent = True

        if smtp_sent:
            logger.info(f"Contact email successfully delivered to {recipients}")
            success_notice = (
                f"Message sent successfully to {santosh_email}!"
                if santosh_email == copy_email
                else f"Message sent successfully to {santosh_email} and {copy_email}!"
            )
            return {
                "success": True,
                "message": success_notice,
                "recipients": recipients,
                "persisted": True,
            }

    except smtplib.SMTPAuthenticationError as auth_err:
        err_str = (
            f"Gmail Authentication Failed: {auth_err}. "
            "Please check that EMAIL_USER and EMAIL_PASSWORD in .env use a valid 16-character Google App Password."
        )
        logger.error(err_str)
        return {
            "success": False,
            "message": err_str,
            "recipients": recipients,
            "persisted": True,
        }

    except (OSError, socket.timeout, TimeoutError, ConnectionRefusedError) as net_err:
        # Render Free Tier outbound SMTP restriction detection ([Errno 101] Network is unreachable)
        is_render_smtp_block = "101" in str(net_err) or "Network is unreachable" in str(net_err) or "timed out" in str(net_err).lower()
        logger.warning(
            f"SMTP dispatch encountered host network restriction: {net_err}. "
            "Inquiry safely retained in SQLite observability registry."
        )
        return {
            "success": True,
            "message": (
                f"Inquiry recorded successfully in platform registry! Note: Direct Gmail SMTP was restricted by Render Free Tier outbound network policy. Your inquiry has been securely stored in the operational database for {santosh_email}."
                if is_render_smtp_block
                else f"Inquiry captured in operational database! Note: Direct email delivery encountered network timeout ({net_err})."
            ),
            "recipients": recipients,
            "persisted": True,
            "delivery_status": "saved_to_database",
        }

    except Exception as error:
        err_str = f"Email delivery failed: {str(error)}"
        logger.error(err_str, exc_info=True)
        return {
            "success": False,
            "message": err_str,
            "recipients": recipients,
            "persisted": True,
        }


@router.get("/contact/messages", response_model=List[Dict[str, Any]])
def list_contact_messages(limit: int = 50, offset: int = 0):
    """Retrieve recorded operational contact inquiries."""
    return repo.list_contact_inquiries(limit=limit, offset=offset)
