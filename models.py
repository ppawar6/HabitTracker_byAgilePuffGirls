from datetime import datetime, timezone

from extensions import db


class UserPreferences(db.Model):
    """Store user preferences including onboarding status and theme preferences"""

    id = db.Column(db.String(100), primary_key=True)  # Store email as ID
    has_seen_tutorial = db.Column(db.Boolean, default=False)
    theme = db.Column(db.String(10), default="light")  # 'light' or 'dark'
    notifications_enabled = db.Column(db.Boolean, default=True)  # Enable/disable notifications
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(60))
    priority = db.Column(db.String(10), default="Medium")  # 'High', 'Medium', 'Low'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_dates = db.Column(db.Text)
    user_id = db.Column(db.Integer, nullable=True, default=0)
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime, nullable=True)


class Notification(db.Model):
    """Store notifications for user actions on habits"""

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100), nullable=False)  # User who receives the notification
    message = db.Column(db.String(255), nullable=False)  # Notification message
    action_type = db.Column(
        db.String(50), nullable=False
    )  # 'added', 'deleted', 'paused', 'archived', 'edited', 'resumed', 'unarchived'
    habit_name = db.Column(db.String(100), nullable=True)  # Name of the habit involved
    is_read = db.Column(db.Boolean, default=False)  # Whether the notification has been read
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class QuizQuestion(db.Model):
    """Store quiz questions for personality assessment"""

    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(500), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    scoring_category = db.Column(
        db.String(50), nullable=False
    )  # 'energy', 'motivation', 'structure', etc.


class PersonalityType(db.Model):
    """Store personality type definitions and characteristics"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., "Morning Warrior"
    emoji = db.Column(db.String(10), default="🎯")
    description = db.Column(db.Text, nullable=False)
    peak_time = db.Column(db.String(50))  # e.g., "6-9 AM"
    energy_level = db.Column(db.String(50))  # e.g., "High"
    motivation_style = db.Column(db.String(50))  # e.g., "Goal-driven"
    commitment_level = db.Column(db.String(50))  # e.g., "Dedicated"
    insights = db.Column(db.Text)  # JSON string of insights
    avoid_habits = db.Column(db.Text)  # JSON string of habits to avoid


class HabitTemplate(db.Model):
    """Store habit templates for recommendations"""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(60))
    priority = db.Column(db.String(10), default="Medium")
    personality_type_id = db.Column(
        db.Integer, db.ForeignKey("personality_type.id"), nullable=True
    )  # NULL = general quick-add template
    reason = db.Column(db.String(200))  # Why this habit is recommended for this personality


class UserQuizResult(db.Model):
    """Store user quiz results and personality type"""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    personality_type_id = db.Column(
        db.Integer, db.ForeignKey("personality_type.id"), nullable=False
    )
    quiz_answers = db.Column(db.Text)  # JSON string of question_id: answer pairs
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
