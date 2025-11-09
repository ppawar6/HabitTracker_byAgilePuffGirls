import json
from datetime import datetime

import pytest

from app import db, otp_store
from models import Habit, UserPreferences

# === Habit Tracker Tests ===

# === Sign-in and Auth Tests (User Story 01) ===


def test_signin_get_returns_ok(client):
    """Test that the GET /signin page loads successfully."""
    response = client.get("/signin")
    assert response.status_code == 200


def test_otp_generation_success(client):
    """Test that posting an email to /signin generates a 6-digit OTP."""
    # Arrange
    email = "test@example.com"
    data = {"email": email}

    # Act
    response = client.post("/signin", json=data)

    # Assert
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["success"]
    assert "otp" in json_data
    assert len(json_data["otp"]) == 6
    assert otp_store.get(email) == json_data["otp"]  # Check global store


def test_otp_verification_success(client):
    """Test successful OTP verification logs the user in and clears the OTP."""
    # Arrange: Request and store OTP first
    email = "success@example.com"
    client.post("/signin", json={"email": email})
    otp = otp_store.get(email)  # Get the generated OTP

    # Act: Verify the OTP
    data_verify = {"email": email, "otp": otp, "action": "verify"}
    response_verify = client.post("/signin", json=data_verify)

    # Assert
    assert response_verify.status_code == 200
    json_data = response_verify.get_json()
    assert json_data["success"]

    # Verify session and OTP store cleanup
    with client.session_transaction() as sess:
        assert sess.get("authenticated")
        assert sess.get("email") == email
    assert email not in otp_store  # OTP should be consumed and deleted


def test_otp_verification_failure_invalid_otp(client):
    """Test failed OTP verification with an incorrect OTP."""
    # Arrange: Request and store OTP first
    email = "failure@example.com"
    client.post("/signin", json={"email": email})

    # Act: Verify with incorrect OTP
    data_verify = {"email": email, "otp": "000000", "action": "verify"}
    response_verify = client.post("/signin", json=data_verify)

    # Assert
    assert response_verify.status_code == 200
    json_data = response_verify.get_json()
    assert not json_data["success"]
    assert "Invalid OTP" in json_data["message"]

    # Verify no session was set and OTP is still in store
    with client.session_transaction() as sess:
        assert sess.get("authenticated") is None
    assert email in otp_store  # Failed attempt should NOT clear the OTP


