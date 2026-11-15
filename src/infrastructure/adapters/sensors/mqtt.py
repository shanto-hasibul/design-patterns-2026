from datetime import datetime, timezone
from typing import Any
from src.domain.devices.entity import Device
from src.domain.sensors.ports import SensorAdapterError, SensorPort
from src.domain.sensors.reading import Reading


class MqttSensorAdapter(SensorPort):
    """Translates raw external sensor payloads (MQTT or Device HTTP) into domain Reading objects."""

    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        source: str = "mqtt",
    ) -> None:
        self._payload = payload
        self._source = source

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorAdapterError("Device must be persisted with an id before reading.")
        if self._payload is None:
            raise SensorAdapterError(
                f"No external payload provided for device '{device.id}'."
            )
        return self.translate_payload(device, self._payload, source=self._source)

    @staticmethod
    def translate_payload(
        device: Device,
        payload: dict[str, Any],
        source: str = "mqtt",
    ) -> Reading:
        if device.id is None:
            raise SensorAdapterError("Device must be persisted with an id before reading.")
        if not isinstance(payload, dict) or "value" not in payload:
            raise SensorAdapterError("Payload must be a JSON object containing 'value'.")

        try:
            numeric_value = float(payload["value"])
        except (TypeError, ValueError) as exc:
            raise SensorAdapterError(
                f"Invalid numeric value in payload: {payload.get('value')!r}"
            ) from exc

        default_unit = "lux" if "light" in device.device_type.lower() else "vwc"
        unit = str(payload.get("unit") or device.default_config.get("unit") or default_unit)

        recorded_at = datetime.now(timezone.utc)
        raw_ts = payload.get("recorded_at") or payload.get("timestamp")
        if isinstance(raw_ts, str) and raw_ts.strip():
            try:
                parsed = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                recorded_at = (
                    parsed.replace(tzinfo=timezone.utc)
                    if parsed.tzinfo is None
                    else parsed
                )
            except ValueError as exc:
                raise SensorAdapterError(
                    f"Invalid ISO timestamp in payload: {raw_ts!r}"
                ) from exc

        return Reading(
            device_id=device.id,
            value=numeric_value,
            unit=unit,
            source=source,
            recorded_at=recorded_at,
        )