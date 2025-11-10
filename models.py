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
