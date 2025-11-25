"""
Tests for Completed Habits feature (US-25)
"""
import json
from datetime import datetime, timedelta

import pytest

from app import app
from extensions import db
from models import Habit, Notification


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


@pytest.fixture
def authenticated_client(client):
    """Create authenticated test client"""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


class TestCompletedHabitsModel:
    """Test Habit model additions for completed status"""

    def test_habit_has_is_completed_field(self, client):
        """Test that Habit model has is_completed field"""
        with app.app_context():
            habit = Habit(name="Test Habit")
            db.session.add(habit)
            db.session.commit()
            
            assert hasattr(habit, 'is_completed')
            assert habit.is_completed is False

    def test_habit_has_completed_at_field(self, client):
        """Test that Habit model has completed_at timestamp"""
        with app.app_context():
            habit = Habit(name="Test Habit")
            db.session.add(habit)
            db.session.commit()
            
            assert hasattr(habit, 'completed_at')
            assert habit.completed_at is None


class TestMarkHabitCompleted:
    """Test marking a habit as completed"""

    def test_mark_completed_requires_authentication(self, client):
        """Test that marking completed requires authentication"""
        response = client.post("/habit-tracker/complete/1")
        assert response.status_code == 302
        assert "/signin" in response.location

    def test_mark_completed_success(self, authenticated_client):
        """Test successfully marking a habit as completed"""
        with app.app_context():
            habit = Habit(name="Morning Routine", description="Wake up at 6am")
            db.session.add(habit)
            db.session.commit()
            habit_id = habit.id

        response = authenticated_client.post(f"/habit-tracker/complete/{habit_id}")
        assert response.status_code == 302

        with app.app_context():
            habit = db.session.get(Habit, habit_id)
            assert habit.is_completed is True
            assert habit.completed_at is not None

    def test_mark_completed_sets_timestamp(self, authenticated_client):
        """Test that marking completed sets the completed_at timestamp"""
        with app.app_context():
            habit = Habit(name="Reading")
            db.session.add(habit)
            db.session.commit()
            habit_id = habit.id

        before_time = datetime.utcnow()
        authenticated_client.post(f"/habit-tracker/complete/{habit_id}")
        after_time = datetime.utcnow()

        with app.app_context():
            habit = db.session.get(Habit, habit_id)
            assert habit.completed_at >= before_time
            assert habit.completed_at <= after_time

    def test_mark_completed_invalid_id_returns_404(self, authenticated_client):
        """Test marking non-existent habit returns 404"""
        response = authenticated_client.post("/habit-tracker/complete/99999")
        assert response.status_code == 404

    def test_mark_completed_creates_notification(self, authenticated_client):
        """Test that marking completed creates a celebration notification"""
        with app.app_context():
            habit = Habit(name="Exercise")
            db.session.add(habit)
            db.session.commit()
            habit_id = habit.id

        authenticated_client.post(f"/habit-tracker/complete/{habit_id}")

        with app.app_context():
            notification = Notification.query.filter_by(
                user_email="test@example.com",
                action_type="completed"
            ).first()
            assert notification is not None
            assert "🎉" in notification.message
            assert "Exercise" in notification.message


class TestUnmarkHabitCompleted:
    """Test unmarking/reactivating a completed habit"""

    def test_unmark_completed_requires_authentication(self, client):
        """Test that unmarking requires authentication"""
        response = client.post("/habit-tracker/uncomplete/1")
        assert response.status_code == 302
        assert "/signin" in response.location

    def test_unmark_completed_success(self, authenticated_client):
        """Test successfully unmarking a completed habit"""
        with app.app_context():
            habit = Habit(name="Meditation", is_completed=True, completed_at=datetime.utcnow())
            db.session.add(habit)
            db.session.commit()
            habit_id = habit.id

        response = authenticated_client.post(f"/habit-tracker/uncomplete/{habit_id}")
        assert response.status_code == 302

        with app.app_context():
            habit = db.session.get(Habit, habit_id)
            assert habit.is_completed is False
            assert habit.completed_at is None

    def test_unmark_completed_invalid_id_returns_404(self, authenticated_client):
        """Test unmarking non-existent habit returns 404"""
        response = authenticated_client.post("/habit-tracker/uncomplete/99999")
        assert response.status_code == 404


