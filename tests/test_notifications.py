"""Test notification functionality including toggle, creation, fetching, and marking as read."""

from extensions import db
from models import Habit, Notification, UserPreferences


def test_toggle_notifications_enables_when_disabled(logged_in_client, app):
    """Test that POST /notifications/toggle enables notifications when currently disabled."""
    # Arrange: Set notifications to disabled
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=False)
        db.session.add(prefs)
        db.session.commit()

    # Act
    response = logged_in_client.post("/notifications/toggle", follow_redirects=False)

    # Assert
    assert response.status_code == 200
    with app.app_context():
        prefs = UserPreferences.query.get("test@example.com")
        assert prefs.notifications_enabled is True


def test_toggle_notifications_disables_when_enabled(logged_in_client, app):
    """Test that POST /notifications/toggle disables notifications when currently enabled."""
    # Arrange: Set notifications to enabled
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        db.session.add(prefs)
        db.session.commit()

    # Act
    response = logged_in_client.post("/notifications/toggle", follow_redirects=False)

    # Assert
    assert response.status_code == 200
    with app.app_context():
        prefs = UserPreferences.query.get("test@example.com")
        assert prefs.notifications_enabled is False


def test_toggle_notifications_creates_preferences_if_not_exists(logged_in_client, app):
    """Test that POST /notifications/toggle creates preferences if they don't exist."""
    # Act
    response = logged_in_client.post("/notifications/toggle", follow_redirects=False)

    # Assert
    assert response.status_code == 200
    with app.app_context():
        prefs = UserPreferences.query.get("test@example.com")
        assert prefs is not None
        assert prefs.notifications_enabled is False  # Toggled from default True to False


def test_get_notifications_returns_all_user_notifications(logged_in_client, app):
    """Test that GET /notifications returns all notifications for logged-in user."""
    # Arrange: Create some notifications
    with app.app_context():
        notif1 = Notification(
            user_email="test@example.com",
            message="Added habit: Morning Exercise",
            action_type="added",
            habit_name="Morning Exercise",
            is_read=False,
        )
        notif2 = Notification(
            user_email="test@example.com",
            message="Paused habit: Evening Reading",
            action_type="paused",
            habit_name="Evening Reading",
            is_read=True,
        )
        notif3 = Notification(
            user_email="other@example.com",
            message="Should not appear",
            action_type="added",
            habit_name="Other Habit",
            is_read=False,
        )
        db.session.add_all([notif1, notif2, notif3])
        db.session.commit()

    # Act
    response = logged_in_client.get("/notifications")

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["notifications"]) == 2
    messages = [notif["message"] for notif in data["notifications"]]
    assert "Paused habit: Evening Reading" in messages
    assert "Added habit: Morning Exercise" in messages


def test_get_notifications_returns_unread_count(logged_in_client, app):
    """Test that GET /notifications returns the count of unread notifications."""
    # Arrange: Create notifications with mixed read status
    with app.app_context():
        notif1 = Notification(
            user_email="test@example.com",
            message="Notification 1",
            action_type="added",
            is_read=False,
        )
        notif2 = Notification(
            user_email="test@example.com",
            message="Notification 2",
            action_type="deleted",
            is_read=False,
        )
        notif3 = Notification(
            user_email="test@example.com",
            message="Notification 3",
            action_type="edited",
            is_read=True,
        )
        db.session.add_all([notif1, notif2, notif3])
        db.session.commit()

    # Act
    response = logged_in_client.get("/notifications")

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["unread_count"] == 2


def test_mark_notification_as_read(logged_in_client, app):
    """Test that POST /notifications/<id>/read marks a notification as read."""
    # Arrange
    with app.app_context():
        notif = Notification(
            user_email="test@example.com",
            message="Test notification",
            action_type="added",
            is_read=False,
        )
        db.session.add(notif)
        db.session.commit()
        notif_id = notif.id

    # Act
    response = logged_in_client.post(f"/notifications/{notif_id}/read", follow_redirects=False)

    # Assert
    assert response.status_code == 200
    with app.app_context():
        updated_notif = Notification.query.get(notif_id)
        assert updated_notif.is_read is True


