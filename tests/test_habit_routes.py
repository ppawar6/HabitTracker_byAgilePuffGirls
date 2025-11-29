import json
from datetime import datetime
from extensions import db
from models import Habit


def test_toggle_completion_recovers_from_corrupt_completed_dates(logged_in_client, app):
    """If completed_dates is invalid JSON, toggle should reset it and still mark today."""
    with app.app_context():
        habit = Habit(
            name="Corrupt Completed Dates",
            description="test",
            completed_dates="this-is-not-json",
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    # Act – this will hit the try/except in routes/habits.toggle_completion
    response = logged_in_client.post(f"/habit-tracker/toggle/{hid}", follow_redirects=False)

    assert response.status_code == 302
    assert response.location == "/habit-tracker"

    # Assert – completed_dates should now be a list with 'today'
    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert isinstance(dates, list)
        assert today in dates


def test_toggle_completion_recovers_from_non_list_json(logged_in_client, app):
    """If completed_dates is valid JSON but not a list, toggle should reset it."""
    with app.app_context():
        habit = Habit(
            name="Non-List JSON",
            completed_dates=json.dumps({"key": "value"}),
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    response = logged_in_client.post(f"/habit-tracker/toggle/{hid}", follow_redirects=False)

    assert response.status_code == 302
    assert response.location == "/habit-tracker"

    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert isinstance(dates, list)
        assert today in dates


def test_toggle_completion_handles_none_completed_dates(logged_in_client, app):
    """Test toggle when completed_dates is None."""
    with app.app_context():
        habit = Habit(
            name="None Dates",
            completed_dates=None
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    resp = logged_in_client.post(f"/habit-tracker/toggle/{hid}")
    assert resp.status_code == 302
    
    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert today in dates


def test_toggle_completion_unauthenticated(client, app):
    """Test that unauthenticated users are redirected to signin."""
    with app.app_context():
        habit = Habit(name="Test Habit")
        db.session.add(habit)
        db.session.commit()
        hid = habit.id
    
    resp = client.post(f"/habit-tracker/toggle/{hid}")
    assert resp.status_code == 302
    assert "/signin" in resp.location


def test_toggle_completion_habit_not_found(logged_in_client):
    """Test that non-existent habit returns 404."""
    resp = logged_in_client.post("/habit-tracker/toggle/99999")
    assert resp.status_code == 404