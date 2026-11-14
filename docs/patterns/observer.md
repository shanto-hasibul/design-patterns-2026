# Observer Pattern — In-Process Event Bus & Alert Persistence

## Problem
When new sensor readings arrive (`ReadingIngest`), commands fail (`CommandService`), or actuators enter an `error` state (`ActuatorStateService`), multiple downstream reactions are needed—persisting threshold-crossed alerts to PostgreSQL (`alerts`), updating metrics, and (in Phase 12) broadcasting live events over WebSockets. Calling `AlertRepository` or WebSocket managers directly inside sensor adapters or command handlers tightly couples core domain workflows to side-effect consumers.

## Solution
We implement an in-process **Observer** (`EventBus` in `backend/src/domain/events/bus.py`) with typed domain events (`backend/src/domain/events/events.py`):
1. **Publishers**:
   - `ReadingIngest.record()` publishes `ReadingCreated` (copying `location_id` and `zone_id` from the device, leaving both `None` when unassigned) **only when `device.tracking_enabled` is `True`**.
   - `CommandService` publishes `CommandCompleted` or `CommandFailed` (and `ActuatorStateChanged` on transitions).
   - `ActuatorStateService` publishes `ActuatorStateChanged`.
2. **Subscribers (`backend/src/application/alerts/subscribers.py`)**:
   - `AlertPersistenceSubscriber` listens for `ReadingCreated` (checking zone `moisture_threshold_low`), `ThresholdCrossed`, `CommandFailed`, and `ActuatorStateChanged` (`new_state == "error"`), persisting active rows into `alerts`.
   - `MetricsSubscriber` tracks event counts in memory without requiring a database table.
3. **Frontend Polling & Phase 12 Stub**:
   - `EventFeed.tsx` polls `GET /api/alerts` every 4 seconds with location, zone, and status filters.
   - `frontend/src/services/realtime.ts` provides the `subscribeRealtime()` stub that Phase 12 will back with a live WebSocket connection.

## Where to Look in Code
- **Domain Events & Bus**: `backend/src/domain/events/events.py`, `backend/src/domain/events/bus.py`
- **Subscribers & DTOs**: `backend/src/application/alerts/subscribers.py`, `dto.py`
- **Publishers**: `backend/src/application/readings/service.py`, `backend/src/application/commands/service.py`, `backend/src/application/devices/actuator_state_service.py`
- **Persistence & Migration**: `backend/src/infrastructure/persistence/alert_repository.py`, `models.py`, `backend/alembic/versions/c3f4a784d189_alerts.py`
- **API & UI**: `backend/src/interfaces/api/alerts.py`, `frontend/src/components/events/EventFeed.tsx`, `frontend/src/services/realtime.ts`