from fastapi import FastAPI

from app.core.error_handlers import register_error_handlers
from app.routes import health

app = FastAPI(title="Plant Simulation API", version="0.1.0")
register_error_handlers(app)
app.include_router(health.router)