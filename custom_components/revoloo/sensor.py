"""Sensor platform for the Revoloo integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_LITTER_BOX,
    DEVICE_TYPE_WATER_DISPENSER,
)
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity, RevolooPetEntity

# Best-effort labels for device status codes actually observed in the capture.
# Any other value is shown as its raw number rather than guessed at.
_LITTER_BOX_STATUS = {0: "idle", 4: "cleaning"}

# "status_id" is a generic field present on every device type (alongside
# is_owner, aliyun_device_name, etc). Only 1 ("normal") has been confirmed
# so far; other codes are unknown and shown as their raw number.
_STATUS_ID_LABELS = {1: "normal"}


@dataclass(frozen=True, kw_only=True)
class RevolooDeviceSensorDescription(SensorEntityDescription):
    """Describes a Revoloo device sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _last_event(info: dict[str, Any]) -> str | None:
    events = info.get("events") or []
    return events[0]["event"] if events else None


def _last_event_attrs(info: dict[str, Any]) -> dict[str, Any]:
    events = info.get("events") or []
    if not events:
        return {}
    latest = events[0]
    return {
        "date": latest.get("date"),
        "time": latest.get("time"),
        "event_type_id": latest.get("event_type_id"),
        "recent_events": [e.get("event") for e in events[:10]],
    }


_COMMON_EVENT_SENSOR = RevolooDeviceSensorDescription(
    key="last_event",
    translation_key="last_event",
    value_fn=_last_event,
    attrs_fn=_last_event_attrs,
)

_LITTER_BOX_SENSORS: tuple[RevolooDeviceSensorDescription, ...] = (
    _COMMON_EVENT_SENSOR,
    RevolooDeviceSensorDescription(
        key="status",
        translation_key="litter_box_status",
        value_fn=lambda i: _LITTER_BOX_STATUS.get(i.get("status"), i.get("status")),
    ),
    RevolooDeviceSensorDescription(
        key="today_clean_count",
        translation_key="today_clean_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda i: i.get("today_clean_count"),
    ),
    RevolooDeviceSensorDescription(
        key="toilet_count",
        translation_key="toilet_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda i: i.get("toilet_count"),
    ),
    RevolooDeviceSensorDescription(
        key="litter_remaining_days",
        translation_key="litter_remaining_days",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda i: i.get("remaining_days"),
        attrs_fn=lambda i: {"default_remaining_days": i.get("default_remaining_days")},
    ),
    RevolooDeviceSensorDescription(
        key="garbage_bag_remaining_days",
        translation_key="garbage_bag_remaining_days",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda i: i.get("garbage_bag_remaining_days"),
        attrs_fn=lambda i: {"cycle_time_days": i.get("garbage_bag_cycle_time")},
    ),
)

_WATER_DISPENSER_SENSORS: tuple[RevolooDeviceSensorDescription, ...] = (
    _COMMON_EVENT_SENSOR,
    RevolooDeviceSensorDescription(
        key="status_id",
        translation_key="water_dispenser_status",
        value_fn=lambda i: _STATUS_ID_LABELS.get(
            i.get("status_id"), i.get("status_id")
        ),
    ),
    RevolooDeviceSensorDescription(
        key="filter_remaining_days",
        translation_key="filter_remaining_days",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda i: i.get("remaining_days"),
        attrs_fn=lambda i: {"default_remaining_days": i.get("default_remaining_days")},
    ),
)

_FEEDER_SENSORS: tuple[RevolooDeviceSensorDescription, ...] = (
    _COMMON_EVENT_SENSOR,
    RevolooDeviceSensorDescription(
        key="status_id",
        translation_key="feeder_status",
        value_fn=lambda i: _STATUS_ID_LABELS.get(
            i.get("status_id"), i.get("status_id")
        ),
    ),
    RevolooDeviceSensorDescription(
        key="meals_fed_today",
        translation_key="meals_fed_today",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda i: (i.get("auto_qty") or 0) + (i.get("manual_qty") or 0),
    ),
    RevolooDeviceSensorDescription(
        key="meals_fed_today_auto",
        translation_key="meals_fed_today_auto",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda i: i.get("auto_qty"),
    ),
    RevolooDeviceSensorDescription(
        key="meals_fed_today_manual",
        translation_key="meals_fed_today_manual",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda i: i.get("manual_qty"),
    ),
    RevolooDeviceSensorDescription(
        key="plan_qty",
        translation_key="plan_qty",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda i: i.get("plan_qty"),
    ),
    RevolooDeviceSensorDescription(
        key="desiccant_remaining_days",
        translation_key="desiccant_remaining_days",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda i: i.get("remaining_days"),
        attrs_fn=lambda i: {"default_remaining_days": i.get("default_remaining_days")},
    ),
)

