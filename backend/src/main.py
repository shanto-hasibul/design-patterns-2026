from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from src.infrastructure.settings import settings
from src.interfaces.api.health import health_check

app = FastAPI(
    title="Smart Greenhouse API",
    docs_url=None,
    redoc_url=None,
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