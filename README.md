# Smart Greenhouse API & Dashboard

Full-stack IoT greenhouse platform built across Phases 1–12 using FastAPI, SQLAlchemy, Alembic, PostgreSQL, and React + TypeScript + Tailwind CSS.

## Quick Start (Course Demo — No Hardware or Broker Required)

```bash
docker compose up --build
```
- **Dashboard UI**: `http://localhost:5173`
- **Scalar API Reference**: `http://localhost:8000/scalar`
- **Dashboard WebSocket**: `ws://localhost:8000/api/ws`

On startup, `alembic upgrade head` applies all migrations through the Phase 12 `schema_hardening` revision, which idempotently seeds **Demo Greenhouse North** with a simulation moisture sensor (`id: 33333333-3333-3333-3333-333333333333`, `sampling_interval_seconds: 5`, `tracking_enabled: true`) so live readings and WebSocket updates run out of the box with zero hardware.

## Device HTTP Smoke Test (`protocol: http`)

Controllers using HTTP poll their sampling configuration and post readings directly:

    curl http://localhost:8000/api/devices/33333333-3333-3333-3333-333333333333/sampling

    curl -X POST http://localhost:8000/api/devices/33333333-3333-3333-3333-333333333333/readings -H "Content-Type: application/json" -d '{"value": 0.24, "unit": "vwc"}'

## Optional MQTT Broker Profile (`protocol: mqtt`)

Mosquitto is configured as an optional Docker Compose profile (`mqtt`) and does **not** start during a standard `docker compose up`:

    MQTT_BROKER_URL=mqtt://mosquitto:1883 docker compose --profile mqtt up --build

- **Reading Topic (Device -> Backend)**: `greenhouse/devices/{device_id}/reading` with JSON `{"value": 0.25, "unit": "vwc"}`.
- **Retained Config Topic (Backend -> Device)**: `greenhouse/devices/{device_id}/config` published with `retain=True` whenever `PATCH /api/devices/{device_id}/sampling` updates a device with `default_config.protocol == "mqtt"`.

## Architecture & Pattern Notes

- Pattern notes live in `docs/patterns/` (`factory-method.md`, `abstract-factory.md`, `builder.md`, `strategy.md`, `facade.md`, `state.md`, `decorator.md`, `command.md`, `observer.md`).
- Phase question answers live in `docs/phases/`.