_FEEDER_PLAN_ATTR_KEYS = ("plan_id", "time", "quantity", "open")

DEVICE_SENSORS: dict[str, tuple[RevolooDeviceSensorDescription, ...]] = {
    DEVICE_TYPE_LITTER_BOX: _LITTER_BOX_SENSORS,
    DEVICE_TYPE_WATER_DISPENSER: _WATER_DISPENSER_SENSORS,
    DEVICE_TYPE_FEEDER: _FEEDER_SENSORS,
}


@dataclass(frozen=True, kw_only=True)
class RevolooPetSensorDescription(SensorEntityDescription):
    """Describes a Revoloo pet sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


_PET_SENSORS: tuple[RevolooPetSensorDescription, ...] = (
    RevolooPetSensorDescription(
        key="weight",
        translation_key="weight",
        device_class=SensorDeviceClass.WEIGHT,
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: p.get("today_weight"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_weight"),
            "difference": p.get("diff_weight_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="litter_box_visits",
        translation_key="litter_box_visits",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: p.get("today_wc_count"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_wc_count"),
            "difference": p.get("diff_wc_count_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="litter_box_duration",
        translation_key="litter_box_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: p.get("today_wc_duration"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_wc_duration"),
            "difference": p.get("diff_wc_duration_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="eating_count",
        translation_key="eating_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: p.get("today_eat_count"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_eat_count"),
            "difference": p.get("diff_eat_count_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="eating_duration",
        translation_key="eating_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: p.get("today_eat_duration"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_eat_duration"),
            "difference": p.get("diff_eat_duration_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="drinking_count",
        translation_key="drinking_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: p.get("today_drink_count"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_drink_count"),
            "difference": p.get("diff_drink_count_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="drinking_duration",
        translation_key="drinking_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: p.get("today_drink_duration"),
        attrs_fn=lambda p: {
            "yesterday": p.get("yesterday_drink_duration"),
            "difference": p.get("diff_drink_duration_str"),
        },
    ),
    RevolooPetSensorDescription(
        key="wc_status",
        translation_key="wc_status",
        value_fn=lambda p: p.get("wc_status") or None,
    ),
    RevolooPetSensorDescription(
        key="eat_status",
        translation_key="eat_status",
        value_fn=lambda p: p.get("eat_status") or None,
    ),
    RevolooPetSensorDescription(
        key="drink_status",
        translation_key="drink_status",
        value_fn=lambda p: p.get("drink_status") or None,
    ),
    RevolooPetSensorDescription(
        key="weight_status",
        translation_key="weight_status",
        value_fn=lambda p: p.get("weight_status") or None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo sensors from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator

    entities: list[SensorEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        for description in DEVICE_SENSORS.get(device.device_type, ()):
            entities.append(
                RevolooDeviceSensor(coordinator, user_device_id, description)
            )
        if device.device_type == DEVICE_TYPE_FEEDER:
            entities.append(RevolooFeedingPlansSensor(coordinator, user_device_id))
    for pet_id in coordinator.data.pets:
        for description in _PET_SENSORS:
            entities.append(RevolooPetSensor(coordinator, pet_id, description))

    async_add_entities(entities)


class RevolooDeviceSensor(RevolooDeviceEntity, SensorEntity):
    """A sensor derived from a Revoloo device's get_info payload."""

    entity_description: RevolooDeviceSensorDescription

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        description: RevolooDeviceSensorDescription,
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self.entity_description = description
        self._attr_unique_id = f"{user_device_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.device.info)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.device.info)


class RevolooFeedingPlansSensor(RevolooDeviceEntity, SensorEntity):
    """The feeder's current on-device feeding plans (read-only)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "feeding_plans"
    _attr_state_class = None

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_feeding_plans"

    @property
    def native_value(self) -> int:
        return len(self.device.plans)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "plans": [
                {k: plan.get(k) for k in _FEEDER_PLAN_ATTR_KEYS}
                for plan in self.device.plans
            ]
        }


class RevolooPetSensor(RevolooPetEntity, SensorEntity):
    """A sensor derived from a pet's /pet/list payload."""

    entity_description: RevolooPetSensorDescription

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        pet_id: int,
        description: RevolooPetSensorDescription,
    ) -> None:
        super().__init__(coordinator, pet_id)
        self.entity_description = description
        self._attr_unique_id = f"pet_{pet_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.pet)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.pet)
