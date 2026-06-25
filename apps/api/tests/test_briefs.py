"""The agentic briefing flow — stage walk, adaptive follow-up, forks, directions.

Runs in local-dev mode against the stub LLM (deterministic), so the suite stays
hermetic — no Anthropic key, no network.
"""

from fastapi.testclient import TestClient


def _create(client: TestClient) -> dict:
    resp = client.post("/briefs")
    assert resp.status_code == 201
    return resp.json()


def test_create_returns_first_question(client: TestClient, local_dev: None, db: str) -> None:
    body = _create(client)
    assert body["status"] == "active"
    assert body["next_question"]["stage"] == "work"
    assert body["next_question"]["kind"] == "text"


def test_unknown_brief_is_404(client: TestClient, local_dev: None, db: str) -> None:
    assert client.get("/briefs/does-not-exist").status_code == 404


def test_feeling_calm_triggers_adaptive_followup(
    client: TestClient, local_dev: None, db: str
) -> None:
    brief = _create(client)
    bid = brief["id"]

    # Answer "the work".
    r = client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "text", "text": "A cafe rebrand"}})
    assert r.status_code == 200
    assert r.json()["next_question"]["stage"] == "feeling"

    # Answer "the feeling" including Calm -> the stub agent inserts a follow-up.
    r = client.post(
        f"/briefs/{bid}/answer",
        json={"value": {"kind": "chips", "chips": ["Calm", "Editorial"]}},
    )
    nq = r.json()["next_question"]
    assert nq["stage"] == "feeling"
    assert nq["adaptive"] is True
    assert nq["kind"] == "chips"


def test_full_flow_to_directions(client: TestClient, local_dev: None, db: str) -> None:
    bid = _create(client)["id"]

    client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "text", "text": "A cafe rebrand"}})
    # feeling without a follow-up trigger -> straight to references
    r = client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "chips", "chips": ["Premium"]}})
    assert r.json()["next_question"]["stage"] == "references"

    client.post(f"/briefs/{bid}/answer", json={"skip": True})  # references
    r = client.post(
        f"/briefs/{bid}/answer",
        json={"value": {"kind": "palette", "swatches": ["#C8643C"], "warmth": 0.7, "intensity": 0.6}},
    )
    assert r.json()["next_question"]["stage"] == "audience"

    r = client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "text", "text": "Local regulars"}})
    assert r.json()["next_question"] is None  # backbone exhausted

    # Answering again is a conflict.
    assert client.post(f"/briefs/{bid}/answer", json={"skip": True}).status_code == 409

    r = client.post(f"/briefs/{bid}/directions")
    body = r.json()
    assert body["status"] == "ready"
    assert len(body["content"]["directions"]) == 1  # no forks -> single direction


def test_fork_yields_multiple_directions(client: TestClient, local_dev: None, db: str) -> None:
    bid = _create(client)["id"]
    client.post(f"/briefs/{bid}/answer", json={"value": {"kind": "text", "text": "A cafe rebrand"}})
    # Fork the feeling into two divergent options.
    client.post(
        f"/briefs/{bid}/answer",
        json={
            "options": [
                {"kind": "chips", "chips": ["Premium"]},
                {"kind": "chips", "chips": ["Playful"]},
            ]
        },
    )
    client.post(f"/briefs/{bid}/answer", json={"skip": True})  # references
    client.post(f"/briefs/{bid}/answer", json={"skip": True})  # palette
    client.post(f"/briefs/{bid}/answer", json={"skip": True})  # audience

    body = client.post(f"/briefs/{bid}/directions").json()
    assert len(body["content"]["directions"]) == 2
