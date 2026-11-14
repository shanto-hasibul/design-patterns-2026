from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.domain.devices.entity import Device
from src.domain.sensors.ports import SensorAdapterError, SensorPort
from src.domain.sensors.reading import Reading


@dataclass(frozen=True)
class VendorRawPacket:
    """Simulated proprietary third-party SDK packet using non-standard field names."""
    channel_code: str
    raw_millivolts: int
    scale_factor: float
    uom_code: str
    epoch_ms: int


class VendorStubSensorAdapter(SensorPort):
    """Translates proprietary VendorRawPacket / dict structures into a normalized Reading."""

    _UOM_MAP = {
        "PCT_VWC": "vwc",
        "VWC": "vwc",
        "LUX_PAR": "lux",
        "LUX": "lux",
    }

    def __init__(self, raw_payload: VendorRawPacket | dict[str, Any] | None = None) -> None:
        self._raw_payload = raw_payload

    def read(self, device: Device) -> Reading:
        if device.id is None:
            raise SensorAdapterError("Cannot read from an unpersisted device without an id.")

        packet = self._raw_payload or self._build_default_vendor_packet(device)
        return self.translate_vendor_payload(device, packet)

    def translate_vendor_payload(
        self,
        device: Device,
        packet: VendorRawPacket | dict[str, Any],
    ) -> Reading:
        if device.id is None:
            raise SensorAdapterError("Device id is required for vendor translation.")

        if isinstance(packet, VendorRawPacket):
            raw_mv = packet.raw_millivolts
            scale = packet.scale_factor
            uom_code = packet.uom_code
            epoch_ms = packet.epoch_ms
        elif isinstance(packet, dict):
            try:
                raw_mv = int(packet["raw_millivolts"])
                scale = float(packet.get("scale_factor", 0.001))
                uom_code = str(packet["uom_code"])
                epoch_ms = int(
                    packet.get(
                        "epoch_ms",
                        int(datetime.now(timezone.utc).timestamp() * 1000),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise SensorAdapterError(f"Malformed vendor payload: {exc}") from exc
        else:
            raise SensorAdapterError("Unsupported vendor payload type.")

        normalized_value = round(raw_mv * scale, 4)
        normalized_unit = self._UOM_MAP.get(uom_code.upper(), uom_code.lower())
        recorded_at = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)

        return Reading(
            device_id=device.id,
            value=float(normalized_value),
            unit=normalized_unit,
            source="vendor",
            recorded_at=recorded_at,
        )

    @staticmethod
    def _build_default_vendor_packet(device: Device) -> VendorRawPacket:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        if "moisture" in device.device_type.lower():
            return VendorRawPacket(
                channel_code="CH_SOIL_01",
                raw_millivolts=420,
                scale_factor=0.001,
                uom_code="PCT_VWC",
                epoch_ms=now_ms,
            )
        return VendorRawPacket(
            channel_code="CH_LIGHT_01",
            raw_millivolts=850,
            scale_factor=1.0,
            uom_code="LUX_PAR",
            epoch_ms=now_ms,
        )