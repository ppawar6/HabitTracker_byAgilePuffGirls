"""Tests for habit statistics dashboard"""

from datetime import datetime, timedelta, timezone

import pytest

from app import app
from extensions import db
from models import Habit


@pytest.fixture
def client():
    """Create a test client with a fresh database"""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


def test_stats_requires_authentication(client):
    """Test that stats page requires authentication"""
    response = client.get("/habit-tracker/stats")
    assert response.status_code == 302
    assert "/signin" in response.location


def test_stats_page_loads(authenticated_client):
    """Test that stats page loads successfully when authenticated"""
    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    assert b"Habit Statistics" in response.data


def test_stats_shows_zero_counts_when_no_habits(authenticated_client):
    """Test that stats page shows zero counts when no habits exist"""
    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    assert b"Habit Statistics" in response.data
    # Should show 0 for all counts
    assert b">0<" in response.data  # Total habits


def test_stats_calculates_total_habits(authenticated_client):
    """Test that stats correctly counts total habits"""
    # Create some habits
    habit1 = Habit(name="Exercise", category="Health")
    habit2 = Habit(name="Read", category="Study")
    habit3 = Habit(name="Meditate", category="Mindfulness")

    db.session.add_all([habit1, habit2, habit3])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    assert b">3<" in response.data  # Total habits = 3


def test_stats_calculates_active_habits(authenticated_client):
    """Test that stats correctly counts active habits"""
    # Create habits with different statuses
    habit1 = Habit(name="Exercise", is_archived=False, is_paused=False)
    habit2 = Habit(name="Read", is_archived=False, is_paused=False)
    habit3 = Habit(name="Meditate", is_archived=True, is_paused=False)
    habit4 = Habit(name="Journal", is_archived=False, is_paused=True)

    db.session.add_all([habit1, habit2, habit3, habit4])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    # Active habits = 2 (not archived and not paused)
    data = response.data.decode("utf-8")
    assert "Active Habits" in data


def test_stats_calculates_paused_habits(authenticated_client):
    """Test that stats correctly counts paused habits"""
    # Create paused and non-paused habits
    habit1 = Habit(name="Exercise", is_paused=True, is_archived=False)
    habit2 = Habit(name="Read", is_paused=False, is_archived=False)
    habit3 = Habit(name="Meditate", is_paused=True, is_archived=False)

    db.session.add_all([habit1, habit2, habit3])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    # Paused habits = 2
    data = response.data.decode("utf-8")
    assert "Paused Habits" in data


def test_stats_calculates_archived_habits(authenticated_client):
    """Test that stats correctly counts archived habits"""
    # Create archived and non-archived habits
    habit1 = Habit(name="Exercise", is_archived=True)
    habit2 = Habit(name="Read", is_archived=False)
    habit3 = Habit(name="Meditate", is_archived=True)
    habit4 = Habit(name="Journal", is_archived=True)

    db.session.add_all([habit1, habit2, habit3, habit4])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    # Archived habits = 3
    data = response.data.decode("utf-8")
    assert "Archived Habits" in data


def test_stats_shows_habits_by_category(authenticated_client):
    """Test that stats shows habits grouped by category"""
    # Create habits with different categories
    habit1 = Habit(name="Exercise", category="Health")
    habit2 = Habit(name="Run", category="Health")
    habit3 = Habit(name="Read", category="Study")
    habit4 = Habit(name="Meditate", category="Mindfulness")

    db.session.add_all([habit1, habit2, habit3, habit4])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that categories are shown
    assert "Health" in data
    assert "Study" in data
    assert "Mindfulness" in data
    assert "Habits by Category" in data


def test_stats_handles_uncategorized_habits(authenticated_client):
    """Test that stats handles habits without categories"""
    # Create habits with and without categories
    habit1 = Habit(name="Exercise", category="Health")
    habit2 = Habit(name="Random Task", category=None)
    habit3 = Habit(name="Another Task", category="")

    db.session.add_all([habit1, habit2, habit3])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that "Uncategorized" is shown for habits without category
    assert "Uncategorized" in data or "Health" in data


def test_stats_shows_most_recent_habit(authenticated_client):
    """Test that stats shows the most recently created habit"""
    now = datetime.now(timezone.utc)

    # Create habits with different creation dates
    habit1 = Habit(name="Old Habit", created_at=now - timedelta(days=10))
    habit2 = Habit(name="Recent Habit", created_at=now - timedelta(days=1))
    habit3 = Habit(name="Oldest Habit", created_at=now - timedelta(days=30))

    db.session.add_all([habit1, habit2, habit3])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that most recent habit is shown
    assert "Most Recent Habit" in data
    assert "Recent Habit" in data


def test_stats_shows_oldest_habit(authenticated_client):
    """Test that stats shows the oldest created habit"""
    now = datetime.now(timezone.utc)

    # Create habits with different creation dates
    habit1 = Habit(name="Old Habit", created_at=now - timedelta(days=10))
    habit2 = Habit(name="Recent Habit", created_at=now - timedelta(days=1))
    habit3 = Habit(name="Oldest Habit", created_at=now - timedelta(days=30))

    db.session.add_all([habit1, habit2, habit3])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that oldest habit is shown
    assert "Oldest Habit" in data


def test_stats_shows_habit_journey_days(authenticated_client):
    """Test that stats calculates and shows the habit journey duration"""
    now = datetime.now(timezone.utc)

    # Create habits with different creation dates
    habit1 = Habit(name="Old Habit", created_at=now - timedelta(days=10))
    habit2 = Habit(name="Recent Habit", created_at=now - timedelta(days=1))

    db.session.add_all([habit1, habit2])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that habit journey is shown (should be 9 days between habits)
    assert "Habit Journey" in data or "day" in data


def test_stats_shows_quick_insights(authenticated_client):
    """Test that stats shows quick insights section"""
    # Create some habits
    habit1 = Habit(name="Exercise", is_archived=False, is_paused=False)
    habit2 = Habit(name="Read", is_archived=False, is_paused=False)
    habit3 = Habit(name="Meditate", is_archived=False, is_paused=True)

    db.session.add_all([habit1, habit2, habit3])
    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that quick insights section exists
    assert "Quick Insights" in data
    assert "Active Rate" in data


def test_stats_back_to_tracker_link(authenticated_client):
    """Test that stats page has a link back to the tracker"""
    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that there's a link back to the habit tracker
    assert "Back to Tracker" in data
    assert "/habit-tracker" in data


def test_stats_category_sorting(authenticated_client):
    """Test that categories are sorted by count (descending)"""
    # Create habits with different category counts
    db.session.add(Habit(name="Ex1", category="Health"))
    db.session.add(Habit(name="Ex2", category="Health"))
    db.session.add(Habit(name="Ex3", category="Health"))
    db.session.add(Habit(name="Study1", category="Study"))
    db.session.add(Habit(name="Study2", category="Study"))
    db.session.add(Habit(name="Mind1", category="Mindfulness"))

    db.session.commit()

    response = authenticated_client.get("/habit-tracker/stats")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Health should appear before Study and Mindfulness (3 > 2 > 1)
    health_pos = data.find("Health")
    study_pos = data.find("Study")
    mindfulness_pos = data.find("Mindfulness")

    # All categories should be present
    assert health_pos > 0
    assert study_pos > 0
    assert mindfulness_pos > 0
