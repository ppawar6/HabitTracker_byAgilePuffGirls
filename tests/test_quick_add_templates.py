"""
Tests for Quick Add Habit Templates feature (US24)
Test-Driven Development: Write tests first, then implement
"""

import json

import pytest

from app import app
from extensions import db
from models import Habit, HabitTemplate


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


@pytest.fixture
def authenticated_session(client):
    """Create authenticated session"""
    with client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"
    return client


@pytest.fixture
def sample_templates():
    """Create sample habit templates"""
    templates = [
        HabitTemplate(
            name="Drink 8 Glasses of Water",
            description="Stay hydrated throughout the day",
            category="Health",
            priority="Medium",
            personality_type_id=None,
        ),
        HabitTemplate(
            name="10 Min Exercise",
            description="Quick daily workout routine",
            category="Fitness",
            priority="High",
            personality_type_id=None,
        ),
        HabitTemplate(
            name="Read 10 Pages",
            description="Daily reading habit",
            category="Study",
            priority="Medium",
            personality_type_id=None,
        ),
        HabitTemplate(
            name="10 Min Meditation",
            description="Daily mindfulness practice",
            category="Mindfulness",
            priority="Medium",
            personality_type_id=None,
        ),
    ]

    for template in templates:
        db.session.add(template)
    db.session.commit()

    return templates


