"""Automated tests for the Contact Us API endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.api.main import app

client = TestClient(app)


def test_contact_endpoint_validation_success():
    """Verify contact endpoint accepts valid contact submissions and formats recipients."""
    payload = {
        "name": "Alex Mercer",
        "email": "alex.mercer@enterprise.io",
        "subject": "Platform Inquiry",
        "message": "Inquiring about real-time Iceberg table commit latencies."
    }

    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance

    with patch("smtplib.SMTP_SSL", mock_smtp_class), patch.dict("os.environ", {"EMAIL_PASSWORD": "mock_app_password_16char"}):
        response = client.post("/api/contact", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Sant7124@gmail.com" in data["recipients"]
        assert mock_smtp_instance.login.called
        assert mock_smtp_instance.send_message.called


def test_contact_endpoint_render_network_unreachable_fallback():
    """Verify endpoint gracefully handles Render Free Tier outbound SMTP block ([Errno 101])."""
    payload = {
        "name": "Santosh Yadav",
        "email": "sant7124@gmail.com",
        "subject": "Render Cloud Test",
        "message": "Testing network unreachable fallback."
    }

    mock_smtp_class = MagicMock(side_effect=OSError(101, "Network is unreachable"))

    with patch("smtplib.SMTP_SSL", mock_smtp_class), patch("smtplib.SMTP", mock_smtp_class), patch.dict("os.environ", {"EMAIL_PASSWORD": "mock_app_password_16char"}):
        response = client.post("/api/contact", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["persisted"] is True
        assert "registry" in data["message"].lower() or "database" in data["message"].lower()


def test_contact_endpoint_list_messages():
    """Verify stored messages can be retrieved via /api/contact/messages."""
    response = client.get("/api/contact/messages?limit=10")
    assert response.status_code == 200
    messages = response.json()
    assert isinstance(messages, list)


def test_contact_endpoint_invalid_email_format():
    """Verify endpoint rejects malformed email addresses."""
    payload = {
        "name": "Invalid User",
        "email": "not-an-email",
        "subject": "Test",
        "message": "This should fail validation."
    }
    response = client.post("/api/contact", json=payload)
    assert response.status_code == 422  # Unprocessable Entity from Pydantic


def test_contact_endpoint_missing_credentials_handling():
    """Verify endpoint provides informative feedback when credentials are absent."""
    payload = {
        "name": "Test User",
        "email": "test@example.com",
        "subject": "Diagnostic Check",
        "message": "Testing fallback behavior."
    }
    with patch.dict("os.environ", {"EMAIL_PASSWORD": ""}):
        response = client.post("/api/contact", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "EMAIL_PASSWORD" in data["message"]
        assert "Sant7124@gmail.com" in data["recipients"]
