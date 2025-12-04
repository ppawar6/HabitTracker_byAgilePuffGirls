"""Tests for Offline Mode banner + network detection"""

import pytest
from flask import url_for

from app import app
from extensions import db


@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client with a fake user session."""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


@pytest.fixture
def tracker_url():
    """Resolve the main Habit Tracker page URL from the Flask endpoint."""
    with app.test_request_context():
        return url_for("habit_tracker")


def test_offline_banner_present_on_authenticated_page(authenticated_client, tracker_url):
    """
    The Offline Mode banner container should be rendered on pages
    that extend base.html (e.g., /habit-tracker) when authenticated.
    """
    response = authenticated_client.get(tracker_url)
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # Main banner container
    assert 'id="offlineBanner"' in data
    # Should contain some offline copy text
    assert "offline" in data.lower()


def test_offline_banner_initially_hidden(authenticated_client, tracker_url):
    """
    Offline banner should start in a hidden state so it only appears
    when JS detects navigator.onLine === false or the offline event.
    """
    response = authenticated_client.get(tracker_url)
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # We expect the banner to have a "hidden" class (Tailwind utility)
    assert 'id="offlineBanner"' in data
    assert "hidden" in data.split('id="offlineBanner"')[1][:200]


def test_offline_banner_present_on_stats_page(authenticated_client):
    """
    Any page that uses base.html (e.g., stats) should also include
    the offline banner container so the behavior is global.
    """
    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200

    data = response.data.decode("utf-8")
    assert 'id="offlineBanner"' in data


def test_offline_js_listens_for_online_offline_events(authenticated_client, tracker_url):
    """
    Base template should register JS listeners for browser online/offline
    events so the banner can react to connectivity changes.
    """
    response = authenticated_client.get(tracker_url)
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # Look for the JS event bindings added in base.html
    assert 'window.addEventListener("offline"' in data or "window.addEventListener('offline'" in data
    assert 'window.addEventListener("online"' in data or "window.addEventListener('online'" in data


def test_offline_banner_has_dismiss_button(authenticated_client, tracker_url):
    """
    Offline banner should provide a way for the user to dismiss/close it.
    This checks that the dismiss control is present in the markup.
    """
    response = authenticated_client.get(tracker_url)
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # Adjust selectors/text here to match your actual HTML
    # e.g., a close button with a specific id or label.
    assert "dismissOfflineBanner" in data or "closeOfflineBanner" in data or "×" in data
