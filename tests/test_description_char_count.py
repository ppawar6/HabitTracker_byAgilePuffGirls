from urllib.parse import urlparse

from app import Habit, app, db


def login(test_client):
    """
    Helper: fake-login by setting session['authenticated'] + email
    so /habit-tracker doesn't redirect to /signin.
    """
    with test_client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"


def ensure_tables():
    """
    Make sure all tables exist for this test module.

    Other tests in the suite may drop tables or use their own fixtures,
    so we defensively call create_all() here to avoid 'no such table' errors.
    """
    with app.app_context():
        db.create_all()


def test_habit_form_has_description_char_counter():
    """
    UI: Habit form should show:
      - description textarea
      - explicit 200-char limit text
      - a live counter element
      - max length hint via data-max-length or maxlength
    """
    ensure_tables()

    client = app.test_client()
    login(client)

    response = client.get("/habit-tracker")
    assert response.status_code == 200

    html = response.data.decode("utf-8")

    # textarea must exist
    assert 'id="habit-description"' in html

    # max length must be encoded in the DOM
    assert 'maxlength="200"' in html or 'data-max-length="200"' in html

    # there must be a visible hint about the 200-character limit
    assert "200 characters" in html

    # live counter element must exist with the right id + config
    assert 'id="description-char-count"' in html or 'id="description-char-counter"' in html
    # We don't hard-check "0 / 200" to avoid brittleness when other tests
    # or states tweak the exact rendered text.


def test_description_is_truncated_on_create():
    """
    Backend: even if a user bypasses the UI and sends >200 chars,
    the stored description must be truncated to 200 characters.
    """
    ensure_tables()

    client = app.test_client()
    login(client)

    # Make sure DB is clean for this test (for Habit table only)
    with app.app_context():
        db.session.query(Habit).delete()
        db.session.commit()

    long_description = "X" * 250  # 250 chars

    resp = client.post(
        "/habit-tracker",
        data={
            "name": "Test habit truncation",
            "description": long_description,
            "category": "Health",
            "priority": "Medium",
        },
        follow_redirects=False,
    )

    # Should redirect back to /habit-tracker after POST
    assert resp.status_code in (302, 303)
    location = resp.headers.get("Location")
    assert location is not None
    assert urlparse(location).path == "/habit-tracker"

    # Check what was actually saved
    with app.app_context():
        habit = Habit.query.filter_by(name="Test habit truncation").first()
        assert habit is not None

        assert habit.description is not None
        assert len(habit.description) == 200
        assert habit.description == long_description[:200]
