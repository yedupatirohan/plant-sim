"""Errors raised by services. Routes will turn these into HTTP codes."""


class NotFoundError(Exception):
    """A requested record does not exist (becomes HTTP 404)."""


class ValidationFailure(Exception):
    """A request is well-formed but breaks a business rule (becomes HTTP 422)."""