from fastapi import FastAPI

from app.core.error_handlers import register_error_handlers
from app.routes import alarms, analysis, health, metrics, plant, simulations

app = FastAPI(title="Plant Simulation API", version="0.1.0")
register_error_handlers(app)
app.include_router(health.router)
app.include_router(plant.router)
app.include_router(analysis.router)
app.include_router(alarms.router)
app.include_router(simulations.router)
app.include_router(metrics.router)