"""The four error cases must all return the same JSON shape."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_handlers import register_error_handlers
from app.core.errors import NotFoundError, ValidationFailure


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/missing")
    def missing():
        raise NotFoundError("Pump PUMP-999 not found")

    @app.get("/broken-rule")
    def broken_rule():
        raise ValidationFailure("mode_id is required")

    @app.get("/number")
    def number(n: int):
        return {"n": n}

    return TestClient(app)


def test_not_found_error_gives_404_in_standard_format():
    response = _client().get("/missing")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Pump PUMP-999 not found", "details": None}
    }


def test_validation_failure_gives_422_in_standard_format():
    response = _client().get("/broken-rule")
    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "VALIDATION_FAILED", "message": "mode_id is required", "details": None}
    }


def test_bad_request_input_gives_422_in_standard_format():
    response = _client().get("/number", params={"n": "abc"})
    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert isinstance(body["error"]["details"], list)


def test_unknown_route_gives_404_in_standard_format():
    response = _client().get("/does-not-exist")
    body = response.json()
    assert response.status_code == 404
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["details"] is None