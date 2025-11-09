"""Notification routes for managing push notifications."""

from flask import Blueprint, jsonify, redirect, session, url_for

from extensions import db
from models import Notification, UserPreferences

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/toggle", methods=["POST"])
def toggle_notifications():
    """Toggle notification settings for the authenticated user."""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    email = session.get("email")
    prefs = db.session.get(UserPreferences, email)

    if not prefs:
        # Create preferences with notifications disabled (toggled from default True)
        prefs = UserPreferences(id=email, notifications_enabled=False)
        db.session.add(prefs)
    else:
        # Toggle the current state
        prefs.notifications_enabled = not prefs.notifications_enabled

    db.session.commit()
    return jsonify({"success": True, "notifications_enabled": prefs.notifications_enabled})


@notifications_bp.route("/settings", methods=["GET"])
def get_notification_settings():
    """Get notification settings for the authenticated user."""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    email = session.get("email")
    prefs = db.session.get(UserPreferences, email)

    # Default to True if no preferences exist
    notifications_enabled = prefs.notifications_enabled if prefs else True

    return jsonify({"notifications_enabled": notifications_enabled})


@notifications_bp.route("", methods=["GET"])
def get_notifications():
    """Get all notifications for the authenticated user."""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    email = session.get("email")
    notifications = (
        Notification.query.filter_by(user_email=email)
        .order_by(Notification.created_at.desc())
        .all()
    )

    unread_count = Notification.query.filter_by(user_email=email, is_read=False).count()

    notifications_data = [
        {
            "id": notif.id,
            "message": notif.message,
            "action_type": notif.action_type,
            "habit_name": notif.habit_name,
            "is_read": notif.is_read,
            "created_at": notif.created_at.isoformat(),
        }
        for notif in notifications
    ]

    return jsonify({"notifications": notifications_data, "unread_count": unread_count})


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
def mark_as_read(notification_id):
    """Mark a specific notification as read."""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    notification = db.session.get(Notification, notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()

    return jsonify({"success": True})


@notifications_bp.route("/read-all", methods=["POST"])
def mark_all_as_read():
    """Mark all notifications as read for the authenticated user."""
    if not session.get("authenticated"):
        return redirect(url_for("signin"))

    email = session.get("email")
    notifications = Notification.query.filter_by(user_email=email, is_read=False).all()

    for notification in notifications:
        notification.is_read = True

    db.session.commit()
    return jsonify({"success": True})


def create_notification(user_email, message, action_type, habit_name=None):
    """
    Helper function to create a notification.

    Args:
        user_email: Email of the user to notify
        message: Notification message
        action_type: Type of action ('added', 'deleted', 'paused', 'archived', 'edited', 'resumed', 'unarchived')
        habit_name: Name of the habit (optional)

    Note: This function adds the notification to the session but does NOT commit.
    The caller is responsible for committing the transaction.
    """
    # Check if notifications are enabled for this user
    prefs = db.session.get(UserPreferences, user_email)

    # Default to enabled if preferences don't exist yet
    if prefs and not prefs.notifications_enabled:
        print(f"[NOTIFICATION] Skipped for {user_email} - notifications disabled")
        return  # Don't create notification if disabled

    print(f"[NOTIFICATION] Creating notification for {user_email}: {message}")
    notification = Notification(
        user_email=user_email,
        message=message,
        action_type=action_type,
        habit_name=habit_name,
    )
    db.session.add(notification)
    print(f"[NOTIFICATION] Added notification to session for {user_email}")
