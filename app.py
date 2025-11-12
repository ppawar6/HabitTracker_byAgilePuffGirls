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

# ✅ NEW: ensure tables exist once, using before_request (Flask 3 compatible)
tables_created = False

@app.before_request
def ensure_tables_exist():
    global tables_created
    if not tables_created:
        db.create_all()
        tables_created = True


# Add custom Jinja filters
@app.template_filter("from_json")
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
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "Medium").strip()

        if category == "other":
            category = request.form.get("category_custom", "").strip()

        if name:
            habit = Habit(
                name=name,
                description=description or None,
                category=(category or None),
                priority=priority or "Medium",
            )
            db.session.add(habit)

            # Create notification BEFORE commit
            email = session.get("email")
            if email:
                create_notification(
                    user_email=email,
                    message=f"Added habit: {name}",
                    action_type="added",
                    habit_name=name,
                )

            db.session.commit()

        return redirect(url_for("habit_tracker"))

    # ---- GET: filters + sorting ----
    sort_by = request.args.get("sort", "priority")
    
    # NEW: Search query parameter
    search_query = request.args.get("search", "").strip()

    # Multiple category & priority filters (comma-separated in URL)
    category_param = request.args.get("category", "")
    priority_param = request.args.get("priority", "")

    if category_param:
        category_filters = [c for c in category_param.split(",") if c]
    else:
        category_filters = []

    if priority_param:
        priority_filters = [p for p in priority_param.split(",") if p]
    else:
        priority_filters = []

    # Get active habits (not archived and not paused)
    base_query = Habit.query.filter_by(is_archived=False, is_paused=False)

    # Filter by one or more categories
    if category_filters:
        base_query = base_query.filter(Habit.category.in_(category_filters))

    # Filter by one or more priority levels
    if priority_filters:
        base_query = base_query.filter(Habit.priority.in_(priority_filters))

    # NEW: Apply search filter
    if search_query:
        search_pattern = f"%{search_query}%"
        from sqlalchemy import or_
        base_query = base_query.filter(
            or_(
                Habit.name.ilike(search_pattern),
                Habit.description.ilike(search_pattern),
                Habit.category.ilike(search_pattern),
            )
        )

    habits = base_query.all()

    # Define priority order for sorting
    priority_order = {"High": 0, "Medium": 1, "Low": 2}

    if sort_by == "priority":
        habits = sorted(
            habits,
            key=lambda h: (priority_order.get(h.priority, 1), h.created_at),
            reverse=False,
        )
    elif sort_by == "az":
        habits = sorted(habits, key=lambda h: h.name.lower())
    elif sort_by == "za":
        habits = sorted(habits, key=lambda h: h.name.lower(), reverse=True)
    elif sort_by == "oldest":
        habits = sorted(habits, key=lambda h: h.created_at)
    elif sort_by == "newest":
        habits = sorted(habits, key=lambda h: h.created_at, reverse=True)
    else:
        # Default to priority sorting
        habits = sorted(
            habits,
            key=lambda h: (priority_order.get(h.priority, 1), h.created_at),
            reverse=False,
        )

    # Paused habits – hide them when searching
    if search_query:
        paused_habits = []
    else:
        paused_habits = (
            Habit.query.filter_by(is_archived=False, is_paused=True)
            .order_by(Habit.paused_at.desc())
            .all()
        )

    # Build category list for filter: default CATEGORIES + any custom ones in DB
    db_categories = {
        c for (c,) in db.session.query(Habit.category).distinct()
        if c is not None and c.strip()
    }
    filter_categories = sorted(set(CATEGORIES) | db_categories)

    return render_template(
        "apps/habit_tracker/index.html",
        page_id="habit-tracker",
        habits=habits,
        paused_habits=paused_habits,
        categories=CATEGORIES,
        current_sort=sort_by,
        filter_categories=filter_categories,
        current_categories=category_filters,   # list of selected categories
        current_priorities=priority_filters,   # list of selected priority levels
        search_query=search_query,  # NEW: Pass search query to template
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
            habit_name=habit_name,
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
                habit_name=new_name,
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
            habit_name=habit.name,
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
            habit_name=habit.name,
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
            habit_name=habit.name,
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
            habit_name=habit.name,
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


@app.route("/habit-tracker/stats")
def habit_stats():
    """View habit statistics dashboard"""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    # Get all habits
    all_habits = Habit.query.all()

    # Calculate basic statistics
    total_habits = len(all_habits)
    active_habits = len([h for h in all_habits if not h.is_archived and not h.is_paused])
    paused_habits = len([h for h in all_habits if h.is_paused and not h.is_archived])
    archived_habits = len([h for h in all_habits if h.is_archived])

    # Calculate habits by category
    category_counts = {}
    for habit in all_habits:
        category = habit.category or "Uncategorized"
        category_counts[category] = category_counts.get(category, 0) + 1

    # Sort categories by count (descending)
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    # Find most recent and oldest habit
    most_recent = None
    oldest = None
    if all_habits:
        most_recent = max(all_habits, key=lambda h: h.created_at)
        oldest = min(all_habits, key=lambda h: h.created_at)

    return render_template(
        "apps/habit_tracker/stats.html",
        page_id="habit-tracker",
        total_habits=total_habits,
        active_habits=active_habits,
        paused_habits=paused_habits,
        archived_habits=archived_habits,
        category_counts=sorted_categories,
        most_recent=most_recent,
        oldest=oldest,
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
    # Get the actual database path from the instance folder
    db_path = os.path.join(app.instance_path, "app.db")
    if not os.path.exists(db_path):
        init_db()
    app.run(debug=True)