def test_mark_all_notifications_as_read(logged_in_client, app):
    """Test that POST /notifications/read-all marks all user notifications as read."""
    # Arrange
    with app.app_context():
        notif1 = Notification(
            user_email="test@example.com",
            message="Notification 1",
            action_type="added",
            is_read=False,
        )
        notif2 = Notification(
            user_email="test@example.com",
            message="Notification 2",
            action_type="deleted",
            is_read=False,
        )
        notif3 = Notification(
            user_email="other@example.com",
            message="Other user notification",
            action_type="edited",
            is_read=False,
        )
        db.session.add_all([notif1, notif2, notif3])
        db.session.commit()

    # Act
    response = logged_in_client.post("/notifications/read-all", follow_redirects=False)

    # Assert
    assert response.status_code == 200
    with app.app_context():
        user_notifs = Notification.query.filter_by(user_email="test@example.com").all()
        assert all(notif.is_read for notif in user_notifs)
        # Other user's notification should remain unread
        other_notif = Notification.query.filter_by(user_email="other@example.com").first()
        assert other_notif.is_read is False


def test_notification_requires_auth(client):
    """Test that notification endpoints require authentication."""
    # Act & Assert
    response = client.get("/notifications")
    assert response.status_code == 302
    assert "/signin" in response.location

    response = client.post("/notifications/toggle")
    assert response.status_code == 302
    assert "/signin" in response.location

    response = client.post("/notifications/1/read")
    assert response.status_code == 302
    assert "/signin" in response.location


def test_add_habit_creates_notification_when_enabled(logged_in_client, app):
    """Test that adding a habit creates a notification when notifications are enabled."""
    # Arrange: Enable notifications
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        db.session.add(prefs)
        db.session.commit()

    # Act: Add a habit
    response = logged_in_client.post(
        "/habit-tracker",
        data={"name": "New Habit", "description": "Test", "category": "Health"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(user_email="test@example.com").all()
        assert len(notifications) == 1
        assert notifications[0].action_type == "added"
        assert "New Habit" in notifications[0].message


def test_add_habit_no_notification_when_disabled(logged_in_client, app):
    """Test that adding a habit does NOT create a notification when notifications are disabled."""
    # Arrange: Disable notifications
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=False)
        db.session.add(prefs)
        db.session.commit()

    # Act: Add a habit
    response = logged_in_client.post(
        "/habit-tracker",
        data={"name": "New Habit", "description": "Test", "category": "Health"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(user_email="test@example.com").all()
        assert len(notifications) == 0


def test_delete_habit_creates_notification(logged_in_client, app):
    """Test that deleting a habit creates a notification when enabled."""
    # Arrange
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        habit = Habit(name="Habit to Delete")
        db.session.add(prefs)
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/delete/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(
            user_email="test@example.com", action_type="deleted"
        ).all()
        assert len(notifications) == 1
        assert "Habit to Delete" in notifications[0].message


def test_pause_habit_creates_notification(logged_in_client, app):
    """Test that pausing a habit creates a notification when enabled."""
    # Arrange
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        habit = Habit(name="Habit to Pause")
        db.session.add(prefs)
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/pause/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(
            user_email="test@example.com", action_type="paused"
        ).all()
        assert len(notifications) == 1
        assert "Habit to Pause" in notifications[0].message


def test_archive_habit_creates_notification(logged_in_client, app):
    """Test that archiving a habit creates a notification when enabled."""
    # Arrange
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        habit = Habit(name="Habit to Archive")
        db.session.add(prefs)
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/archive/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(
            user_email="test@example.com", action_type="archived"
        ).all()
        assert len(notifications) == 1
        assert "Habit to Archive" in notifications[0].message


def test_update_habit_creates_notification(logged_in_client, app):
    """Test that updating a habit name creates a notification when enabled."""
    # Arrange
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        habit = Habit(name="Old Name")
        db.session.add(prefs)
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(
        f"/habit-tracker/update/{habit_id}", data={"name": "New Name"}, follow_redirects=False
    )

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(
            user_email="test@example.com", action_type="edited"
        ).all()
        assert len(notifications) == 1
        assert "Old Name" in notifications[0].message
        assert "New Name" in notifications[0].message


def test_resume_habit_creates_notification(logged_in_client, app):
    """Test that resuming a paused habit creates a notification when enabled."""
    # Arrange
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        habit = Habit(name="Paused Habit", is_paused=True)
        db.session.add(prefs)
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/resume/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(
            user_email="test@example.com", action_type="resumed"
        ).all()
        assert len(notifications) == 1
        assert "Paused Habit" in notifications[0].message


def test_unarchive_habit_creates_notification(logged_in_client, app):
    """Test that unarchiving a habit creates a notification when enabled."""
    # Arrange
    with app.app_context():
        prefs = UserPreferences(id="test@example.com", notifications_enabled=True)
        habit = Habit(name="Archived Habit", is_archived=True)
        db.session.add(prefs)
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/unarchive/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        notifications = Notification.query.filter_by(
            user_email="test@example.com", action_type="unarchived"
        ).all()
        assert len(notifications) == 1
        assert "Archived Habit" in notifications[0].message
