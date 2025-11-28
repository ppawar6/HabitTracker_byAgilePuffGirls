import json
from datetime import datetime

from flask import Blueprint, jsonify, redirect, request, session, url_for

from extensions import db
from models import Habit

habits_bp = Blueprint("habits", __name__, url_prefix="/habit-tracker")


@habits_bp.route("/toggle/<int:habit_id>", methods=["POST"])
def toggle_completion(habit_id):
    """
    Toggle a habit's completion for today's date.
    Uses the completed_dates JSON list on the Habit model.
    """
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = Habit.query.get_or_404(habit_id)

    today = datetime.utcnow().date().isoformat()

    # completed_dates is stored as JSON text
    try:
        completed_dates = json.loads(habit.completed_dates or "[]")
    except json.JSONDecodeError:
        completed_dates = []

    if today in completed_dates:
        completed_dates.remove(today)
    else:
        completed_dates.append(today)

    habit.completed_dates = json.dumps(completed_dates)
    db.session.commit()

    # This matches what you had before and what tests expect
    return redirect(url_for("habit_tracker"))


@habits_bp.route("/reorder", methods=["POST"])
def reorder_habits():
    """
    Update manual sort order for habits based on drag-and-drop in the UI.

    Expects JSON payload:
      { "order": [<habit_id_1>, <habit_id_2>, ...] }

    The first ID gets position=1, second gets position=2, etc.
    """
    if not session.get("authenticated"):
        return jsonify({"success": False, "error": "Authentication required"}), 401

    data = request.get_json(silent=True) or {}
    order = data.get("order")

    # Basic payload validation
    if not isinstance(order, list) or not order:
        return jsonify({"success": False, "error": "Invalid payload"}), 400

    updated_ids = []

    # Assign 1-based positions in the order received
    for position, habit_id in enumerate(order, start=1):
        try:
            hid = int(habit_id)
        except (TypeError, ValueError):
            # Skip bad values instead of blowing up
            continue

        habit = Habit.query.get(hid)
        if not habit:
            continue

        habit.position = position
        updated_ids.append(hid)

    if not updated_ids:
        return jsonify({"success": False, "error": "No valid habit IDs"}), 400

    db.session.commit()
    return jsonify({"success": True, "updated": updated_ids})