class TestQuickAddTemplatesAPI:
    """Test the Quick Add Templates API endpoints"""

    def test_get_templates_requires_authentication(self, client):
        """Test that getting templates requires authentication"""
        response = client.get("/habit-tracker/templates")
        assert response.status_code == 302  # Redirect to signin
        assert "/signin" in response.location or "signin" in response.location

    def test_get_templates_returns_categorized_list(self, authenticated_session, sample_templates):
        """Test that templates are returned grouped by category"""
        response = authenticated_session.get("/habit-tracker/templates")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "templates" in data
        assert "total" in data
        assert data["total"] == 4

        # Check categories exist
        templates = data["templates"]
        assert "Health" in templates
        assert "Fitness" in templates
        assert "Study" in templates
        assert "Mindfulness" in templates

    def test_get_templates_filters_existing_habits(self, authenticated_session, sample_templates):
        """Test that templates for existing habits are filtered out"""
        # Add a habit that matches a template
        habit = Habit(
            name="Drink 8 Glasses of Water",
            description="Test",
            category="Health",
            priority="Medium",
        )
        db.session.add(habit)
        db.session.commit()

        response = authenticated_session.get("/habit-tracker/templates")
        data = json.loads(response.data)

        # Should be 3 templates now (one filtered out)
        assert data["total"] == 3

        # The 'Drink 8 Glasses of Water' template should not be in the list
        all_template_names = []
        for category_templates in data["templates"].values():
            all_template_names.extend([t["name"] for t in category_templates])

        assert "Drink 8 Glasses of Water" not in all_template_names
        assert "10 Min Exercise" in all_template_names

    def test_add_from_template_requires_authentication(self, client):
        """Test that adding from template requires authentication"""
        response = client.post(
            "/habit-tracker/add-from-template",
            json={"template_id": 1},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_add_habit_from_template(self, authenticated_session, sample_templates):
        """Test adding a habit from a template"""
        template = sample_templates[0]

        response = authenticated_session.post(
            "/habit-tracker/add-from-template",
            json={"template_id": template.id},
            content_type="application/json",
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "habit" in data

        # Verify habit was created in database
        habit = Habit.query.filter_by(name=template.name).first()
        assert habit is not None
        assert habit.description == template.description
        assert habit.category == template.category
        assert habit.priority == template.priority

    def test_add_habit_with_customization(self, authenticated_session, sample_templates):
        """Test adding a habit from template with custom values"""
        template = sample_templates[1]

        custom_data = {
            "template_id": template.id,
            "name": "Custom Exercise Name",
            "description": "My custom description",
            "priority": "High",
        }

        response = authenticated_session.post(
            "/habit-tracker/add-from-template", json=custom_data, content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        # Verify custom values were used
        habit = Habit.query.filter_by(name="Custom Exercise Name").first()
        assert habit is not None
        assert habit.description == "My custom description"
        assert habit.priority == "High"

    def test_cannot_add_duplicate_habit(self, authenticated_session, sample_templates):
        """Test that duplicate habits cannot be added"""
        template = sample_templates[0]

        # Add habit first time
        authenticated_session.post(
            "/habit-tracker/add-from-template",
            json={"template_id": template.id},
            content_type="application/json",
        )

        # Try to add same habit again
        response = authenticated_session.post(
            "/habit-tracker/add-from-template",
            json={"template_id": template.id},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "already exists" in data["error"].lower()

    def test_add_habit_with_invalid_template(self, authenticated_session):
        """Test adding habit with non-existent template ID"""
        response = authenticated_session.post(
            "/habit-tracker/add-from-template",
            json={"template_id": 9999},
            content_type="application/json",
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False

    def test_add_habit_without_name(self, authenticated_session):
        """Test that habit name is required"""
        response = authenticated_session.post(
            "/habit-tracker/add-from-template", json={"name": ""}, content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False


class TestTemplateData:
    """Test the template data structure"""

    def test_templates_have_correct_structure(self, authenticated_session, sample_templates):
        """Test that each template has all required fields"""
        response = authenticated_session.get("/habit-tracker/templates")
        data = json.loads(response.data)

        # Get first template from any category
        first_category = list(data["templates"].keys())[0]
        first_template = data["templates"][first_category][0]

        # Check required fields
        assert "id" in first_template
        assert "name" in first_template
        assert "description" in first_template
        assert "category" in first_template
        assert "priority" in first_template

    def test_templates_grouped_by_category(self, authenticated_session, sample_templates):
        """Test that templates are properly grouped by category"""
        response = authenticated_session.get("/habit-tracker/templates")
        data = json.loads(response.data)

        templates = data["templates"]

        # Verify each category only contains templates from that category
        for category, category_templates in templates.items():
            for template in category_templates:
                assert template["category"] == category


class TestTemplateIntegration:
    """Test integration with existing habit features"""

    def test_notification_created_when_adding_from_template(
        self, authenticated_session, sample_templates
    ):
        """Test that notification is created when adding habit from template"""
        from models import Notification

        template = sample_templates[0]

        authenticated_session.post(
            "/habit-tracker/add-from-template",
            json={"template_id": template.id},
            content_type="application/json",
        )

        # Check notification was created
        notification = Notification.query.filter_by(
            user_email="test@example.com", action_type="added"
        ).first()

        assert notification is not None
        assert template.name in notification.message

    def test_template_respects_archived_habits(self, authenticated_session, sample_templates):
        """Test that archived habits with same name don't prevent template from showing"""
        template = sample_templates[0]

        # Create archived habit with template name
        habit = Habit(
            name=template.name,
            description="Test",
            category="Health",
            priority="Medium",
            is_archived=True,
        )
        db.session.add(habit)
        db.session.commit()

        response = authenticated_session.get("/habit-tracker/templates")
        data = json.loads(response.data)

        # Template should still be filtered out (habit exists regardless of archived status)
        all_template_names = []
        for category_templates in data["templates"].values():
            all_template_names.extend([t["name"] for t in category_templates])

        assert template.name not in all_template_names

    def test_template_respects_paused_habits(self, authenticated_session, sample_templates):
        """Test that paused habits with same name don't prevent template from showing"""
        template = sample_templates[1]

        # Create paused habit with template name
        habit = Habit(
            name=template.name,
            description="Test",
            category="Fitness",
            priority="High",
            is_paused=True,
        )
        db.session.add(habit)
        db.session.commit()

        response = authenticated_session.get("/habit-tracker/templates")
        data = json.loads(response.data)

        # Template should be filtered out
        all_template_names = []
        for category_templates in data["templates"].values():
            all_template_names.extend([t["name"] for t in category_templates])

        assert template.name not in all_template_names
