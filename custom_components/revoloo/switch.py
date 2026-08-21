"""Switch platform for the Revoloo integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_WATER_DISPENSER
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo switches from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator

    entities: list[SwitchEntity] = [
        RevolooUvcSwitch(coordinator, user_device_id)
        for user_device_id, device in coordinator.data.devices.items()
        if device.device_type == DEVICE_TYPE_WATER_DISPENSER
    ]
    async_add_entities(entities)


class RevolooUvcSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the water dispenser's UVC sterilization lamp."""

    _attr_translation_key = "uvc_switch"

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_uvc_switch"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("uvc_switch"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.water_dispenser_set_uvc(
            self._user_device_id, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.water_dispenser_set_uvc(
            self._user_device_id, False
        )
        await self.coordinator.async_request_refresh()
