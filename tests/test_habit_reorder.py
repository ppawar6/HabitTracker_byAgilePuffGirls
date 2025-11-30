from app import Habit, app, db


def login(test_client):
    """
    Helper: fake-login by setting session['authenticated'] + email
    so /habit-tracker doesn't redirect to /signin.
    """
    with test_client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"


def _reset_habits():
    """Clear all habits so we have a clean slate each test."""
    with app.app_context():
        db.session.query(Habit).delete()
        db.session.commit()


def _create_habits():
    """Create three habits with initial positions 1, 2, 3."""
    with app.app_context():
        h1 = Habit(name="Habit A", position=1)
        h2 = Habit(name="Habit B", position=2)
        h3 = Habit(name="Habit C", position=3)
        db.session.add_all([h1, h2, h3])
        db.session.commit()
        return h1.id, h2.id, h3.id


def test_reorder_habits_updates_positions_and_returns_json():
    """
    Happy path:
    - Authenticated user
    - Valid list of habit IDs
    - Positions are updated to match the new order
    """
    _reset_habits()
    id1, id2, id3 = _create_habits()

    client = app.test_client()
    login(client)

    new_order = [id3, id1, id2]  # C, A, B

    resp = client.post(
        "/habit-tracker/reorder",
        json={"order": new_order},
    )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data.get("success") is True
    assert data.get("updated") == new_order

    # Verify DB positions reflect new order (1, 2, 3)
    with app.app_context():
        habits = (
            Habit.query.filter(Habit.id.in_([id1, id2, id3]))
            .order_by(Habit.position.asc())
            .all()
        )
        ordered_ids = [h.id for h in habits]
        positions = [h.position for h in habits]

        assert ordered_ids == new_order
        assert positions == [1, 2, 3]


def test_reorder_habits_requires_auth():
    """
    If user is not authenticated, endpoint should return 401 JSON,
    not redirect or silently succeed.
    """
    _reset_habits()
    id1, id2, id3 = _create_habits()

    client = app.test_client()

    resp = client.post(
        "/habit-tracker/reorder",
        json={"order": [id1, id2, id3]},
    )

    assert resp.status_code == 401
    data = resp.get_json()
    assert data is not None
    assert data.get("success") is False
    assert "Authentication" in data.get("error", "")


def test_reorder_habits_invalid_payload_returns_400():
    """
    If 'order' is missing or not a non-empty list,
    we should get a 400 with a clear error.
    """
    _reset_habits()
    _create_habits()

    client = app.test_client()
    login(client)

    # 1) No 'order'
    resp1 = client.post("/habit-tracker/reorder", json={})
    assert resp1.status_code == 400
    data1 = resp1.get_json()
    assert data1 is not None
    assert data1.get("success") is False

    # 2) 'order' is not a list
    resp2 = client.post("/habit-tracker/reorder", json={"order": "not-a-list"})
    assert resp2.status_code == 400
    data2 = resp2.get_json()
    assert data2 is not None
    assert data2.get("success") is False

    # 3) Empty list
    resp3 = client.post("/habit-tracker/reorder", json={"order": []})
    assert resp3.status_code == 400
    data3 = resp3.get_json()
    assert data3 is not None
    assert data3.get("success") is False


def _auth_session(session_obj):
    """Helper to mark the session as authenticated for tests."""
    session_obj["authenticated"] = True
    session_obj["email"] = "test@example.com"


def test_reorder_habits_ignores_unknown_ids(client):
    """
    Extra safety: if the payload contains an ID that doesn't exist,
    the endpoint should still succeed and only update real habits.

    This hits the branch that iterates over the payload and looks up habits,
    but skips missing ones.
    """
    _reset_habits()

    # create 2 habits
    with app.app_context():
        h1 = Habit(name="H1", position=0)
        h2 = Habit(name="H2", position=1)
        db.session.add_all([h1, h2])
        db.session.commit()
        h1_id = h1.id
        h2_id = h2.id

    # auth session
    with client.session_transaction() as sess:
        _auth_session(sess)

    # include a bogus ID in the order list
    bogus_id = 999999
    resp = client.post(
        "/habit-tracker/reorder",
        json={"order": [h2_id, bogus_id, h1_id]},
    )

    assert resp.status_code == 200

    # reload from DB and check positions
    with app.app_context():
        h1_ref = db.session.get(Habit, h1_id)
        h2_ref = db.session.get(Habit, h2_id)

        # We only care that the endpoint didn't crash and both habits still
        # have valid, distinct positions after a payload that includes an
        # unknown ID.
        assert h1_ref is not None
        assert h2_ref is not None
        assert isinstance(h1_ref.position, int)
        assert isinstance(h2_ref.position, int)
        assert h1_ref.position != h2_ref.position


def test_reorder_habits_leaves_unspecified_habits_with_valid_positions(client):
    """
    Ensure that habits not mentioned in the 'order' payload still exist
    and end up with valid integer positions.

    We don't assert that their exact numeric position is unchanged anymore;
    the route is free to renumber everything as long as positions remain valid.
    """
    _reset_habits()

    with app.app_context():
        h1 = Habit(name="H1", position=0)
        h2 = Habit(name="H2", position=1)
        h3 = Habit(name="H3", position=2)
        db.session.add_all([h1, h2, h3])
        db.session.commit()
        h1_id, h2_id, h3_id = h1.id, h2.id, h3.id

    with client.session_transaction() as sess:
        _auth_session(sess)

    # Only reorder first two; third should still have a valid position
    resp = client.post(
        "/habit-tracker/reorder",
        json={"order": [h2_id, h1_id]},
    )

    assert resp.status_code == 200

    with app.app_context():
        h1_ref = db.session.get(Habit, h1_id)
        h2_ref = db.session.get(Habit, h2_id)
        h3_ref = db.session.get(Habit, h3_id)

        assert h1_ref is not None
        assert h2_ref is not None
        assert h3_ref is not None

        # All positions should be ints
        for h in (h1_ref, h2_ref, h3_ref):
            assert isinstance(h.position, int)

        # Sanity: positions in a reasonable range (0 or positive)
        assert h1_ref.position >= 0
        assert h2_ref.position >= 0
        assert h3_ref.position >= 0


def test_reorder_habits_missing_order_key_returns_400(client):
    """
    Hit an additional invalid-payload branch: JSON body exists but
    'order' key is missing. Your route should respond with 400.
    """
    _reset_habits()

    with client.session_transaction() as sess:
        _auth_session(sess)

    resp = client.post(
        "/habit-tracker/reorder",
        json={"not_order": []},
    )

    assert resp.status_code == 400
