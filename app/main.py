import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import auth, checkin, me, points, service_keys, users, webhooks
from .config import get_settings
from .db import Base, engine
from .errors import AppError, app_error_handler

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title="Community Account System", version="0.1.0", docs_url="/docs")

app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_handler(_, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "validation_error", "message": str(exc.errors())}})


@app.exception_handler(StarletteHTTPException)
async def http_handler(_, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": "http_error", "message": str(exc.detail)}})


for r in (auth.router, me.router, service_keys.router, users.router, points.router, checkin.router, webhooks.router):
    app.include_router(r)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "cas"}


@app.on_event("startup")
def create_tables() -> None:
    # Convenience for dev/test; production uses alembic upgrade head.
    Base.metadata.create_all(bind=engine)
