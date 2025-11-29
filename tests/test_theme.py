"""Test theme functionality."""

from models import UserPreferences


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
        pref = UserPreferences.query.filter_by(id="test@example.com").first()
        assert pref is not None
        assert pref.theme == "dark"


def test_dark_mode_category_colors_not_overridden(logged_in_client, app):
    """Test that habit cards preserve category colors in dark mode."""
    from extensions import db
    from models import Habit

    # Create a habit with a specific category
    with app.app_context():
        habit = Habit(name="Morning Run", category="Fitness", description="Run 5km")
        db.session.add(habit)
        db.session.commit()

    # Get the habit tracker page
    response = logged_in_client.get("/habit-tracker")
    assert response.status_code == 200

    html = response.data.decode()

    # Verify dark mode CSS does NOT override card background colors with generic dark theme colors
    # The old broken CSS had: [data-theme="dark"] .habit-card { background-color: var(--bg-primary) !important; }
    # We should NOT find this pattern
    assert '[data-theme="dark"] .habit-card {' not in html or 'background-color: var(--bg-primary) !important' not in html

    # Verify the category color is applied via inline styles (from cat_styles filter)
    # Fitness category should have card color #F7FEE7
    assert 'background-color: #F7FEE7' in html or 'background-color:#F7FEE7' in html


def test_dark_mode_text_readability_preserved(logged_in_client):
    """Test that text remains readable in dark mode on colored habit cards."""
    response = logged_in_client.get("/habit-tracker")
    assert response.status_code == 200

    html = response.data.decode()

    # Verify dark mode text color adjustments are present
    # These ensure text is readable on light-colored category backgrounds
    assert '[data-theme="dark"] .habit-card .text-gray-900' in html
    assert '[data-theme="dark"] .habit-card .habit-name-display' in html
    assert 'color: #111827 !important' in html


def test_category_colors_applied_with_inline_styles(logged_in_client, app):
    """Test that category colors are applied via inline styles, not CSS overrides."""
    from extensions import db
    from models import Habit

    # Create habits with different categories
    with app.app_context():
        habits = [
            Habit(name="Meditation", category="Health"),
            Habit(name="Workout", category="Fitness"),
            Habit(name="Reading", category="Study"),
        ]
        db.session.add_all(habits)
        db.session.commit()

    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode()

    # Verify that each category has its specific background color applied
    # Health: #FFF1F2
    assert 'background-color: #FFF1F2' in html or 'background-color:#FFF1F2' in html

    # Fitness: #F7FEE7
    assert 'background-color: #F7FEE7' in html or 'background-color:#F7FEE7' in html

    # Study: #EFF6FF
    assert 'background-color: #EFF6FF' in html or 'background-color:#EFF6FF' in html


def test_dark_mode_does_not_break_category_pills(logged_in_client, app):
    """Test that category pills maintain their colors in dark mode."""
    from extensions import db
    from models import Habit

    # Create a habit with a category
    with app.app_context():
        habit = Habit(name="Yoga", category="Health")
        db.session.add(habit)
        db.session.commit()

    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode()

    # Category pills use CSS variables set by cat_styles filter
    # Verify the CSS variables are defined
    assert '--cat-pill-bg:' in html or '--cat-pill-bg :' in html
    assert '--cat-pill-text:' in html or '--cat-pill-text :' in html
