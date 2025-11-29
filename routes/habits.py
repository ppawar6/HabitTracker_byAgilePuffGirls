import json
from datetime import datetime

from flask import Blueprint, redirect, session, url_for

from extensions import db
from models import Habit

habits_bp = Blueprint("habits", __name__, url_prefix="/habit-tracker")


@habits_bp.route("/toggle-completion/<int:habit_id>", methods=["POST"])
@habits_bp.route("/toggle_completion/<int:habit_id>", methods=["POST"])
def toggle_completion(habit_id):
    """
    Toggle today's completion for a habit.

    Behaviour expected by tests (tests/test_habit_routes.py + tests/test_routes.py):

    - If NOT authenticated → 302 redirect to /signin
    - If habit not found    → 404
    - If success            → 302 redirect back to /habit-tracker
    - Side-effect: toggle today's date inside Habit.completed_dates
      (JSON list of ISO date strings)
    """
    # 1) Auth required – tests expect redirect, not JSON
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    # 2) Look up habit
    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    # 3) Toggle today's completion in completed_dates
    today = datetime.utcnow().date().isoformat()

    try:
        # completed_dates is stored as a JSON list, e.g. '["2025-02-01", "2025-02-02"]'
        dates = json.loads(habit.completed_dates or "[]")
    except (TypeError, json.JSONDecodeError):
        dates = []

    if today in dates:
        # already completed → remove it
        dates = [d for d in dates if d != today]
    else:
        # not completed → mark as done
        dates.append(today)

    habit.completed_dates = json.dumps(dates)
    db.session.commit()

    # 4) Redirect back to main habit tracker (tests expect 302 to /habit-tracker)
    return redirect(url_for("habit_tracker"))
