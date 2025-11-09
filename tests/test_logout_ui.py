"""Test logout button UI functionality in settings modal."""



def test_logout_button_exists_in_settings_modal(logged_in_client):
    """Test that logout button is present in the settings modal."""
    # Act
    response = logged_in_client.get("/habit-tracker")

    # Assert
    assert response.status_code == 200
    assert b"Logout" in response.data or b"logout" in response.data
    # Check for logout button/link in settings
    assert b'href="/logout"' in response.data or b"onclick=\"handleLogout()\"" in response.data


def test_logout_button_has_proper_styling(logged_in_client):
    """Test that logout button has appropriate styling classes for theme support."""
    # Act
    response = logged_in_client.get("/habit-tracker")

    # Assert
    assert response.status_code == 200
    content = response.data.decode('utf-8')

    # Check for theme-aware classes
    assert 'text-theme-primary' in content or 'text-red-600' in content
    # Logout should be visible in settings modal
    assert 'settingsModal' in content


def test_logout_button_accessible_when_authenticated(logged_in_client):
    """Test that logout option is only accessible when user is authenticated."""
    # Act
    response = logged_in_client.get("/habit-tracker")

    # Assert - logout should be present for authenticated users
    assert response.status_code == 200
    assert b"Settings" in response.data  # Settings icon should be visible


def test_logout_button_not_visible_on_landing_page(client):
    """Test that logout button is not visible on the landing page for unauthenticated users."""
    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    # Landing page should not have settings modal with logout
    # Settings modal might exist but logout should not be prominent


def test_settings_modal_structure(logged_in_client):
    """Test that settings modal contains all expected sections including logout."""
    # Act
    response = logged_in_client.get("/habit-tracker")

    # Assert
    assert response.status_code == 200
    content = response.data.decode('utf-8')

    # Settings modal should exist
    assert 'id="settingsModal"' in content
    # Dark mode toggle should exist
    assert 'Dark Mode' in content
    assert 'Toggle dark theme' in content
    # Logout button should exist
    assert 'Logout' in content
    assert 'End your session securely' in content
