# Facade Pattern — Location Dashboard Overview

## Why One Entry Point
Rendering the dashboard **Overview** section requires data scattered across four subsystems built in Phases 2–6:
1. **Locations & Zones** (`LocationRepository`)
2. **Assigned Devices** (`DeviceRepository`, filtered to `location_id` and non-null `zone_id`)
3. **Latest Sensor Readings** (`ReadingRepository`, newest `sensor_readings` row per assigned device)
4. **Automation Rules & Strategy Evaluation** (`AutomationRepository` + `AutomationService`)

Without a Facade, either the FastAPI router (`interfaces/api/overview.py`) would import and orchestrate four repositories directly, or the React frontend (`OverviewPanel.tsx`) would issue multiple sequential API requests and stitch them together in the browser. `LocationOverviewFacade` (`backend/src/application/overview/facade.py`) hides that coordination behind a single `get_overview(location_id) -> LocationOverviewDto` method, so the HTTP router calls **only** the facade.

## Query Shape & Recommendation Computation
Inside `LocationOverviewFacade.get_overview(location_id)`:
1. **One load** of the location and its zones (`LocationRepository.get_config`).
2. **One query** for all devices assigned to that location (`DeviceRepository.list_assigned_devices_for_location`), excluding unassigned devices (`zone_id IS NULL`).
3. **One batch query** for the newest reading per assigned device ID (`ReadingRepository.get_latest_readings_for_devices` using `DISTINCT ON (device_id) ... ORDER BY device_id, recorded_at DESC`) rather than running an N+1 query loop per device.
4. **One lookup** of the saved strategy key (`AutomationRepository.find_saved_strategy_key`).
5. **On-demand recommendation**: If a strategy key is saved, the facade delegates to `AutomationService.evaluate()`, which computes `last_recommendation` on each `GET` request (which internally loads moisture once per zone to build `LocationAutomationContext`) rather than duplicating `decide()` or caching recommendations in a separate table. When no strategy key has been saved yet, `GET /api/locations/{location_id}/overview` still returns HTTP `200` with `strategy_key: null` and `last_recommendation: null`.

## Schema Note
No new database tables or migrations were required for Phase 7: existing Phase 2–6 tables (`locations`, `zones`, `devices`, `sensor_readings`, `automation_rules`) provide everything needed for `LocationOverviewFacade`.