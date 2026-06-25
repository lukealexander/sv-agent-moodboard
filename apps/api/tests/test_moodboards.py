"""Moodboard generation — inline brief, saved brief, SSE, auth, and 404s.

Local-dev mode uses the stub LLM + stub image renderer, so generation runs end to end
(no Anthropic/Replicate keys). FastAPI background tasks complete before the POST
returns under TestClient, so the result is terminal by the time we assert.
"""

from fastapi.testclient import TestClient


def test_generate_requires_exactly_one_source(
    client: TestClient, local_dev: None, db: str
) -> None:
    assert client.post("/moodboards", json={}).status_code == 422
    both = {"brief_id": "x", "brief": {"prompt": "y"}}
    assert client.post("/moodboards", json=both).status_code == 422


def test_generate_from_inline_brief(client: TestClient, local_dev: None, db: str) -> None:
    resp = client.post(
        "/moodboards",
        json={"brief": {"prompt": "A neighbourhood cafe rebrand", "directions": ["Warm", "Cool"]}},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert len(body["moodboards"]) == 2
    request_id = body["id"]

    req = client.get(f"/moodboards/requests/{request_id}").json()
    assert req["status"] == "done"
    assert all(m["status"] == "done" for m in req["moodboards"])

    mb_id = req["moodboards"][0]["id"]
    mb = client.get(f"/moodboards/{mb_id}").json()
    assert mb["status"] == "done"
    assert mb["palette"]
    assert len(mb["images"]) == 5
    assert mb["concept"]["title"]
    assert mb["html_url"] == f"/moodboards/{mb_id}/html"

    html = client.get(f"/moodboards/{mb_id}/html")
    assert html.status_code == 200
    assert "text/html" in html.headers["content-type"]
    assert "moodboard" in html.text.lower()

    image = client.get(f"/moodboards/{mb_id}/image/0")
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/")


def test_generate_from_saved_brief(client: TestClient, local_dev: None, db: str) -> None:
    bid = client.post("/briefs").json()["id"]
    client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "text", "text": "A cafe rebrand"}})
    client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "chips", "chips": ["Premium"]}})
    client.post(f"/briefs/{bid}/answer", json={"skip": True})
    client.post(f"/briefs/{bid}/answer", json={"skip": True})
    client.post(f"/briefs/{bid}/answer", json={"skip": True})
    client.post(f"/briefs/{bid}/directions")

    resp = client.post("/moodboards", json={"brief_id": bid})
    assert resp.status_code == 202
    request_id = resp.json()["id"]
    req = client.get(f"/moodboards/requests/{request_id}").json()
    assert req["status"] == "done"
    assert len(req["moodboards"]) == 1


def test_request_events_stream_to_done(client: TestClient, local_dev: None, db: str) -> None:
    request_id = client.post("/moodboards", json={"brief": {"prompt": "A cafe"}}).json()["id"]
    saw_done = False
    with client.stream("GET", f"/moodboards/requests/{request_id}/events") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        for line in resp.iter_lines():
            if line and "done" in line:
                saw_done = True
                break
    assert saw_done


def test_unknown_ids_are_404(client: TestClient, local_dev: None, db: str) -> None:
    assert client.get("/moodboards/requests/nope").status_code == 404
    assert client.get("/moodboards/nope").status_code == 404
    assert client.get("/moodboards/nope/html").status_code == 404


def test_endpoints_require_auth(client: TestClient, production: None) -> None:
    # Router-level require_auth rejects before any DB access, so no `db` fixture needed.
    assert client.post("/briefs").status_code == 401
    assert client.post("/moodboards", json={"brief": {"prompt": "x"}}).status_code == 401
