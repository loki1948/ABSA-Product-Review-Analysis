from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import requires_models

REVIEW = "The camera is excellent but the battery life is poor."


def test_analyze_returns_aspect_sentiment_map(client: TestClient) -> None:
    response = client.post("/api/analyze", json={"review": REVIEW})
    assert response.status_code == 200
    body = response.json()

    assert set(body) == {"id", "review", "overall_sentiment", "overall_confidence", "aspects", "created_at"}
    assert body["id"] == 1 and body["review"] == REVIEW
    assert body["created_at"].endswith("+00:00")
    assert [(a["aspect"], a["sentiment"]) for a in body["aspects"]] == [
        ("camera", "positive"),
        ("battery life", "negative"),
    ]
    first = body["aspects"][0]
    assert set(first) == {"aspect", "sentiment", "confidence", "context", "start", "end"}
    assert body["review"][first["start"] : first["end"]] == "camera"
    assert first["context"] == "The camera is excellent"


def test_analyze_without_saving(client: TestClient) -> None:
    body = client.post("/api/analyze", json={"review": REVIEW, "save": False}).json()
    assert body["id"] is None and body["created_at"] is None
    assert client.get("/api/reviews").json()["total"] == 0


def test_analyze_rejects_bad_input(client: TestClient) -> None:
    assert client.post("/api/analyze", json={"review": ""}).status_code == 422
    assert client.post("/api/analyze", json={"review": "   "}).status_code == 422
    assert client.post("/api/analyze", json={"review": "x" * 5001}).status_code == 422
    assert client.post("/api/analyze", json={}).status_code == 422


def test_analyze_batch_keeps_request_order_and_saves(client: TestClient) -> None:
    reviews = ["The camera is great.", "The screen is bad."]
    response = client.post("/api/analyze/batch", json={"reviews": reviews})
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 2
    assert [item["review"] for item in body["items"]] == reviews
    assert [item["id"] for item in body["items"]] == [1, 2]
    assert body["items"][1]["aspects"][0]["sentiment"] == "negative"
    assert client.get("/api/reviews").json()["total"] == 2


def test_analyze_batch_without_saving(client: TestClient) -> None:
    body = client.post("/api/analyze/batch", json={"reviews": [REVIEW], "save": False}).json()
    assert body["items"][0]["id"] is None
    assert client.get("/api/reviews").json()["total"] == 0


def test_analyze_batch_rejects_bad_input(client: TestClient) -> None:
    assert client.post("/api/analyze/batch", json={"reviews": []}).status_code == 422
    assert client.post("/api/analyze/batch", json={"reviews": ["ok", "  "]}).status_code == 422
    assert client.post("/api/analyze/batch", json={"reviews": ["x" * 5001]}).status_code == 422
    assert client.post("/api/analyze/batch", json={"reviews": ["ok"] * 51}).status_code == 422
    assert client.get("/api/reviews").json()["total"] == 0


def test_review_history_is_newest_first_and_paginated(client: TestClient) -> None:
    for text in ("The camera is great.", "The screen is bad.", "Nice display."):
        client.post("/api/analyze", json={"review": text})

    page = client.get("/api/reviews", params={"limit": 2}).json()
    assert (page["total"], page["limit"], page["offset"]) == (3, 2, 0)
    assert [item["review"] for item in page["items"]] == ["Nice display.", "The screen is bad."]
    assert page["items"][0]["aspects"][0]["aspect"] == "display"

    rest = client.get("/api/reviews", params={"limit": 2, "offset": 2}).json()
    assert [item["review"] for item in rest["items"]] == ["The camera is great."]

    negative = client.get("/api/reviews", params={"sentiment": "negative"}).json()
    assert negative["total"] == 1 and negative["items"][0]["review"] == "The screen is bad."


def test_get_and_delete_review(client: TestClient) -> None:
    review_id = client.post("/api/analyze", json={"review": REVIEW}).json()["id"]
    assert client.get(f"/api/reviews/{review_id}").json()["review"] == REVIEW

    assert client.delete(f"/api/reviews/{review_id}").status_code == 204
    assert client.get(f"/api/reviews/{review_id}").status_code == 404
    assert client.delete(f"/api/reviews/{review_id}").status_code == 404
    assert client.get("/api/statistics").json()["total_aspects"] == 0


def test_statistics_aggregate_aspects(client: TestClient) -> None:
    empty = client.get("/api/statistics").json()
    assert empty["total_reviews"] == 0 and empty["top_aspects"] == []
    assert empty["overall_sentiment_distribution"] == {"positive": 0, "negative": 0, "neutral": 0}

    for text in ("The Battery is terrible.", "Great battery.", "The camera is poor.", "Great camera, great battery."):
        client.post("/api/analyze", json={"review": text})

    stats = client.get("/api/statistics").json()
    assert stats["total_reviews"] == 4 and stats["total_aspects"] == 5
    assert stats["aspect_sentiment_distribution"] == {"positive": 3, "negative": 2, "neutral": 0}
    assert stats["top_aspects"] == [
        {"aspect": "battery", "total": 3, "positive": 2, "negative": 1, "neutral": 0},
        {"aspect": "camera", "total": 2, "positive": 1, "negative": 1, "neutral": 0},
    ]
    assert len(client.get("/api/statistics", params={"top_n": 1}).json()["top_aspects"]) == 1


def test_health_reports_missing_models(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["models_loaded"] is False and body["database"] is True
    assert "ABSA_LOAD_MODELS" in body["detail"]


def test_analyze_returns_503_when_models_are_not_loaded(client: TestClient) -> None:
    client.app.dependency_overrides.clear()  # drop the stub: no pipeline is loaded
    response = client.post("/api/analyze", json={"review": REVIEW})
    assert response.status_code == 503
    assert "detail" in response.json()


def test_cors_allows_the_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/api/analyze",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.model
@requires_models
def test_analyze_endpoint_with_the_deployed_models(real_client: TestClient) -> None:
    """The whole path a user takes: HTTP request -> real models -> database -> response."""
    review = "The screen is gorgeous and the keyboard feels great, but the battery life is terrible."
    response = real_client.post("/api/analyze", json={"review": review})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] is not None
    assert body["overall_sentiment"] in {"positive", "negative", "neutral"}
    assert body["aspects"], "no aspects extracted"
    for aspect in body["aspects"]:
        assert body["review"][aspect["start"] : aspect["end"]] == aspect["aspect"]
        assert aspect["sentiment"] in {"positive", "negative", "neutral"}
        assert 0.0 <= aspect["confidence"] <= 1.0
    assert real_client.get(f"/api/reviews/{body['id']}").json() == body
    assert real_client.get("/api/health").json()["status"] == "ok"


@pytest.mark.model
@requires_models
def test_analyze_endpoint_handles_a_restaurant_review(real_client: TestClient) -> None:
    response = real_client.post(
        "/api/analyze",
        json={"review": "The pasta was delicious but the service was slow.", "save": False},
    )
    assert response.status_code == 200
    assert response.json()["aspects"], "no aspects extracted from a restaurant review"
