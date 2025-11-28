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
