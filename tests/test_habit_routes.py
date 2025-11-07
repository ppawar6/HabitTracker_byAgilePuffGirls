"""Test habit toggle completion functionality."""

import json
from datetime import datetime

from extensions import db
from models import Habit


def test_toggle_completion_marks_habit_completed(logged_in_client, app):
    """Test that POST /habit-tracker/toggle/<id> marks a habit as completed for today."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Morning Exercise", description="Daily workout")
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/toggle/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/habit-tracker"

    with app.app_context():
        updated_habit = Habit.query.get(habit_id)
        completed_dates = json.loads(updated_habit.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert today in completed_dates


def test_toggle_completion_removes_completed_date(logged_in_client, app):
    """Test that toggling an already completed habit removes it from completed_dates."""
    # Arrange: Create a habit that's already completed for today
    today = datetime.utcnow().date().isoformat()
    with app.app_context():
        habit = Habit(
            name="Evening Reading",
            description="Read for 30 minutes",
            completed_dates=json.dumps([today])
        )
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act: Toggle completion again
    response = logged_in_client.post(f"/habit-tracker/toggle/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        updated_habit = Habit.query.get(habit_id)
        completed_dates = json.loads(updated_habit.completed_dates)
        assert today not in completed_dates


def test_toggle_completion_requires_auth(client, app):
    """Test that toggling completion without authentication redirects to signin."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Test Habit")
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = client.post(f"/habit-tracker/toggle/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/signin"


def test_toggle_completion_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/toggle/<invalid_id> returns 404."""
    # Act
    response = logged_in_client.post("/habit-tracker/toggle/99999", follow_redirects=False)

    # Assert
    assert response.status_code == 404
