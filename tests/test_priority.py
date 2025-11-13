"""Tests for habit priority levels functionality"""

from datetime import datetime, timedelta, timezone

import pytest

from app import app
from extensions import db
from models import Habit


@pytest.fixture
def client():
    """Create a test client"""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client"""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


def test_create_habit_with_default_priority(authenticated_client):
    """Test that habits are created with default Medium priority"""
    response = authenticated_client.post(
        "/habit-tracker",
        data={"name": "Test Habit", "description": "Test description"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Check that habit was created with Medium priority
    with app.app_context():
        habit = Habit.query.filter_by(name="Test Habit").first()
        assert habit is not None
        assert habit.priority == "Medium"


def test_create_habit_with_high_priority(authenticated_client):
    """Test creating a habit with High priority"""
    response = authenticated_client.post(
        "/habit-tracker",
        data={"name": "Important Habit", "priority": "High"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        habit = Habit.query.filter_by(name="Important Habit").first()
        assert habit is not None
        assert habit.priority == "High"


def test_create_habit_with_low_priority(authenticated_client):
    """Test creating a habit with Low priority"""
    response = authenticated_client.post(
        "/habit-tracker",
        data={"name": "Low Priority Habit", "priority": "Low"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        habit = Habit.query.filter_by(name="Low Priority Habit").first()
        assert habit is not None
        assert habit.priority == "Low"


def test_priority_badges_displayed(authenticated_client):
    """Test that priority badges are displayed in the UI"""
    # Create habits with different priorities
    with app.app_context():
        high_habit = Habit(name="High Priority Task", priority="High")
        medium_habit = Habit(name="Medium Priority Task", priority="Medium")
        low_habit = Habit(name="Low Priority Task", priority="Low")

        db.session.add_all([high_habit, medium_habit, low_habit])
        db.session.commit()

    response = authenticated_client.get("/habit-tracker")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that priority badges are shown
    assert "High Priority" in data
    assert "Medium Priority" in data
    assert "Low Priority" in data


def test_priority_sorting_order(authenticated_client):
    """Test that habits are sorted by priority correctly (High > Medium > Low)"""
    now = datetime.now(timezone.utc)

    with app.app_context():
        # Create habits with different priorities and creation times
        low_habit = Habit(
            name="Low Priority Task", priority="Low", created_at=now - timedelta(hours=3)
        )
        high_habit = Habit(
            name="High Priority Task", priority="High", created_at=now - timedelta(hours=2)
        )
        medium_habit = Habit(
            name="Medium Priority Task", priority="Medium", created_at=now - timedelta(hours=1)
        )

        db.session.add_all([low_habit, high_habit, medium_habit])
        db.session.commit()

    response = authenticated_client.get("/habit-tracker?sort=priority")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Find positions of each habit name in the response
    high_pos = data.find("High Priority Task")
    medium_pos = data.find("Medium Priority Task")
    low_pos = data.find("Low Priority Task")

    # High priority should appear first, then Medium, then Low
    assert high_pos < medium_pos < low_pos


def test_priority_sort_option_in_dropdown(authenticated_client):
    """Test that Priority sort option appears in the dropdown"""
    response = authenticated_client.get("/habit-tracker")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that the priority sort option exists
    assert "priority" in data  # Check for priority value in dropdown
    assert "Sort: Priority" in data or "Priority" in data  # Check for priority text


def test_all_sort_options_still_work(authenticated_client):
    """Test that all original sort options (A-Z, Z-A, Newest, Oldest) still work"""
    with app.app_context():
        habit_a = Habit(
            name="Alpha Habit", created_at=datetime.now(timezone.utc) - timedelta(days=2)
        )
        habit_z = Habit(
            name="Zulu Habit", created_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        db.session.add_all([habit_a, habit_z])
        db.session.commit()

    # Test A-Z sorting
    response = authenticated_client.get("/habit-tracker?sort=az")
    assert response.status_code == 200
    data = response.data.decode("utf-8")
    alpha_pos = data.find("Alpha Habit")
    zulu_pos = data.find("Zulu Habit")
    assert alpha_pos < zulu_pos

    # Test Z-A sorting
    response = authenticated_client.get("/habit-tracker?sort=za")
    assert response.status_code == 200
    data = response.data.decode("utf-8")
    alpha_pos = data.find("Alpha Habit")
    zulu_pos = data.find("Zulu Habit")
    assert zulu_pos < alpha_pos

    # Test Newest First sorting
    response = authenticated_client.get("/habit-tracker?sort=newest")
    assert response.status_code == 200

    # Test Oldest First sorting
    response = authenticated_client.get("/habit-tracker?sort=oldest")
    assert response.status_code == 200


def test_priority_with_same_level_sorts_by_creation_date(authenticated_client):
    """Test that habits with same priority are sorted by creation date"""
    now = datetime.now(timezone.utc)

    with app.app_context():
        # Create two high priority habits at different times
        older_habit = Habit(
            name="Older High Priority", priority="High", created_at=now - timedelta(hours=2)
        )
        newer_habit = Habit(
            name="Newer High Priority", priority="High", created_at=now - timedelta(hours=1)
        )

        db.session.add_all([newer_habit, older_habit])
        db.session.commit()

    response = authenticated_client.get("/habit-tracker?sort=priority")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Older habit should appear before newer habit when priorities are the same
    older_pos = data.find("Older High Priority")
    newer_pos = data.find("Newer High Priority")
    assert older_pos < newer_pos


def test_priority_default_value_in_model(authenticated_client):
    """Test that the Habit model has correct default priority"""
    with app.app_context():
        habit = Habit(name="Test Habit")
        db.session.add(habit)
        db.session.commit()

        # Fetch the habit and check default priority
        saved_habit = Habit.query.filter_by(name="Test Habit").first()
        assert saved_habit.priority == "Medium"


def test_priority_dropdown_in_create_form(authenticated_client):
    """Test that priority dropdown exists in the create habit form"""
    response = authenticated_client.get("/habit-tracker")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that priority dropdown exists with all three options
    assert 'name="priority"' in data
    assert 'value="High"' in data
    assert 'value="Medium"' in data
    assert 'value="Low"' in data


def test_priority_colors_in_badges(authenticated_client):
    """Test that different priority levels have different color badges"""
    with app.app_context():
        high_habit = Habit(name="High Task", priority="High")
        medium_habit = Habit(name="Medium Task", priority="Medium")
        low_habit = Habit(name="Low Task", priority="Low")

        db.session.add_all([high_habit, medium_habit, low_habit])
        db.session.commit()

    response = authenticated_client.get("/habit-tracker")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # Check that different color classes are used for different priorities
    assert "text-red-700" in data  # High priority should use red
    assert "text-blue-700" in data  # Medium priority should use blue
    assert "text-gray-700" in data  # Low priority should use gray


def test_priority_sorting_is_default(authenticated_client):
    """Test that priority sorting is the default when no sort parameter is specified"""
    with app.app_context():
        low_habit = Habit(name="Low Priority Task", priority="Low")
        high_habit = Habit(name="High Priority Task", priority="High")

        db.session.add_all([low_habit, high_habit])
        db.session.commit()

    # Access without sort parameter
    response = authenticated_client.get("/habit-tracker")
    assert response.status_code == 200
    data = response.data.decode("utf-8")

    # High priority should appear before low priority by default
    high_pos = data.find("High Priority Task")
    low_pos = data.find("Low Priority Task")
    assert high_pos < low_pos
