from flask import Blueprint, jsonify, request, session

from extensions import db
from models import UserPreferences

theme_bp = Blueprint("theme", __name__, url_prefix="/theme")


@theme_bp.route("/settings")
def theme_settings():
    """Get current theme settings."""
    # Try to get theme from session first
    theme_preference = session.get("theme")
    print(f"[DEBUG] /settings - session['theme']: {theme_preference}")
    if not theme_preference:
        # If authenticated, try to get from database
        if session.get("authenticated"):
            email = session.get("email")
            preferences = UserPreferences.query.filter_by(id=email).first()
            print(f"[DEBUG] /settings - DB theme for {email}: {getattr(preferences, 'theme', None)}")
            if preferences:
                theme_preference = preferences.theme
                # Cache in session
                session["theme"] = theme_preference
    print(f"[DEBUG] /settings - returning: {theme_preference or 'light'}")
    return jsonify({"theme": theme_preference or "light"})


@theme_bp.route("/toggle", methods=["POST"])
def toggle_theme():
    """Toggle theme preference."""
    data = request.get_json()
    theme = data.get("theme")
    print(f"[DEBUG] /toggle - requested theme: {theme}")
    if theme not in ["light", "dark"]:
        return jsonify({"error": "Invalid theme value"}), 400
    # Always store in session for immediate effect
    session["theme"] = theme
    print(f"[DEBUG] /toggle - session['theme'] set to: {theme}")
    # If user is authenticated, store in database
    if session.get("authenticated"):
        email = session.get("email")
        preferences = UserPreferences.query.filter_by(id=email).first()
        if preferences:
            preferences.theme = theme
        else:
            preferences = UserPreferences(id=email, theme=theme)
            db.session.add(preferences)
        db.session.commit()
        print(f"[DEBUG] /toggle - DB theme for {email} set to: {theme}")
    return jsonify({"success": True, "theme": theme})
