import json
from datetime import datetime

from flask import Blueprint, redirect, session, url_for

from extensions import db
from models import Habit

habits_bp = Blueprint("habits", __name__, url_prefix="/habit-tracker")


@habits_bp.route("/toggle/<int:habit_id>", methods=["POST"])
def toggle_completion(habit_id):
    """Toggle habit completion for today"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = Habit.query.get_or_404(habit_id)
    today = datetime.utcnow().date().isoformat()
    completed_dates = json.loads(habit.completed_dates) if habit.completed_dates else []
    # Toggle completion for today
    if today in completed_dates:
        completed_dates.remove(today)
    else:
        completed_dates.append(today)
    habit.completed_dates = json.dumps(completed_dates)
    db.session.commit()
    return redirect(url_for("habit_tracker"))
