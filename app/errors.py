from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    code = "bad_request"
    status = 400

    def __init__(self, message: str | None = None):
        self.message = message or self.code
        super().__init__(self.message)


class NotFound(AppError):
    code = "not_found"
    status = 404


class Conflict(AppError):
    code = "conflict"
    status = 409


class Gone(AppError):
    code = "expired"
    status = 410


class Unauthorized(AppError):
    code = "unauthorized"
    status = 401


class Forbidden(AppError):
    code = "forbidden"
    status = 403


class Unprocessable(AppError):
    code = "unprocessable"
    status = 422


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"error": {"code": exc.code, "message": exc.message}})
