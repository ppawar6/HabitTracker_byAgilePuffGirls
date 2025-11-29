import json
from datetime import datetime

from extensions import db
from models import Habit

ROUTES = [
    "/toggle-completion/{id}",
    "/toggle_completion/{id}",
    "/habit-tracker/toggle-completion/{id}",
    "/habit-tracker/toggle_completion/{id}",
]


def test_toggle_aliases_recover_from_corrupt_completed_dates(logged_in_client, app):
    """_mark_completed_today should handle invalid JSON in completed_dates."""
    with app.app_context():
        habit = Habit(
            name="Alias Corrupt JSON",
            completed_dates="not-valid-json",
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    for route in ROUTES:
        resp = logged_in_client.post(route.format(id=hid), follow_redirects=False)
        assert resp.status_code == 302
        assert resp.location == "/habit-tracker"

        with app.app_context():
            updated = db.session.get(Habit, hid)
            dates = json.loads(updated.completed_dates)
            today = datetime.utcnow().date().isoformat()
            assert isinstance(dates, list)
            assert today in dates


def test_toggle_aliases_recover_from_non_list_completed_dates(logged_in_client, app):
    """_mark_completed_today should reset completed_dates if JSON is not a list."""
    with app.app_context():
        # Valid JSON but not a list → should trigger `if not isinstance(completed_dates, list)`
        habit = Habit(
            name="Alias Non List JSON",
            completed_dates=json.dumps({"foo": "bar"}),
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    for route in ROUTES:
        resp = logged_in_client.post(route.format(id=hid), follow_redirects=False)
        assert resp.status_code == 302
        assert resp.location == "/habit-tracker"

        with app.app_context():
            updated = db.session.get(Habit, hid)
            dates = json.loads(updated.completed_dates)
            today = datetime.utcnow().date().isoformat()
            assert isinstance(dates, list)
            assert today in dates


def test_toggle_aliases_unauthenticated(client, app):
    """Test that unauthenticated users are redirected to signin for all alias routes."""
    with app.app_context():
        habit = Habit(name="Test Habit")
        db.session.add(habit)
        db.session.commit()
        hid = habit.id
    
    # Try all routes without logging in
    for route in ROUTES:
        resp = client.post(route.format(id=hid))
        assert resp.status_code == 302
        assert "/signin" in resp.location


def test_toggle_aliases_habit_not_found(logged_in_client):
    """Test that non-existent habit returns 404 for all alias routes."""
    for route in ROUTES:
        resp = logged_in_client.post(route.format(id=99999))
        assert resp.status_code == 404


def test_toggle_aliases_all_redirect_and_mark_completed(logged_in_client, app):
    """Test that all toggle alias routes properly mark habit as completed."""
    with app.app_context():
        habit = Habit(
            name="Test All Aliases",
            completed_dates="[]"
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    today = datetime.utcnow().date().isoformat()

    for route in ROUTES:
        # Reset completed_dates before each test
        with app.app_context():
            h = db.session.get(Habit, hid)
            h.completed_dates = "[]"
            db.session.commit()

        # Test the route
        resp = logged_in_client.post(route.format(id=hid), follow_redirects=False)
        assert resp.status_code == 302
        assert resp.location == "/habit-tracker"

        # Verify it was marked completed
        with app.app_context():
            updated = db.session.get(Habit, hid)
            dates = json.loads(updated.completed_dates)
            assert today in dates


def test_toggle_aliases_idempotent_already_completed(logged_in_client, app):
    """Test that calling toggle alias on already-completed habit is idempotent (keeps it completed)."""
    today = datetime.utcnow().date().isoformat()
    
    with app.app_context():
        habit = Habit(
            name="Already Completed",
            completed_dates=json.dumps([today])  # Already completed today
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    # Call it again - should remain completed
    for route in ROUTES:
        resp = logged_in_client.post(route.format(id=hid), follow_redirects=False)
        assert resp.status_code == 302
        
        with app.app_context():
            updated = db.session.get(Habit, hid)
            dates = json.loads(updated.completed_dates)
            # Should still be completed, and only appear once
            assert today in dates
            assert dates.count(today) == 1  # Not duplicated


def test_toggle_aliases_marks_new_completion(logged_in_client, app):
    """Test that marking a fresh habit as completed works correctly."""
    with app.app_context():
        habit = Habit(
            name="Fresh Habit",
            completed_dates=None  # Start with None, not empty list
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    today = datetime.utcnow().date().isoformat()
    
    # Mark it completed - test just one route to ensure commit happens
    resp = logged_in_client.post(f"/toggle-completion/{hid}", follow_redirects=False)
    assert resp.status_code == 302
    
    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates)
        assert today in dates
        assert len(dates) == 1


def test_toggle_aliases_empty_string_completed_dates(logged_in_client, app):
    """Test handling of empty string in completed_dates."""
    with app.app_context():
        habit = Habit(
            name="Empty String",
            completed_dates=""  # Empty string, not None or "[]"
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    resp = logged_in_client.post(f"/toggle-completion/{hid}")
    assert resp.status_code == 302
    
    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates or "[]")
        today = datetime.utcnow().date().isoformat()
        assert today in dates


def test_toggle_aliases_type_error_in_json_parse(logged_in_client, app):
    """Test handling of TypeError during JSON parsing."""
    with app.app_context():
        habit = Habit(
            name="Type Error Test",
            completed_dates=123  # Integer instead of string - will cause TypeError
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    resp = logged_in_client.post(f"/toggle-completion/{hid}")
    assert resp.status_code == 302
    
    with app.app_context():
        updated = db.session.get(Habit, hid)
        dates = json.loads(updated.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert isinstance(dates, list)
        assert today in dates


def test_toggle_aliases_database_persistence(logged_in_client, app):
    """Verify that changes actually persist to database across sessions."""
    with app.app_context():
        habit = Habit(
            name="Persistence Test",
            completed_dates="[]"
        )
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    # Mark completed
    resp = logged_in_client.post(f"/toggle-completion/{hid}")
    assert resp.status_code == 302

    # Start a completely fresh database session
    with app.app_context():
        # Force a fresh query from DB, not from session cache
        db.session.expire_all()
        fresh_habit = db.session.query(Habit).filter_by(id=hid).first()
        dates = json.loads(fresh_habit.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert today in dates
        
        # Mark it again to test the idempotent path commits too
        current_count = len(dates)
        
    # Call again (should be idempotent - no new date added)
    resp2 = logged_in_client.post(f"/toggle-completion/{hid}")
    assert resp2.status_code == 302
    
    with app.app_context():
        db.session.expire_all()
        final_habit = db.session.query(Habit).filter_by(id=hid).first()
        final_dates = json.loads(final_habit.completed_dates)
        # Should still have the same count (idempotent)
        assert len(final_dates) == current_count
        assert today in final_dates