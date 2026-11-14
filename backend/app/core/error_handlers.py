"""Turns errors into one JSON format: {"error": {"code", "message", "details"}}."""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import NotFoundError, ValidationFailure


def _body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


async def _not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=_body("NOT_FOUND", str(exc)))


async def _validation_failure(request: Request, exc: ValidationFailure) -> JSONResponse:
    return JSONResponse(status_code=422, content=_body("VALIDATION_FAILED", str(exc)))


async def _request_invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=422,
        content=_body("VALIDATION_FAILED", "Request validation failed", details),
    )


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return JSONResponse(
        status_code=exc.status_code, content=_body(code, str(exc.detail))
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(ValidationFailure, _validation_failure)
    app.add_exception_handler(RequestValidationError, _request_invalid)
    app.add_exception_handler(StarletteHTTPException, _http_error)