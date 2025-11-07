from datetime import datetime, timezone

from extensions import db


class UserPreferences(db.Model):
    """Store user preferences including onboarding status and theme preferences"""
    id = db.Column(db.String(100), primary_key=True)  # Store email as ID
    has_seen_tutorial = db.Column(db.Boolean, default=False)
    theme = db.Column(db.String(10), default="light")  # 'light' or 'dark'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_dates = db.Column(db.Text)
    user_id = db.Column(db.Integer, nullable=True, default=0)
    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    is_paused = db.Column(db.Boolean, default=False)
    paused_at = db.Column(db.DateTime, nullable=True)
