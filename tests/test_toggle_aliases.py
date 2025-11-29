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
            updated = Habit.query.get(hid)
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
            updated = Habit.query.get(hid)
            dates = json.loads(updated.completed_dates)
            today = datetime.utcnow().date().isoformat()
            assert isinstance(dates, list)
            assert today in dates
