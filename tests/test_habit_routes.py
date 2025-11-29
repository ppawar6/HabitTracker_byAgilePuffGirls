import json
from datetime import datetime

from extensions import db
from models import Habit


def test_toggle_completion_handles_malformed_completed_dates(logged_in_client, app):
    """If completed_dates is bad JSON, toggle should recover and store today's date."""
    today = datetime.utcnow().date().isoformat()

    with app.app_context():
        # completed_dates is invalid JSON on purpose
        habit = Habit(
            name="Bad JSON Habit",
            description="test",
            completed_dates="not-a-json-list",
        )
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act: hit the canonical toggle route
    resp = logged_in_client.post(
        f"/habit-tracker/toggle/{habit_id}",
        follow_redirects=False,
    )

    # Assert redirect + fixed data
    assert resp.status_code == 302
    assert resp.location == "/habit-tracker"

    with app.app_context():
        updated = Habit.query.get(habit_id)
        dates = json.loads(updated.completed_dates)
        assert dates == [today]
