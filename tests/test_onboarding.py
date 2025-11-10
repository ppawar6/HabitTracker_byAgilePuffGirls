"""Additional Tests for the Onboarding Feature"""


def test_tips_modal_dark_mode_classes(logged_in_client):
    """Test that tips modal has correct dark mode classes for accessibility."""
    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert "dark:text-purple-300" in html
    assert "dark:text-blue-300" in html
    assert "dark:text-green-300" in html
    assert "dark:text-yellow-300" in html
    assert "dark:from-purple-900/30" in html


def test_tips_hide_button_accessibility(logged_in_client):
    """Test that tips hide button is accessible."""
    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert "aria-label" in html or "title" in html
    assert 'type="button"' in html
    assert 'onclick="closeTipsModal()"' in html


def test_tips_persistent_across_sessions(logged_in_client, app):
    """Test that tips preference persists across sessions."""
    # First session: disable tips
    response1 = logged_in_client.post("/tips/disable", follow_redirects=True)
    assert response1.status_code == 200

    # Clear session
    logged_in_client.get("/logout")

    # Second session: check tips are still disabled
    with logged_in_client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"

    response2 = logged_in_client.get("/habit-tracker")
    html = response2.data.decode("utf-8")
    assert (
        "document.addEventListener('DOMContentLoaded', function() { showTipsModal(); })" not in html
    )


def test_tips_modal_keyboard_navigation(logged_in_client):
    """Test that tips modal can be navigated with keyboard."""
    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    assert 'tabindex="0"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html


def test_tips_content_accessibility(logged_in_client):
    """Test that tips content follows accessibility guidelines."""
    response = logged_in_client.get("/habit-tracker")
    html = response.data.decode("utf-8")

    # Check for ARIA labels and proper heading hierarchy
    assert 'role="dialog"' in html
    assert "aria-labelledby" in html
    assert 'class="text-2xl"' in html  # Proper text sizing
    assert 'class="sr-only"' in html  # Screen reader text
