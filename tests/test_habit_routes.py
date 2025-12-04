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


def test_canonical_toggle_with_empty_string(logged_in_client, app):
    """Test canonical toggle route with empty string completed_dates."""
    with app.app_context():
        habit = Habit(
            name="Empty String Canonical",
            completed_dates=""
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    resp = logged_in_client.post(f"/habit-tracker/toggle/{hid}")
    assert resp.status_code == 302

    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates or "[]")
        today = datetime.utcnow().date().isoformat()
        assert today in dates


def test_canonical_toggle_type_error(logged_in_client, app):
    """Test canonical toggle handles TypeError in JSON parsing."""
    with app.app_context():
        habit = Habit(
            name="Type Error Canonical",
            completed_dates=456  # Integer to trigger TypeError
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
        assert isinstance(dates, list)
        assert today in dates


def test_reorder_habits_handles_invalid_habit_ids(logged_in_client, app):
    """Test that reorder gracefully handles invalid IDs (covers lines 240-241)."""
    with app.app_context():
        h1 = Habit(name="Habit 1", position=1)
        h2 = Habit(name="Habit 2", position=2)
        db.session.add_all([h1, h2])
        db.session.commit()
        id1, id2 = h1.id, h2.id

    # Send order with invalid IDs mixed in - this covers the except (TypeError, ValueError): continue
    invalid_order = [
        id1,
        "not-a-number",  # Triggers ValueError
        None,            # Triggers TypeError
        id2,
        99999,           # Non-existent ID
        {"bad": "data"}  # Triggers TypeError
    ]

    resp = logged_in_client.post(
        "/habit-tracker/reorder",
        json={"order": invalid_order}
    )

    # Should succeed and just skip the invalid IDs
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    # Verify only valid IDs were updated
    with app.app_context():
        h1_updated = db.session.get(Habit, id1)
        h2_updated = db.session.get(Habit, id2)
        assert h1_updated.position == 1
        assert h2_updated.position == 2
