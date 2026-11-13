import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from src.application.readings.sampler import SimulationSampler
from src.infrastructure.persistence.base import SessionLocal
from src.infrastructure.persistence.device_repository import DeviceRepository
from src.infrastructure.persistence.reading_repository import ReadingRepository
from src.infrastructure.settings import settings
from src.interfaces.api.devices import router as devices_router
from src.interfaces.api.health import health_check
from src.interfaces.api.locations import router as locations_router
from src.interfaces.api.sensors import router as sensors_router


async def _sampler_loop() -> None:
    while True:
        try:
            with SessionLocal() as session:
                sampler = SimulationSampler(
                    device_repo=DeviceRepository(session),
                    reading_repo=ReadingRepository(session),
                )
                sampler.run_once(datetime.now(timezone.utc))
        except Exception:
            pass
        await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_sampler_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Smart Greenhouse API",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_api_route(
    "/health",
    health_check,
    methods=["GET"],
    tags=["Health"],
)

app.include_router(sensors_router)
app.include_router(devices_router)
app.include_router(locations_router)


@app.get("/")
def root():
    return {
        "name": "Smart Greenhouse API",
        "health": "/health",
        "api_reference": "/scalar",
    }


@app.get("/scalar", include_in_schema=False)
def scalar_api_reference():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="Smart Greenhouse API Reference",
    )