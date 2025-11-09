import json
import os
import random
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from extensions import db
from models import Habit, UserPreferences

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Add custom Jinja filters
@app.template_filter('from_json')
def from_json_filter(value):
    if value is None:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []

from routes.habits import habits_bp  # noqa: E402
from routes.notifications import create_notification, notifications_bp  # noqa: E402
from routes.theme import theme_bp  # noqa: E402

app.register_blueprint(theme_bp)
app.register_blueprint(habits_bp)
app.register_blueprint(notifications_bp)

# Store OTPs temporarily
otp_store = {}

CATEGORIES = [
    "Health",
    "Fitness",
    "Study",
    "Productivity",
    "Mindfulness",
    "Finance",
    "Social",
    "Chores",
]


@app.route("/")
def home():
    """Landing page"""
    return render_template("home/index.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    """Sign in with OTP"""
    if request.method == "POST":
        data = request.get_json()

        if "email" in data and "action" not in data:
            # Generate OTP
            email = data["email"]
            otp = str(random.randint(100000, 999999))
            otp_store[email] = otp

            print(f"\n{'=' * 50}")
            print(f"OTP for {email}: {otp}")
            print(f"{'=' * 50}\n")

            return jsonify({"success": True, "message": f"OTP sent to {email}", "otp": otp})

        elif "action" in data and data["action"] == "verify":
            # Verify OTP
            email = data["email"]
            otp = data["otp"]

            if email in otp_store and otp_store[email] == otp:
                session["authenticated"] = True
                session["email"] = email
                del otp_store[email]
                return jsonify({"success": True, "message": "Authentication successful"})
            else:
                return jsonify({"success": False, "message": "Invalid OTP"})

    return render_template("home/signIn.html")


@app.route("/habit-tracker", methods=["GET", "POST"])
def habit_tracker():
    """Habit tracker - protected"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get('category', '').strip()

        if category == 'other':
            category = request.form.get('category_custom', '').strip()

        if name:
            habit = Habit(
                name=name,
                description=description or None,
                category=(category or None),
            )
            db.session.add(habit)

            # Create notification BEFORE commit
            email = session.get("email")
            if email:
                create_notification(
                    user_email=email,
                    message=f"Added habit: {name}",
                    action_type="added",
                    habit_name=name
                )

            db.session.commit()

        return redirect(url_for("habit_tracker"))

    # Get active habits (not archived and not paused)
    habits = (
        Habit.query.filter_by(is_archived=False, is_paused=False)
        .order_by(Habit.created_at.desc())
        .all()
    )
    # Get paused habits (not archived but paused)
    paused_habits = (
        Habit.query.filter_by(is_archived=False, is_paused=True)
        .order_by(Habit.paused_at.desc())
        .all()
    )

    return render_template(
        "apps/habit_tracker/index.html",
        page_id="habit-tracker",
        habits=habits,
        paused_habits=paused_habits,
        categories=CATEGORIES,
    )


@app.route("/habit-tracker/delete/<int:habit_id>", methods=["POST"])
def delete_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    habit_name = habit.name
    db.session.delete(habit)

    # Create notification BEFORE commit
    email = session.get("email")
    if email:
        create_notification(
            user_email=email,
            message=f"Deleted habit: {habit_name}",
            action_type="deleted",
            habit_name=habit_name
        )

    db.session.commit()
    return redirect(url_for("habit_tracker"))


@app.route("/habit-tracker/update/<int:habit_id>", methods=["POST"])
def update_habit(habit_id):
    """Update habit name"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    old_name = habit.name
    new_name = request.form.get("name", "").strip()
    if new_name:
        habit.name = new_name

        # Create notification BEFORE commit
        email = session.get("email")
        if email:
            create_notification(
                user_email=email,
                message=f"Edited habit: '{old_name}' to '{new_name}'",
                action_type="edited",
                habit_name=new_name
            )

        db.session.commit()

    return redirect(url_for("habit_tracker"))


@app.route("/habit-tracker/archive/<int:habit_id>", methods=["POST"])
def archive_habit(habit_id):
    """Archive a habit"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    habit.is_archived = True
    habit.archived_at = datetime.now(timezone.utc)

    # Create notification BEFORE commit
    email = session.get("email")
    if email:
        create_notification(
            user_email=email,
            message=f"Archived habit: {habit.name}",
            action_type="archived",
            habit_name=habit.name
        )

    db.session.commit()
    return redirect(url_for("habit_tracker"))


@app.route("/habit-tracker/unarchive/<int:habit_id>", methods=["POST"])
def unarchive_habit(habit_id):
    """Unarchive a habit"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    habit.is_archived = False
    habit.archived_at = None

    # Create notification BEFORE commit
    email = session.get("email")
    if email:
        create_notification(
            user_email=email,
            message=f"Unarchived habit: {habit.name}",
            action_type="unarchived",
            habit_name=habit.name
        )

    db.session.commit()
    return redirect(request.referrer or url_for("habit_tracker"))


@app.route("/habit-tracker/pause/<int:habit_id>", methods=["POST"])
def pause_habit(habit_id):
    """Pause a habit"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    habit.is_paused = True
    habit.paused_at = datetime.now(timezone.utc)

    # Create notification BEFORE commit
    email = session.get("email")
    if email:
        create_notification(
            user_email=email,
            message=f"Paused habit: {habit.name}",
            action_type="paused",
            habit_name=habit.name
        )

    db.session.commit()
    return redirect(url_for("habit_tracker"))


@app.route("/habit-tracker/resume/<int:habit_id>", methods=["POST"])
def resume_habit(habit_id):
    """Resume a paused habit"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habit = db.session.get(Habit, habit_id)
    if not habit:
        return "Habit not found", 404

    habit.is_paused = False
    habit.paused_at = None

    # Create notification BEFORE commit
    email = session.get("email")
    if email:
        create_notification(
            user_email=email,
            message=f"Resumed habit: {habit.name}",
            action_type="resumed",
            habit_name=habit.name
        )

    db.session.commit()
    return redirect(request.referrer or url_for("habit_tracker"))


@app.route("/habit-tracker/archived")
def archived_habits():
    """View archived habits"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    habits = Habit.query.filter_by(is_archived=True).order_by(Habit.archived_at.desc()).all()
    return render_template(
        "apps/habit_tracker/archived.html", page_id="habit-tracker", habits=habits
    )


@app.route("/tips/disable", methods=["POST"])
def disable_tips():
    """Disable tips for authenticated users"""
    if session.get("authenticated"):
        email = session.get("email")
        prefs = db.session.get(UserPreferences, email)
        if not prefs:
            prefs = UserPreferences(id=email)
            db.session.add(prefs)
        prefs.has_seen_tutorial = True
        db.session.commit()
    return redirect(request.referrer or url_for("habit_tracker"))


@app.context_processor
def inject_show_tips():
    """Inject show_tips variable into all templates"""
    show_tips = False
    if session.get("authenticated"):
        email = session.get("email")
        prefs = db.session.get(UserPreferences, email)
        show_tips = not (prefs and prefs.has_seen_tutorial)
    return dict(show_tips=show_tips)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


def init_db():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    if not os.path.exists("app.db"):
        init_db()
    app.run(debug=True)
