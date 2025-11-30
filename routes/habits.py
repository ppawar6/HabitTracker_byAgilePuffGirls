# routes/habits.py
import json
from datetime import datetime

from flask import Blueprint, redirect, session, url_for

from extensions import db
from models import Habit

habits_bp = Blueprint("habits", __name__, url_prefix="/habit-tracker")


@habits_bp.route("/toggle/<int:habit_id>", methods=["POST"])
def toggle_completion(habit_id):
    """
    Canonical toggle:
    POST /habit-tracker/toggle/<id>

    - If NOT authenticated → 302 to /signin
    - If habit not found → 404
    - Otherwise: toggle today's date in completed_dates (JSON list)
      and redirect to /habit-tracker
    """
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    today = datetime.utcnow().date().isoformat()

    try:
        completed_dates = json.loads(habit.completed_dates or "[]")
    except (TypeError, json.JSONDecodeError):
        completed_dates = []

    if not isinstance(completed_dates, list):
        completed_dates = []

    if today in completed_dates:
        completed_dates.remove(today)
    else:
        completed_dates.append(today)

    habit.completed_dates = json.dumps(completed_dates)
    db.session.commit()

    return redirect(url_for("habit_tracker"))
