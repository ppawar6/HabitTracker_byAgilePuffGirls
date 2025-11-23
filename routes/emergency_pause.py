"""
Emergency Pause routes for Break Glass feature
"""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, redirect, request, session, url_for

from extensions import db
from models import EmergencyPause, Habit

emergency_bp = Blueprint('emergency', __name__, url_prefix='/habit-tracker/emergency')


@emergency_bp.route('/pause', methods=['POST'])
def activate_pause():
    """Activate emergency pause for all user habits"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session.get('user_id', 0)

    # Get form data
    reason = request.form.get('reason', '')
    duration_days = int(request.form.get('duration_days', 7))

    # Check if user already has an active pause
    existing_pause = EmergencyPause.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()

    if existing_pause:
        return jsonify({
            'error': 'Emergency pause already active',
            'debug_info': {
                'pause_id': existing_pause.id,
                'started_at': existing_pause.started_at.isoformat() if existing_pause.started_at else None,
                'ends_at': existing_pause.ends_at.isoformat() if existing_pause.ends_at else None,
                'is_active': existing_pause.is_active
            }
        }), 400

    # Calculate end date
    starts_at = datetime.now(timezone.utc)
    ends_at = starts_at + timedelta(days=duration_days)

    # Create emergency pause record
    emergency_pause = EmergencyPause(
        user_id=user_id,
        is_active=True,
        reason=reason,
        duration_days=duration_days,
        started_at=starts_at,
        ends_at=ends_at
    )

    db.session.add(emergency_pause)

    # Pause all active (non-paused, non-archived) habits for this user
    active_habits = Habit.query.filter_by(
        user_id=user_id,
        is_paused=False,
        is_archived=False
    ).all()

    now = datetime.now(timezone.utc)
    for habit in active_habits:
        habit.is_paused = True
        habit.paused_at = now

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Emergency pause activated for {duration_days} days. All {len(active_habits)} habits paused.',
        'ends_at': ends_at.isoformat(),
        'habits_paused': len(active_habits)
    })


@emergency_bp.route('/resume', methods=['POST'])
def resume():
    """Resume from emergency pause"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session.get('user_id', 0)
    print(f"\n[DEBUG RESUME] Called for user_id: {user_id}")

    # Find active pause
    active_pause = EmergencyPause.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()

    if not active_pause:
        print(f"[DEBUG RESUME] No active pause found for user_id: {user_id}")
        all_pauses = EmergencyPause.query.filter_by(user_id=user_id).all()
        print(f"[DEBUG RESUME] All pauses for user: {[(p.id, p.is_active, p.ended_at) for p in all_pauses]}")
        return jsonify({'error': 'No active emergency pause found'}), 404

    print(f"[DEBUG RESUME] Found active pause - ID: {active_pause.id}, is_active: {active_pause.is_active}")

    # Mark pause as inactive
    now = datetime.now(timezone.utc)
    print(f"[DEBUG RESUME] Setting is_active=False and ended_at={now}")
    active_pause.is_active = False
    active_pause.ended_at = now

    print(f"[DEBUG RESUME] After assignment - is_active: {active_pause.is_active}, ended_at: {active_pause.ended_at}")

    # Resume all paused habits that were paused around the same time as emergency pause started
    # We'll resume habits that were paused within 1 minute of the emergency pause start
    paused_habits = Habit.query.filter_by(
        user_id=user_id,
        is_paused=True
    ).all()

    resumed_count = 0
    for habit in paused_habits:
        # Check if habit was paused around the time of emergency pause activation
        if habit.paused_at:
            time_diff = abs((habit.paused_at.replace(tzinfo=timezone.utc) if habit.paused_at.tzinfo is None else habit.paused_at) -
                          (active_pause.started_at.replace(tzinfo=timezone.utc) if active_pause.started_at.tzinfo is None else active_pause.started_at))
            # If paused within 1 minute of emergency pause, resume it
            if time_diff.total_seconds() < 60:
                habit.is_paused = False
                habit.paused_at = None
                resumed_count += 1

    print(f"[DEBUG RESUME] About to commit. Resumed {resumed_count} habits")
    db.session.commit()
    print(f"[DEBUG RESUME] Commit completed")

    # Verify the change was persisted
    verification = db.session.get(EmergencyPause, active_pause.id)
    print(f"[DEBUG RESUME] POST-COMMIT Verification - ID: {verification.id}, is_active: {verification.is_active}, ended_at: {verification.ended_at}")

    return jsonify({
        'success': True,
        'message': f'Emergency pause ended. Welcome back! {resumed_count} habits resumed.',
        'habits_resumed': resumed_count
    })


@emergency_bp.route('/status', methods=['GET'])
def get_status():
    """Get current emergency pause status"""
    if not session.get('authenticated'):
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session.get('user_id', 0)

    # Find active pause
    active_pause = EmergencyPause.query.filter_by(
        user_id=user_id,
        is_active=True
    ).first()

    if not active_pause:
        return jsonify({
            'is_paused': False
        })

    # Check if pause should auto-expire
    now = datetime.now(timezone.utc)
    # Ensure ends_at is timezone-aware for comparison
    ends_at_aware = active_pause.ends_at.replace(tzinfo=timezone.utc) if active_pause.ends_at and active_pause.ends_at.tzinfo is None else active_pause.ends_at
    if ends_at_aware and now >= ends_at_aware:
        # Auto-resume
        active_pause.is_active = False
        active_pause.ended_at = now
        db.session.commit()

        return jsonify({
            'is_paused': False,
            'auto_resumed': True
        })

    return jsonify({
        'is_paused': True,
        'reason': active_pause.reason,
        'duration_days': active_pause.duration_days,
        'started_at': active_pause.started_at.isoformat(),
        'ends_at': active_pause.ends_at.isoformat() if active_pause.ends_at else None,
        'days_remaining': (ends_at_aware - now).days if ends_at_aware else None
    })
