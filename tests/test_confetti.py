"""Tests for Habit completion + confetti celebration feature."""

import pytest
from flask import url_for

from app import app
from extensions import db
from models import Habit


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
    """Create an authenticated test client."""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


@pytest.fixture
def habit_url():
    """Resolve the habit tracker URL."""
    with app.test_request_context():
        return url_for("habit_tracker")


@pytest.fixture
def sample_habit_data():
    """
    Insert a simple active habit in the test DB and return scalar data
    (id and name) so we don't depend on a live SQLAlchemy session.
    """
    with app.app_context():
        habit = Habit(
            name="Read 10 pages",
            description="Daily reading habit",
            category="Study",
            priority="Medium",
        )
        db.session.add(habit)
        db.session.commit()
        return {"id": habit.id, "name": habit.name}


def test_confetti_script_and_helpers_present(authenticated_client, habit_url, sample_habit_data):
    """
    Habit tracker page should include the confetti library and
    JS helpers for the celebration flow.
    """
    response = authenticated_client.get(habit_url)
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Confetti CDN script tag
    assert "canvas-confetti" in data

    # Helper functions for the feature
    assert "function launchConfetti()" in data
    assert "function showCompletionCelebration(habitId)" in data
    assert "function closeAndComplete(habitId)" in data


def test_habit_card_has_completion_form_and_button(
    authenticated_client, habit_url, sample_habit_data
):
    """
    Each active habit card should expose a Complete button wired to the
    showCompletionCelebration JS function and have a form with a stable id.
    """
    habit_id = sample_habit_data["id"]

    response = authenticated_client.get(habit_url)
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # Form id used later by closeAndComplete(habitId)
    form_id = f"completeForm{habit_id}"
    assert form_id in html

    # Button uses JS celebration handler instead of plain submit
    expected_onclick = f'onclick="showCompletionCelebration({habit_id})"'
    assert expected_onclick in html

    # Human-readable label (we don't care about exact whitespace)
    assert "Complete" in html



def test_complete_endpoint_marks_habit_completed(authenticated_client, sample_habit_data):
    """
    Backend /habit-tracker/complete/<id> should still mark the habit as completed
    and redirect back to the habit tracker (JS overlay submits this form).
    """
    habit_id = sample_habit_data["id"]
    url = f"/habit-tracker/complete/{habit_id}"

    response = authenticated_client.post(url, follow_redirects=False)
    assert response.status_code == 302
    assert "/habit-tracker" in response.headers.get("Location", "")

    # Verify DB state
    with app.app_context():
        refreshed = db.session.get(Habit, habit_id)
        assert refreshed.is_completed is True
        assert refreshed.completed_at is not None


def test_completed_habit_shows_in_completed_section(
    authenticated_client, habit_url, sample_habit_data
):
    """
    Once completed, the habit should appear in the 'Completed Habits' section
    with the success styling.
    """
    habit_id = sample_habit_data["id"]
    habit_name = sample_habit_data["name"]

    # First mark as completed via backend route (as JS would after closing overlay)
    authenticated_client.post(f"/habit-tracker/complete/{habit_id}")

    # Reload page
    response = authenticated_client.get(habit_url)
    assert response.status_code == 200
    html = response.data.decode("utf-8")

    # Section header + habit name present in completed block
    assert "Completed Habits" in html
    assert habit_name in html
    assert "100% Complete" in html or "100% Progress" in html