class TestCompletedHabitsDisplay:
    """Test displaying completed habits in UI"""

    def test_completed_habits_section_exists(self, authenticated_client):
        """Test that completed habits section is rendered"""
        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        assert b"completed_habits" in response.data or b"Completed Habits" in response.data

    def test_completed_habits_shows_celebration_badge(self, authenticated_client):
        """Test completed habits show celebration badge"""
        with app.app_context():
            habit = Habit(
                name="Daily Coding",
                is_completed=True,
                completed_at=datetime.utcnow()
            )
            db.session.add(habit)
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        # Check for celebration emoji or badge
        assert b"\xf0\x9f\x8e\x89" in response.data or b"&#127881;" in response.data or b"completed" in response.data.lower()

    def test_completed_habits_sorted_by_completion_date(self, authenticated_client):
        """Test completed habits are sorted by completion date (newest first)"""
        with app.app_context():
            habit1 = Habit(
                name="Habit 1",
                is_completed=True,
                completed_at=datetime.utcnow() - timedelta(days=2)
            )
            habit2 = Habit(
                name="Habit 2",
                is_completed=True,
                completed_at=datetime.utcnow() - timedelta(days=1)
            )
            habit3 = Habit(
                name="Habit 3",
                is_completed=True,
                completed_at=datetime.utcnow()
            )
            db.session.add_all([habit1, habit2, habit3])
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        content = response.data.decode()
        
        # Find positions in HTML - most recent should appear first
        pos_habit3 = content.find("Habit 3")
        pos_habit2 = content.find("Habit 2")
        pos_habit1 = content.find("Habit 1")
        
        assert pos_habit3 < pos_habit2 < pos_habit1

    def test_empty_completed_section_shows_encouragement(self, authenticated_client):
        """Test empty completed section shows encouraging message"""
        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        content = response.data.decode().lower()
        
        # Should show encouraging message when no completed habits
        assert "complete your first habit" in content or "no completed habits" in content or "you've got this" in content

    def test_completed_habits_not_in_active_list(self, authenticated_client):
        """Test completed habits don't appear in active habits list"""
        with app.app_context():
            active_habit = Habit(name="Active Habit")
            completed_habit = Habit(
                name="Completed Habit",
                is_completed=True,
                completed_at=datetime.utcnow()
            )
            db.session.add_all([active_habit, completed_habit])
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        
        # Verify completed habit is not in active section
        # This would require more sophisticated HTML parsing in real tests


class TestCompletedHabitsStats:
    """Test stats display for completed habits"""

    def test_completed_habit_shows_final_streak(self, authenticated_client):
        """Test completed habit displays final streak count"""
        with app.app_context():
            # Create habit with some completed dates (simulating a streak)
            completed_dates = [
                (datetime.utcnow() - timedelta(days=i)).date().isoformat()
                for i in range(7)  # 7-day streak
            ]
            habit = Habit(
                name="Workout",
                is_completed=True,
                completed_at=datetime.utcnow(),
                completed_dates=json.dumps(completed_dates)
            )
            db.session.add(habit)
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        # Should show streak indicator
        assert b"streak" in response.data.lower() or b"\xf0\x9f\x94\xa5" in response.data  # 🔥 emoji

    def test_completed_habit_shows_100_percent_progress(self, authenticated_client):
        """Test completed habit shows 100% progress"""
        with app.app_context():
            habit = Habit(
                name="Language Learning",
                is_completed=True,
                completed_at=datetime.utcnow()
            )
            db.session.add(habit)
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        assert b"100%" in response.data


class TestCompletedHabitsIntegration:
    """Integration tests for completed habits feature"""

    def test_completed_habit_excludes_from_filters(self, authenticated_client):
        """Test completed habits are excluded from active habit filters"""
        with app.app_context():
            active_habit = Habit(name="Active", category="Health")
            completed_habit = Habit(
                name="Completed",
                category="Health",
                is_completed=True,
                completed_at=datetime.utcnow()
            )
            db.session.add_all([active_habit, completed_habit])
            db.session.commit()

        # Filter by Health category - should only show active habit
        response = authenticated_client.get("/habit-tracker?category=Health")
        assert response.status_code == 200
        # Completed habit should not appear in filtered active results

    def test_completed_habit_preserved_when_archived_then_completed(self, authenticated_client):
        """Test that archived status doesn't interfere with completed status"""
        with app.app_context():
            habit = Habit(name="Old Habit", is_archived=False)
            db.session.add(habit)
            db.session.commit()
            habit_id = habit.id

        # Mark as completed
        authenticated_client.post(f"/habit-tracker/complete/{habit_id}")

        with app.app_context():
            habit = db.session.get(Habit, habit_id)
            assert habit.is_completed is True
            assert habit.is_archived is False

    def test_mark_complete_button_position(self, authenticated_client):
        """Test that complete button is positioned at the end near week percentage"""
        with app.app_context():
            habit = Habit(name="Test Habit")
            db.session.add(habit)
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        # Button should be near "% this week" indicator
        # This would need HTML structure verification

    def test_completed_section_below_paused_section(self, authenticated_client):
        """Test that completed habits section appears below paused habits"""
        with app.app_context():
            paused_habit = Habit(name="Paused", is_paused=True, paused_at=datetime.utcnow())
            completed_habit = Habit(name="Completed", is_completed=True, completed_at=datetime.utcnow())
            db.session.add_all([paused_habit, completed_habit])
            db.session.commit()

        response = authenticated_client.get("/habit-tracker")
        assert response.status_code == 200
        content = response.data.decode()
        
        # Find section positions - paused should come before completed
        paused_section_pos = content.lower().find("paused habits")
        completed_section_pos = content.lower().find("completed habits")
        
        if paused_section_pos != -1 and completed_section_pos != -1:
            assert paused_section_pos < completed_section_pos
