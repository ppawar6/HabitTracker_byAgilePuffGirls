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
        updated = Habit.query.get(hid)
        dates = json.loads(updated.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert isinstance(dates, list)
        assert today in dates
