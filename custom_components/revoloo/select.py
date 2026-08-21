"""Select platform for the Revoloo integration (device modes)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_TYPE_LITTER_BOX,
    DEVICE_TYPE_WATER_DISPENSER,
    LITTER_BOX_MODES,
    WATER_DISPENSER_MODES,
)
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo mode selects from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator
    client = coordinator.client

    entities: list[SelectEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        if device.device_type == DEVICE_TYPE_LITTER_BOX:
            entities.append(
                RevolooModeSelect(
                    coordinator,
                    user_device_id,
                    key="mode",
                    translation_key="litter_box_mode",
                    modes=LITTER_BOX_MODES,
                    set_mode_fn=client.litter_box_set_mode,
                )
            )
        elif device.device_type == DEVICE_TYPE_WATER_DISPENSER:
            entities.append(
                RevolooModeSelect(
                    coordinator,
                    user_device_id,
                    key="mode",
                    translation_key="water_dispenser_mode",
                    modes=WATER_DISPENSER_MODES,
                    set_mode_fn=client.water_dispenser_change_mode,
                )
            )
    async_add_entities(entities)


class RevolooModeSelect(RevolooDeviceEntity, SelectEntity):
    """A select entity mapping a device's numeric mode field to labels."""

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        *,
        key: str,
        translation_key: str,
        modes: dict[int, str],
        set_mode_fn: Callable[[int, int], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self._key = key
        self._modes = modes
        self._modes_reverse = {v: k for k, v in modes.items()}
        self._set_mode_fn = set_mode_fn
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{user_device_id}_{key}"
        self._attr_options = list(modes.values())

    @property
    def current_option(self) -> str | None:
        return self._modes.get(self.device.info.get(self._key))

    async def async_select_option(self, option: str) -> None:
        mode = self._modes_reverse[option]
        await self._set_mode_fn(self._user_device_id, mode)
        await self.coordinator.async_request_refresh()
