import json
from datetime import datetime
from extensions import db
from models import Habit

# All alternative toggle routes that must behave the same
ROUTES = [
    "/toggle-completion/{id}",
    "/toggle_completion/{id}",
    "/habit-tracker/toggle-completion/{id}",
    "/habit-tracker/toggle_completion/{id}",
]

def test_all_toggle_aliases_redirect_and_mark_completed(logged_in_client, app):
    """Verify all compatibility toggle routes behave identically."""
    with app.app_context():
        habit = Habit(name="Alias Test Habit")
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    for route in ROUTES:
        response = logged_in_client.post(route.format(id=hid))
        assert response.status_code == 302
        assert response.location == "/habit-tracker"

        with app.app_context():
            updated = Habit.query.get(hid)
            today = datetime.utcnow().date().isoformat()
            completions = json.loads(updated.completed_dates)
            assert today in completions

def test_all_toggle_aliases_404_when_invalid(logged_in_client):
    """Verify all alias routes return 404 for invalid habit IDs."""
    for route in ROUTES:
        response = logged_in_client.post(route.format(id=999999))
        assert response.status_code == 404

def test_all_toggle_aliases_require_auth(client, app):
    """Verify all alias routes redirect to signin when not authenticated."""
    with app.app_context():
        habit = Habit(name="NoAuth Habit")
        db.session.add(habit)
        db.session.commit()
        hid = habit.id

    for route in ROUTES:
        response = client.post(route.format(id=hid))
        assert response.status_code == 302
        assert response.location == "/signin"
