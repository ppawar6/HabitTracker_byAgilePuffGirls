import pytest

from app import app, db
from models import Habit


@pytest.fixture
def client():
    """
    Test client with:
    - TESTING mode enabled
    - DB tables created
    - session authenticated for /habit-tracker
    """
    app.config["TESTING"] = True

    with app.test_client() as client:
        # Make sure tables exist
        with app.app_context():
            db.create_all()

        # Fake login
        with client.session_transaction() as sess:
            sess["authenticated"] = True
            sess["email"] = "test@example.com"

        yield client


def test_habit_form_has_description_char_counter(client):
    """
    US28: The habit creation form should show a character counter
    for the description/intention field, with 200 max.
    """
    resp = client.get("/habit-tracker")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")

    # Textarea exists
    assert 'id="habit-description"' in html

    # Counter wrapper + span + max length
    assert 'id="description-char-counter"' in html
    assert 'id="description-char-count"' in html
    assert 'data-max-length="200"' in html
    assert "/ 200 characters" in html


def test_description_is_truncated_on_create(client):
    """
    US28: Backend must hard-limit description to 200 characters
    even if the user submits more.
    """
    long_description = "x" * 250  # more than 200

    habit_name = "Test Habit Truncation"

    # Clean up any existing habit with this name (in case of re-runs)
    with app.app_context():
        Habit.query.filter_by(name=habit_name).delete()
        db.session.commit()

    # Create habit via POST
    resp = client.post(
        "/habit-tracker",
        data={
            "name": habit_name,
            "description": long_description,
            "category": "Health",
            "priority": "Medium",
        },
        follow_redirects=True,
    )

    # Page should load fine
    assert resp.status_code == 200

    # Check DB
    with app.app_context():
        habit = Habit.query.filter_by(name=habit_name).first()
        assert habit is not None
        assert habit.description is not None

        # Hard length check
        assert len(habit.description) == 200
        assert habit.description == long_description[:200]
