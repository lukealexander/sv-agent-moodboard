"""The example `/items` resource — response shape and routing.

Auth *enforcement* for these routes lives in ``test_auth.py``; here we run in
local-dev mode and assert the contract the frontend dashboard relies on.
"""

from fastapi.testclient import TestClient


def test_list_items_returns_a_list_of_items(
    client: TestClient, local_dev: None
) -> None:
    response = client.get("/items")
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    assert body, "expected at least one example item"

    item = body[0]
    assert set(item) == {"id", "name", "description"}
    assert isinstance(item["id"], int)
    assert isinstance(item["name"], str)


def test_get_item_echoes_the_requested_id(
    client: TestClient, local_dev: None
) -> None:
    response = client.get("/items/42")
    assert response.status_code == 200
    assert response.json()["id"] == 42


def test_get_item_rejects_non_integer_id(
    client: TestClient, local_dev: None
) -> None:
    """Path is typed `int`, so a non-numeric id is a 422 validation error."""
    response = client.get("/items/not-a-number")
    assert response.status_code == 422
