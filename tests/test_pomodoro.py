"""Tests for Pomodoro Timer page"""

import pytest
from flask import url_for

from app import app
from extensions import db


@pytest.fixture
def client():
    """Create a test client with a fresh database."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client."""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


@pytest.fixture
def pomodoro_url():
    """Resolve the Pomodoro Timer URL from the Flask endpoint."""
    with app.test_request_context():
        # IMPORTANT: endpoint name must match your view function
        return url_for("pomodoro_timer")


def test_pomodoro_requires_authentication(client, pomodoro_url):
    """Pomodoro page should redirect to signin when not authenticated."""
    response = client.get(pomodoro_url)
    assert response.status_code == 302
    assert "/signin" in response.location


def test_pomodoro_page_loads_with_auth(authenticated_client, pomodoro_url):
    """Pomodoro page should load successfully when authenticated."""
    response = authenticated_client.get(pomodoro_url)
    assert response.status_code == 200
    assert b"Pomodoro Timer" in response.data


def test_pomodoro_has_timer_display_and_label(authenticated_client, pomodoro_url):
    """Pomodoro page should show initial time and mode label."""
    response = authenticated_client.get(pomodoro_url)
    data = response.data

    # Default time 25:00 and focus label from template
    assert b"25:00" in data
    assert b"Focus session" in data

    # Main timer display element
    assert b'id="timerDisplay"' in data
    assert b'id="modeLabel"' in data


def test_pomodoro_has_mode_buttons(authenticated_client, pomodoro_url):
    """Pomodoro page should render all three mode buttons."""
    response = authenticated_client.get(pomodoro_url)
    data = response.data

    assert b'id="mode-focus"' in data
    assert b'id="mode-short"' in data
    assert b'id="mode-long"' in data

    # Optional: label texts (• encoded as UTF-8)
    assert b"Focus \xe2\x80\xa2 25 min" in data  # "Focus • 25 min"
    assert b"Short Break \xe2\x80\xa2 5 min" in data
    assert b"Long Break \xe2\x80\xa2 15 min" in data


def test_pomodoro_has_control_buttons(authenticated_client, pomodoro_url):
    """Pomodoro page should expose Start, Pause, Reset controls."""
    response = authenticated_client.get(pomodoro_url)
    data = response.data

    assert b'id="startBtn"' in data
    assert b'id="pauseBtn"' in data
    assert b'id="resetBtn"' in data

    assert b"Start" in data
    assert b"Pause" in data
    assert b"Reset" in data


def test_pomodoro_has_focus_quote_section(authenticated_client, pomodoro_url):
    """Pomodoro page should show the Focus Quote card."""
    response = authenticated_client.get(pomodoro_url)
    data = response.data

    assert b"Focus Quote" in data
    assert b'id="quoteText"' in data
    # Initial loading text from template
    assert b"Loading a little burst of motivation" in data


def test_pomodoro_back_to_tracker_link(authenticated_client, pomodoro_url):
    """Pomodoro page should provide a Back to Tracker link."""
    response = authenticated_client.get(pomodoro_url)
    data = response.data.decode("utf-8")

    assert "Back to Tracker" in data
    # Just ensure it links back to the tracker path somehow
    assert "/habit-tracker" in data


def test_pomodoro_navbar_button_visible_in_base_template(authenticated_client):
    """
    Ensure the Pomodoro Timer button appears in the navbar
    (for pages using base.html).
    """
    # Use some page that extends base.html – stats is a good example
    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Button label visible
    assert "Pomodoro Timer" in data


def test_pomodoro_info_modal_present(authenticated_client, pomodoro_url):
    """Pomodoro page should render the info modal container."""
    response = authenticated_client.get(pomodoro_url)
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # Modal wrapper and heading
    assert 'id="pomodoroInfoModal"' in data
    assert "Why use the Pomodoro Timer?" in data

    # Check that it's initially hidden via the utility class
    assert "bg-black/40 hidden" in data or "bg-black/40  hidden" in data


def test_pomodoro_info_modal_has_action_buttons(authenticated_client, pomodoro_url):
    """Pomodoro info modal should include both action buttons."""
    response = authenticated_client.get(pomodoro_url)
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # Buttons by id
    assert 'id="pomodoroInfoLater"' in data
    assert 'id="pomodoroInfoGotIt"' in data

    # Button labels
    assert "Ok" in data
    assert "Don’t show this again" in data  # covers "Got it, let’s focus"


def test_pomodoro_info_modal_not_on_stats_page(authenticated_client):
    """Pomodoro info modal should not be injected on unrelated pages like stats."""
    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200

    data = response.data.decode("utf-8")

    # Ensure the modal id is not present on the stats page
    assert "pomodoroInfoModal" not in data
