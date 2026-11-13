# Strategy Pattern — Pluggable Automation Algorithms

## Problem
Different crops and greenhouse operating modes require different irrigation decision rules (for example, a water-saving **conservative** policy versus a yield-maximizing **aggressive** policy). Hardcoding conditional branches (`if strategy == "conservative": ... elif strategy == "aggressive": ...`) inside FastAPI routers or repository queries couples transport code to irrigation math and makes adding new algorithms risky.

## Solution
We apply the **Strategy** pattern (`backend/src/domain/automation/strategy.py`):
1. **Context (`LocationAutomationContext`, `ZoneAutomationContext` in `domain/automation/context.py`)**: A pure Python immutable snapshot assembled by `AutomationRepository.build_location_context(location_id)` using each zone's persisted VWC thresholds (`zones.moisture_threshold_low`, `moisture_threshold_high`) and the latest reading from moisture sensors assigned to that `zone_id` (never borrowing readings from unassigned devices or other zones).
2. **Strategy Interface (`AutomationStrategy`)**: Declares `key` and `decide(context: LocationAutomationContext) -> Recommendation`.
3. **Concrete Strategies**:
   - **`ConservativeMoistureStrategy` (`"conservative"`)**: Recommends `"irrigate"` only when `latest_moisture < moisture_threshold_low`; otherwise `"wait"`.
   - **`AggressiveMoistureStrategy` (`"aggressive"`)**: Recommends `"irrigate"` proactively whenever `latest_moisture < (moisture_threshold_low + moisture_threshold_high) / 2`; otherwise `"wait"`.
4. **Persistence (`automation_rules` table)**: Stores one active `strategy_key` per `location_id` (`UNIQUE`), updated via `PUT /api/locations/{location_id}/automation/strategy` and evaluated via `POST /api/locations/{location_id}/automation/evaluate`.

## Where to Look in Code
- **Domain Context & Strategies**: `backend/src/domain/automation/context.py`, `backend/src/domain/automation/strategy.py`
- **Application Service & DTOs**: `backend/src/application/automation/service.py`, `backend/src/application/automation/dto.py`
- **Persistence & ORM**: `backend/src/infrastructure/persistence/automation_repository.py`, `models.py` (`AutomationRuleRow`)
- **REST Endpoints**: `backend/src/interfaces/api/automation.py`
- **Dashboard UI**: `frontend/src/components/automation/StrategyPanel.tsx`

## Extension Exercise: Adding a Third Strategy (`light_aware`)
1. Subclass `AutomationStrategy` in `backend/src/domain/automation/strategy.py` as `LightAwareMoistureStrategy` with `key = "light_aware"`.
2. In `decide(context)`, inspect both `zone.latest_moisture` and `zone.latest_light` (for example, raising the moisture trigger threshold when `latest_light > 1000.0` lux due to higher evapotranspiration).
3. Register `"light_aware": LightAwareMoistureStrategy` in `_STRATEGIES` without touching the FastAPI router or database schema.