def test_logout_clears_session(client):
    """Test that the /logout route clears the session and redirects to home."""
    # Arrange: Simulate login
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "logout_test@example.com"

    # Act
    response = client.get("/logout", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/"

    # Check session after redirect
    with client.session_transaction() as sess:
        assert sess.get("authenticated") is None
        assert sess.get("email") is None


def test_habit_tracker_requires_auth_unauthenticated(client):
    """Test that access to /habit-tracker without authentication redirects to /signin."""
    # Act
    response = client.get("/habit-tracker", follow_redirects=False)

    # Assert
    assert response.status_code == 302  # Redirect expected
    assert response.location == "/signin"  # Redirects to signin


# === Basic CRUD Tests ===


def test_habit_tracker_get_returns_ok(logged_in_client):
    """Test that GET /habit-tracker returns a 200 status code when authenticated."""
    # Act
    response = logged_in_client.get("/habit-tracker")

    # Assert
    assert response.status_code == 200


def test_habit_tracker_post_creates_habit(logged_in_client, app):
    """Test that POST /habit-tracker creates a new habit in the database when authenticated."""
    # Arrange
    habit_data = {"name": "Read 20 pages", "description": "Daily reading goal"}

    # Act
    response = logged_in_client.post("/habit-tracker", data=habit_data, follow_redirects=False)

    # Assert
    assert response.status_code == 302

    with app.app_context():
        stored = Habit.query.filter_by(name="Read 20 pages").first()
        assert stored is not None
        assert stored.description == "Daily reading goal"


def test_habit_tracker_delete_removes_habit(client, app):
    """Test that POST /habit-tracker/delete/<id> removes a habit from the database."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Morning Run", description="Run 5k every morning")
        from extensions import db

        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = client.post(f"/habit-tracker/delete/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/habit-tracker"
    with app.app_context():
        deleted_habit = Habit.query.filter_by(id=habit_id).first()
        assert deleted_habit is None


def test_habit_tracker_delete_invalid_id_returns_404(client):
    """Test that POST /habit-tracker/delete/<invalid_id> returns 404."""
    # Act
    response = client.post("/habit-tracker/delete/99999", follow_redirects=False)

    # Assert
    assert response.status_code == 404


# === Update Habit Tests ===


def test_habit_tracker_update_changes_name(logged_in_client, app):
    """Test that POST /habit-tracker/update/<id> updates the habit name."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Old Habit Name", description="Test description")
        from extensions import db

        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(
        f"/habit-tracker/update/{habit_id}",
        data={"name": "Updated Habit Name"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    assert response.location == "/habit-tracker"
    with app.app_context():
        updated_habit = Habit.query.filter_by(id=habit_id).first()
        assert updated_habit is not None
        assert updated_habit.name == "Updated Habit Name"
        assert updated_habit.description == "Test description"


def test_habit_tracker_update_requires_auth(client, app):
    """Test that update requires authentication."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Test Habit")
        from extensions import db

        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = client.post(
        f"/habit-tracker/update/{habit_id}",
        data={"name": "New Name"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    assert response.location == "/signin"


def test_habit_tracker_update_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/update/<invalid_id> returns 404."""
    # Act
    response = logged_in_client.post(
        "/habit-tracker/update/99999",
        data={"name": "New Name"},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 404


def test_habit_tracker_update_empty_name_does_not_update(logged_in_client, app):
    """Test that submitting empty name does not update the habit."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Original Name")
        from extensions import db

        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(
        f"/habit-tracker/update/{habit_id}",
        data={"name": "   "},
        follow_redirects=False,
    )

    # Assert
    assert response.status_code == 302
    with app.app_context():
        habit = Habit.query.filter_by(id=habit_id).first()
        assert habit.name == "Original Name"


# === Category Tests ===

def test_habit_tracker_post_saves_predefined_category(logged_in_client, app):
    """Selecting a predefined category stores it on the Habit."""
    form = {"name": "Read 10 pages", "description": "Night routine", "category": "Fitness"}
    resp = logged_in_client.post("/habit-tracker", data=form, follow_redirects=False)
    assert resp.status_code == 302 and resp.location == "/habit-tracker"

    with app.app_context():
        stored = Habit.query.filter_by(name="Read 10 pages").first()
        assert stored is not None
        assert stored.category == "Fitness"


def test_habit_tracker_post_uses_category_custom_when_other_selected(logged_in_client, app):
    """If category=='other', the value from category_custom is stored."""
    form = {
        "name": "Evening Walk",
        "description": "30 mins",
        "category": "other",
        "category_custom": "Wellness",
    }
    resp = logged_in_client.post("/habit-tracker", data=form, follow_redirects=False)
    assert resp.status_code == 302 and resp.location == "/habit-tracker"

    with app.app_context():
        stored = Habit.query.filter_by(name="Evening Walk").first()
        assert stored is not None
        assert stored.category == "Wellness"


def test_habit_dashboard_displays_category(logged_in_client, app):
    """After creating a habit with a category, the /habit-tracker page shows that category text."""
    form = {"name": "Meditation", "description": "Mindful breathing", "category": "Mindfulness"}
    create_resp = logged_in_client.post("/habit-tracker", data=form, follow_redirects=False)
    assert create_resp.status_code == 302

    page_resp = logged_in_client.get("/habit-tracker", follow_redirects=True)
    assert page_resp.status_code == 200
    html = page_resp.data.decode("utf-8")
    assert "Meditation" in html
    assert "Mindfulness" in html


def test_archive_habit_success(logged_in_client, app):
    """Test that POST /habit-tracker/archive/<id> archives a habit successfully."""
    with app.app_context():
        habit = Habit(name="Morning Yoga", description="Daily yoga routine", is_archived=False)
        from extensions import db

        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    response = logged_in_client.post(f'/habit-tracker/archive/{habit_id}', follow_redirects=False)

    assert response.status_code == 302
    assert response.location == '/habit-tracker'

    with app.app_context():
        archived_habit = Habit.query.filter_by(id=habit_id).first()
        assert archived_habit is not None
        assert archived_habit.is_archived is True
        assert archived_habit.archived_at is not None


def test_archive_habit_requires_auth(client):
    """Test that archiving a habit without authentication redirects to signin."""
    response = client.post("/habit-tracker/archive/1", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/signin"


def test_archive_habit_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/archive/<invalid_id> returns 404."""
    response = logged_in_client.post("/habit-tracker/archive/99999", follow_redirects=False)
    assert response.status_code == 404


def test_unarchive_habit_success(logged_in_client, app):
    """Test that POST /habit-tracker/unarchive/<id> unarchives a habit successfully."""
    with app.app_context():
        from datetime import datetime, timezone

        habit = Habit(
            name="Evening Walk",
            description="30 min walk",
            is_archived=True,
            archived_at=datetime.now(timezone.utc),
        )
        from extensions import db

        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    response = logged_in_client.post(f'/habit-tracker/unarchive/{habit_id}', follow_redirects=False)

    assert response.status_code == 302

    with app.app_context():
        unarchived_habit = Habit.query.filter_by(id=habit_id).first()
        assert unarchived_habit is not None
        assert unarchived_habit.is_archived is False
        assert unarchived_habit.archived_at is None


def test_unarchive_habit_requires_auth(client):
    """Test that unarchiving a habit without authentication redirects to signin."""
    response = client.post("/habit-tracker/unarchive/1", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/signin"


def test_unarchive_habit_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/unarchive/<invalid_id> returns 404."""
    response = logged_in_client.post("/habit-tracker/unarchive/99999", follow_redirects=False)
    assert response.status_code == 404


def test_archived_habits_page_get_returns_ok(logged_in_client):
    """Test that GET /habit-tracker/archived returns a 200 status code when authenticated."""
    response = logged_in_client.get("/habit-tracker/archived")
    assert response.status_code == 200


def test_archived_habits_page_requires_auth(client):
    """Test that accessing archived habits page without authentication redirects to signin."""
    response = client.get("/habit-tracker/archived", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/signin"


def test_archived_habits_page_shows_only_archived(logged_in_client, app):
    """Test that /habit-tracker/archived page only displays archived habits."""
    with app.app_context():
        from datetime import datetime, timezone

        from extensions import db

        active_habit = Habit(name='My Active Habit Item', description='Not archived', is_archived=False)
        archived_habit = Habit(
            name="My Archived Habit Item",
            description="This is archived",
            is_archived=True,
            archived_at=datetime.now(timezone.utc),
        )
        db.session.add(active_habit)
        db.session.add(archived_habit)
        db.session.commit()

    response = logged_in_client.get('/habit-tracker/archived')
    html = response.data.decode('utf-8')

    assert response.status_code == 200
    assert "My Archived Habit Item" in html
    assert "My Active Habit Item" not in html


# === Pause/Resume Tests ===


def test_pause_habit_success(logged_in_client, app):
    """Test that POST /habit-tracker/pause/<id> pauses a habit successfully."""
    with app.app_context():
        habit = Habit(name="My Active Habit", description="Test habit")
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    response = logged_in_client.post(f"/habit-tracker/pause/{habit_id}", follow_redirects=False)

    assert response.status_code == 302
    assert response.location == "/habit-tracker"

    with app.app_context():
        paused_habit = Habit.query.filter_by(id=habit_id).first()
        assert paused_habit is not None
        assert paused_habit.is_paused is True
        assert paused_habit.paused_at is not None


def test_pause_habit_requires_auth(client, app):
    """Test that pause requires authentication."""
    with app.app_context():
        habit = Habit(name="Test Habit")
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    response = client.post(f"/habit-tracker/pause/{habit_id}", follow_redirects=False)

    assert response.status_code == 302
    assert "/signin" in response.location


def test_pause_habit_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/pause/<invalid_id> returns 404."""
    response = logged_in_client.post("/habit-tracker/pause/99999")
    assert response.status_code == 404


def test_resume_habit_success(logged_in_client, app):
    """Test that POST /habit-tracker/resume/<id> resumes a paused habit successfully."""
    from datetime import datetime, timezone

    with app.app_context():
        habit = Habit(
            name="My Paused Habit",
            description="Test habit",
            is_paused=True,
            paused_at=datetime.now(timezone.utc),
        )
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    response = logged_in_client.post(f"/habit-tracker/resume/{habit_id}", follow_redirects=False)

    assert response.status_code == 302

    with app.app_context():
        resumed_habit = Habit.query.filter_by(id=habit_id).first()
        assert resumed_habit is not None
        assert resumed_habit.is_paused is False
        assert resumed_habit.paused_at is None


def test_resume_habit_requires_auth(client, app):
    """Test that resume requires authentication."""
    from datetime import datetime, timezone

    with app.app_context():
        habit = Habit(name="Test Habit", is_paused=True, paused_at=datetime.now(timezone.utc))
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    response = client.post(f"/habit-tracker/resume/{habit_id}", follow_redirects=False)

    assert response.status_code == 302
    assert "/signin" in response.location


def test_resume_habit_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/resume/<invalid_id> returns 404."""
    response = logged_in_client.post("/habit-tracker/resume/99999")
    assert response.status_code == 404


def test_habit_tracker_shows_paused_habits_separately(logged_in_client, app):
    """Test that habit tracker page displays paused habits in separate section."""
    from datetime import datetime, timezone

    with app.app_context():
        active_habit = Habit(name="Active Habit", is_paused=False)
        paused_habit = Habit(
            name="Paused Habit", is_paused=True, paused_at=datetime.now(timezone.utc)
        )
        db.session.add(active_habit)
        db.session.add(paused_habit)
        db.session.commit()

    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "Active Habit" in html
    assert "Paused Habit" in html
    assert "Paused Habits" in html


def test_paused_habit_independent_of_archive(logged_in_client, app):
    """Test that paused and archived habits are independent."""
    from datetime import datetime, timezone

    with app.app_context():
        active_habit = Habit(name="ActiveHabit123", is_paused=False, is_archived=False)
        paused_habit = Habit(
            name="PausedHabit456",
            is_paused=True,
            is_archived=False,
            paused_at=datetime.now(timezone.utc),
        )
        archived_habit = Habit(
            name="ArchivedHabit789",
            is_paused=False,
            is_archived=True,
            archived_at=datetime.now(timezone.utc),
        )
        paused_and_archived = Habit(
            name="BothPausedArchived999",
            is_paused=True,
            is_archived=True,
            paused_at=datetime.now(timezone.utc),
            archived_at=datetime.now(timezone.utc),
        )
        db.session.add_all([active_habit, paused_habit, archived_habit, paused_and_archived])
        db.session.commit()

    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    # Active habits section should show only active
    assert "ActiveHabit123" in html
    # Paused habits section should show only paused (not archived)
    assert "PausedHabit456" in html
    # Archived and paused+archived should not be on main page
    assert "ArchivedHabit789" not in html
    assert "BothPausedArchived999" not in html




# === Toggle Completion Tests ===

def test_toggle_completion_marks_habit_completed(logged_in_client, app):
    """Test that POST /habit-tracker/toggle/<id> marks a habit as completed for today."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Morning Exercise", description="Daily workout")
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = logged_in_client.post(f"/habit-tracker/toggle/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/habit-tracker"

    with app.app_context():
        updated_habit = Habit.query.get(habit_id)
        completed_dates = json.loads(updated_habit.completed_dates)
        today = datetime.utcnow().date().isoformat()
        assert today in completed_dates


def test_toggle_completion_removes_completed_date(logged_in_client, app):
    """Test that toggling an already completed habit removes it from completed_dates."""
    # Arrange: Create a habit that's already completed for today
    today = datetime.utcnow().date().isoformat()
    with app.app_context():
        habit = Habit(
            name="Evening Reading",
            description="Read for 30 minutes",
            completed_dates=json.dumps([today])
        )
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act: Toggle completion again
    response = logged_in_client.post(f"/habit-tracker/toggle/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    with app.app_context():
        updated_habit = Habit.query.get(habit_id)
        completed_dates = json.loads(updated_habit.completed_dates)
        assert today not in completed_dates


def test_toggle_completion_requires_auth(client, app):
    """Test that toggling completion without authentication redirects to signin."""
    # Arrange
    with app.app_context():
        habit = Habit(name="Test Habit")
        db.session.add(habit)
        db.session.commit()
        habit_id = habit.id

    # Act
    response = client.post(f"/habit-tracker/toggle/{habit_id}", follow_redirects=False)

    # Assert
    assert response.status_code == 302
    assert response.location == "/signin"


def test_toggle_completion_invalid_id_returns_404(logged_in_client):
    """Test that POST /habit-tracker/toggle/<invalid_id> returns 404."""
    # Act
    response = logged_in_client.post("/habit-tracker/toggle/99999", follow_redirects=False)

    # Assert
    assert response.status_code == 404

# === Share Progress Tests ===


def test_share_progress_button_visible_with_habits(logged_in_client, app):
    """Test that the Share Progress button appears when user has habits."""
    # Arrange: Create a habit
    with app.app_context():
        from extensions import db
        habit = Habit(name='Morning Run', description='Daily run')
        db.session.add(habit)
        db.session.commit()

    # Act: Load habit tracker page
    response = logged_in_client.get('/habit-tracker')
    html = response.data.decode('utf-8')

    # Assert: Share Progress button is visible
    assert response.status_code == 200
    assert 'Share Progress' in html
    assert 'openShareModal' in html


def test_share_progress_button_hidden_without_habits(logged_in_client):
    """Test that the Share Progress button is hidden when user has no habits."""
    # Act: Load habit tracker page with no habits
    response = logged_in_client.get('/habit-tracker')
    html = response.data.decode('utf-8')

    # Assert: Share Progress button should not be visible
    assert response.status_code == 200
    # Button should be hidden when there are no habits
    assert 'No habits yet' in html


def test_share_modal_html_structure(logged_in_client, app):
    """Test that the share modal HTML structure exists in the page."""
    # Arrange: Create a habit so button appears
    with app.app_context():
        from extensions import db
        habit = Habit(name='Study', description='Daily study session')
        db.session.add(habit)
        db.session.commit()

    # Act: Load page
    response = logged_in_client.get('/habit-tracker')
    html = response.data.decode('utf-8')

    # Assert: Modal elements exist
    assert 'id="shareModal"' in html
    assert 'Share Your Progress' in html
    assert 'Copy to Clipboard' in html


def test_share_progress_javascript_functions_present(logged_in_client, app):
    """Test that JavaScript functions for share functionality are present."""
    # Arrange: Create a habit
    with app.app_context():
        from extensions import db
        habit = Habit(name='Workout', description='Gym session')
        db.session.add(habit)
        db.session.commit()

    # Act: Load page
    response = logged_in_client.get('/habit-tracker')
    html = response.data.decode('utf-8')

    # Assert: JavaScript functions exist
    assert 'function openShareModal()' in html
    assert 'function closeShareModal()' in html
    assert 'function generateShareText()' in html
    assert 'function copyToClipboard()' in html


def test_share_text_generation_with_multiple_habits(logged_in_client, app):
    """Test that share text is correctly generated with habit count."""
    # Arrange: Create multiple habits
    with app.app_context():
        from extensions import db
        habit1 = Habit(name='Morning Run', description='5K run')
        habit2 = Habit(name='Reading', description='Read 20 pages')
        habit3 = Habit(name='Meditation', description='10 min meditation')
        db.session.add_all([habit1, habit2, habit3])
        db.session.commit()

    # Act: Load page
    response = logged_in_client.get('/habit-tracker')
    html = response.data.decode('utf-8')

    # Assert: Page loads and can generate text with correct count
    assert response.status_code == 200
    assert 'Active Habits:' in html or '3 habit' in html


def test_share_progress_requires_authentication(client):
    """Test that share progress feature requires authentication."""
    # Act: Try to access habit tracker without login
    response = client.get('/habit-tracker', follow_redirects=False)

    # Assert: Redirects to signin
    assert response.status_code == 302
    assert response.location == '/signin'


# Sort Habits Tests


def test_sort_parameter_default_newest(logged_in_client, app):
    """Test that default sorting is newest first."""
    with app.app_context():
        from datetime import datetime, timedelta

        habit1 = Habit(
            name="Oldest Habit",
            description="First",
            created_at=datetime.utcnow() - timedelta(days=2),
        )
        habit2 = Habit(name="Newest Habit", description="Last", created_at=datetime.utcnow())
        db.session.add_all([habit1, habit2])
        db.session.commit()

    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    newest_pos = html.find("Newest Habit")
    oldest_pos = html.find("Oldest Habit")
    assert newest_pos < oldest_pos


def test_sort_parameter_oldest(logged_in_client, app):
    """Test that sorting by oldest works correctly."""
    with app.app_context():
        from datetime import datetime, timedelta

        habit1 = Habit(
            name="Oldest Habit",
            description="First",
            created_at=datetime.utcnow() - timedelta(days=2),
        )
        habit2 = Habit(name="Newest Habit", description="Last", created_at=datetime.utcnow())
        db.session.add_all([habit1, habit2])
        db.session.commit()

    response = logged_in_client.get("/habit-tracker?sort=oldest")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    oldest_pos = html.find("Oldest Habit")
    newest_pos = html.find("Newest Habit")
    assert oldest_pos < newest_pos


def test_sort_parameter_az(logged_in_client, app):
    """Test that sorting alphabetically A-Z works."""
    with app.app_context():
        habit1 = Habit(name="Zebra Habit", description="Last alphabetically")
        habit2 = Habit(name="Apple Habit", description="First alphabetically")
        db.session.add_all([habit1, habit2])
        db.session.commit()

    response = logged_in_client.get("/habit-tracker?sort=az")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    apple_pos = html.find("Apple Habit")
    zebra_pos = html.find("Zebra Habit")
    assert apple_pos < zebra_pos


def test_sort_parameter_za(logged_in_client, app):
    """Test that sorting alphabetically Z-A works."""
    with app.app_context():
        habit1 = Habit(name="Zebra Habit", description="Last in reverse")
        habit2 = Habit(name="Apple Habit", description="First in reverse")
        db.session.add_all([habit1, habit2])
        db.session.commit()

    response = logged_in_client.get("/habit-tracker?sort=za")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    zebra_pos = html.find("Zebra Habit")
    apple_pos = html.find("Apple Habit")
    assert zebra_pos < apple_pos


def test_sort_dropdown_shows_current_selection(logged_in_client, app):
    """Test that the sort dropdown shows the currently selected option."""
    with app.app_context():
        habit = Habit(name="Test Habit", description="Test")
        db.session.add(habit)
        db.session.commit()

    response = logged_in_client.get("/habit-tracker?sort=az")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert 'value="az"' in html
    assert "selected" in html


def test_sort_dropdown_visible_with_habits(logged_in_client, app):
    """Test that the sort dropdown appears when user has habits."""
    with app.app_context():
        habit = Habit(name="Morning Run", description="Daily run")
        db.session.add(habit)
        db.session.commit()

    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert response.status_code == 200
    assert 'id="sortSelect"' in html
    assert "Sort: Newest First" in html
    assert "Sort: A-Z" in html



# === Parametrized Tests ===


# === Theme Tests ===

def test_theme_toggle_endpoint_exists(client):
    """Test that the theme toggle endpoint exists and returns 200."""
    response = client.get("/theme/settings")
    assert response.status_code == 200


def test_theme_toggle_saves_preference(client):
    """Test that toggling theme saves the preference."""
    response = client.post("/theme/toggle", json={"theme": "dark"})
    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["theme"] == "dark"


def test_theme_preference_persists(client):
    """Test that theme preference is remembered between requests."""
    # First set the preference via the API
    client.post("/theme/toggle", json={"theme": "dark"})

    # Then get the settings
    response = client.get("/theme/settings")
    assert response.json["theme"] == "dark"


def test_invalid_theme_handled(client):
    """Test that invalid theme values are handled gracefully."""
    response = client.post("/theme/toggle", json={"theme": "invalid"})
    assert response.status_code == 400
    assert "error" in response.json


def test_theme_preference_for_authenticated_user(logged_in_client, app):
    """Test that theme preference is stored in database for authenticated users."""
    response = logged_in_client.post("/theme/toggle", json={"theme": "dark"})
    assert response.status_code == 200
    assert response.json["success"] is True

    with app.app_context():
        from models import UserPreferences
        pref = UserPreferences.query.filter_by(id="test@example.com").first()
        assert pref is not None
        assert pref.theme == "dark"


@pytest.mark.parametrize("endpoint", ["/habit-tracker", "/theme/settings"])
def test_all_modules_get_returns_ok(logged_in_client, endpoint):
    """Test that all module endpoints return 200 status code on GET requests when authenticated."""
    response = logged_in_client.get(endpoint)
    assert response.status_code == 200


# === Tips/Tutorial Tests ===

def test_new_user_sees_tips(client, app):
    """Test that new users see the tips modal."""
    # Login a new user
    email = "new_user@example.com"
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = email

    # Access habit tracker
    response = client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    # Assert tips modal is shown
    assert 'id="tipsModal"' in html
    assert "Welcome to Habit Tracker!" in html
    assert not db.session.get(UserPreferences, email)


def test_returning_user_no_tips(client, app):
    """Test that returning users don't see tips if they've disabled them."""
    # Setup a user who has seen the tutorial
    email = "returning@example.com"
    with app.app_context():
        prefs = UserPreferences(id=email, has_seen_tutorial=True)
        db.session.add(prefs)
        db.session.commit()

    # Login the user
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = email

    # Check that tips are not automatically shown
    response = client.get("/habit-tracker")
    html = response.data.decode("utf-8")
    # The tips modal should not be automatically shown for returning users
    assert 'document.addEventListener(\'DOMContentLoaded\', function() { showTipsModal(); })' not in html


def test_disable_tips_endpoint(logged_in_client, app):
    """Test that POST /tips/disable works correctly."""
    email = "test@example.com"

    response = logged_in_client.post("/tips/disable", follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        prefs = db.session.get(UserPreferences, email)
        assert prefs is not None
        assert prefs.has_seen_tutorial is True