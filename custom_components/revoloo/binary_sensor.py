"""Binary sensor platform for the Revoloo integration.

These expose boolean fields that appear in the device get_info payloads but
for which no setter call was captured in the traffic dump, so they are
read-only here rather than switches.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_LITTER_BOX,
    DEVICE_TYPE_WATER_DISPENSER,
)
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


@dataclass(frozen=True, kw_only=True)
class RevolooBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Revoloo boolean device field."""

    value_fn: Callable[[dict[str, Any]], bool | None]


_LITTER_BOX_BINARY_SENSORS: tuple[RevolooBinarySensorDescription, ...] = (
    RevolooBinarySensorDescription(
        key="switch_litter",
        translation_key="litter_sensor_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda i: bool(i.get("switch_litter")),
    ),
    RevolooBinarySensorDescription(
        key="garbage_bag_switch",
        translation_key="garbage_bag_enabled",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda i: bool(i.get("garbage_bag_switch")),
    ),
)

_WATER_DISPENSER_BINARY_SENSORS: tuple[RevolooBinarySensorDescription, ...] = (
    RevolooBinarySensorDescription(
        key="water",
        translation_key="water_flowing",
        value_fn=lambda i: bool(i.get("water")),
    ),
    RevolooBinarySensorDescription(
        key="uvc",
        translation_key="uvc_active",
        value_fn=lambda i: bool(i.get("uvc")),
    ),
    RevolooBinarySensorDescription(
        key="present",
        translation_key="pet_present",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda i: bool(i.get("present")),
    ),
)

_FEEDER_BINARY_SENSORS: tuple[RevolooBinarySensorDescription, ...] = (
    RevolooBinarySensorDescription(
        key="food",
        translation_key="food_available",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda i: bool(i.get("food")),
    ),
    RevolooBinarySensorDescription(
        key="present",
        translation_key="pet_present",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda i: bool(i.get("present")),
    ),
)

DEVICE_BINARY_SENSORS: dict[str, tuple[RevolooBinarySensorDescription, ...]] = {
    DEVICE_TYPE_LITTER_BOX: _LITTER_BOX_BINARY_SENSORS,
    DEVICE_TYPE_WATER_DISPENSER: _WATER_DISPENSER_BINARY_SENSORS,
    DEVICE_TYPE_FEEDER: _FEEDER_BINARY_SENSORS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo binary sensors from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator

    entities: list[BinarySensorEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        for description in DEVICE_BINARY_SENSORS.get(device.device_type, ()):
            entities.append(
                RevolooBinarySensor(coordinator, user_device_id, description)
            )
    async_add_entities(entities)


class RevolooBinarySensor(RevolooDeviceEntity, BinarySensorEntity):
    """A binary sensor derived from a Revoloo device's get_info payload."""

    entity_description: RevolooBinarySensorDescription

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        description: RevolooBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self.entity_description = description
        self._attr_unique_id = f"{user_device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.device.info)
