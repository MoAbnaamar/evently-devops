from uuid import uuid4

from fastapi.testclient import TestClient


# Test health endpoint status and payload structure
def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "environment" in body


# Test form creation with valid data
def test_create_form_returns_created_form(client: TestClient) -> None:
    response = client.post("/forms", json={"title": "Friday borrel"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Friday borrel"
    assert body["id"]
    assert body["created_at"]


# Test creating and subsequently listing submissions for a form
def test_submission_roundtrip(client: TestClient) -> None:
    form_id = client.post("/forms", json={"title": "Workshop"}).json()["id"]

    created = client.post(
        f"/forms/{form_id}/submissions",
        json={"data": {"name": "Jane", "attending": True}},
    )
    assert created.status_code == 201

    listed = client.get(f"/forms/{form_id}/submissions")
    assert listed.status_code == 200
    submissions = listed.json()
    assert len(submissions) == 1
    assert submissions[0]["data"]["name"] == "Jane"
    assert submissions[0]["form_id"] == form_id


# Test submission creation attempt on a non-existent form returns 404
def test_submission_to_unknown_form_returns_404(client: TestClient) -> None:
    response = client.post(f"/forms/{uuid4()}/submissions", json={"data": {}})

    assert response.status_code == 404


# Test listing submissions for a non-existent form returns 404
def test_listing_submissions_of_unknown_form_returns_404(client: TestClient) -> None:
    response = client.get(f"/forms/{uuid4()}/submissions")

    assert response.status_code == 404


# Test form creation with empty title fails payload validation
def test_empty_title_is_rejected(client: TestClient) -> None:
    response = client.post("/forms", json={"title": ""})

    assert response.status_code == 422


# Test request using invalid UUID format fails URL validation
def test_malformed_form_id_is_rejected(client: TestClient) -> None:
    response = client.get("/forms/not-a-uuid/submissions")

    assert response.status_code == 422