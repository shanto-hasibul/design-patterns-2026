from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.domain.devices.entity import Device
from src.domain.sensors.ports import SensorAdapterError, SensorPort
from src.domain.sensors.reading import Reading


class MqttSensorAdapter(SensorPort):
    """Translates inbound MQTT JSON payload dicts into a normalized domain Reading (no broker in Phase 5)."""

    def __init__(self, last_payload: dict[str, Any] | None = None) -> None:
        self._last_payload = last_payload

    def translate_payload(
        self,
        device_id: UUID,
        payload: dict[str, Any],
        recorded_at: datetime | None = None,
    ) -> Reading:
        if not isinstance(payload, dict):
            raise SensorAdapterError("MQTT payload must be a dictionary.")

        if "value" not in payload or "unit" not in payload:
            raise SensorAdapterError(
                "MQTT payload must contain both 'value' and 'unit' fields."
            )

        try:
            numeric_val = float(payload["value"])
        except (TypeError, ValueError) as exc:
            raise SensorAdapterError(f"Invalid numeric 'value' in MQTT payload: {exc}") from exc

        unit = str(payload["unit"]).strip()
        if not unit:
            raise SensorAdapterError("MQTT payload 'unit' cannot be empty.")

        ts = recorded_at or datetime.now(timezone.utc)
        return Reading(
            device_id=device_id,
            value=numeric_val,
            unit=unit,
            source="mqtt",
            recorded_at=ts,
        )

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorAdapterError("Cannot read from an unpersisted device without an id.")

        if self._last_payload is not None:
            return self.translate_payload(device.id, self._last_payload)

        # Fallback synthetic MQTT payload for one-shot POST /read when no live broker is running
        default_unit = str(device.default_config.get("unit") or ("vwc" if "moisture" in device.device_type else "lux"))
        default_val = 0.41 if default_unit == "vwc" else 950.0
        return self.translate_payload(
            device.id,
            {"value": default_val, "unit": default_unit},
        )