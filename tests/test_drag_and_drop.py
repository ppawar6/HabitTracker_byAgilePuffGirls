from app import Habit, app, db


def login(test_client):
    with test_client.session_transaction() as sess:
        sess["authenticated"] = True
        sess["email"] = "test@example.com"


def _reset_habits():
    with app.app_context():
        db.session.query(Habit).delete()
        db.session.commit()


def _create_two_habits():
    with app.app_context():
        h1 = Habit(name="Drag Habit 1", position=1)
        h2 = Habit(name="Drag Habit 2", position=2)
        db.session.add_all([h1, h2])
        db.session.commit()
        return h1.id, h2.id


def test_habit_list_container_has_id_for_drag_and_drop():
    """
    UI: The active habits list should have a stable container ID
    so JS can attach drag-and-drop listeners.
    """
    _reset_habits()
    _create_two_habits()

    client = app.test_client()
    login(client)

    resp = client.get("/habit-tracker")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")

    # Container for active habits should exist
    assert 'id="habit-list"' in html


def test_each_habit_card_is_draggable_and_has_data_id():
    """
    UI: Each habit card must:
      - have data-habit-id="<id>"
      - be draggable="true"
    so the frontend can build an ordered list and send it to /habit-tracker/reorder.
    """
    _reset_habits()
    id1, id2 = _create_two_habits()

    client = app.test_client()
    login(client)

    resp = client.get("/habit-tracker")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")

    # Draggable attribute somewhere in the habit list
    assert 'draggable="true"' in html

    # Each habit's data-habit-id should be present
    assert f'data-habit-id="{id1}"' in html
    assert f'data-habit-id="{id2}"' in html


def test_drag_and_drop_js_calls_reorder_endpoint():
    """
    UI: The template should include JS that calls /habit-tracker/reorder
    (we just check the string is present in the HTML).
    """
    _reset_habits()
    _create_two_habits()

    client = app.test_client()
    login(client)

    resp = client.get("/habit-tracker")
    assert resp.status_code == 200

    html = resp.data.decode("utf-8")

    # The JS should send a fetch to the reorder endpoint
    assert 'fetch("/habit-tracker/reorder"' in html or "fetch('/habit-tracker/reorder'" in html
