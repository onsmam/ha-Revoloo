"""Button platform for the Revoloo integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_LITTER_BOX,
    DEVICE_TYPE_WATER_DISPENSER,
    LITTER_BOX_ONE_KEY_CLEAN,
    LITTER_BOX_ONE_KEY_SMOOTH,
)
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo buttons from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator
    client = coordinator.client

    entities: list[ButtonEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        if device.device_type == DEVICE_TYPE_LITTER_BOX:

            async def _clean_now(user_device_id: int) -> None:
                await client.litter_box_one_key(
                    user_device_id, one_key=LITTER_BOX_ONE_KEY_CLEAN
                )

            async def _smooth_litter(user_device_id: int) -> None:
                await client.litter_box_one_key(
                    user_device_id, one_key=LITTER_BOX_ONE_KEY_SMOOTH
                )

            entities.append(
                RevolooButton(
                    coordinator,
                    user_device_id,
                    key="clean_now",
                    translation_key="clean_now",
                    action_fn=_clean_now,
                )
            )
            entities.append(
                RevolooButton(
                    coordinator,
                    user_device_id,
                    key="smooth_litter",
                    translation_key="smooth_litter",
                    action_fn=_smooth_litter,
                )
            )
        elif device.device_type == DEVICE_TYPE_WATER_DISPENSER:
            entities.append(
                RevolooButton(
                    coordinator,
                    user_device_id,
                    key="reset_filter",
                    translation_key="reset_filter",
                    action_fn=client.water_dispenser_reset_filter,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            entities.append(
                RevolooButton(
                    coordinator,
                    user_device_id,
                    key="sterilize",
                    translation_key="sterilize",
                    action_fn=client.water_dispenser_sterilize,
                )
            )
        elif device.device_type == DEVICE_TYPE_FEEDER:

            async def _dispense_manual_qty(user_device_id: int) -> None:
                qty = coordinator.get_manual_feed_qty(user_device_id)
                await client.feeder_one_key(user_device_id, qty=qty)

            entities.append(
                RevolooButton(
                    coordinator,
                    user_device_id,
                    key="dispense_food",
                    translation_key="dispense_food",
                    action_fn=_dispense_manual_qty,
                )
            )
    async_add_entities(entities)


class RevolooButton(RevolooDeviceEntity, ButtonEntity):
    """A button that triggers a one-off Revoloo device action."""

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        *,
        key: str,
        translation_key: str,
        action_fn: Callable[[int], Awaitable[None]],
        entity_category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self._action_fn = action_fn
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{user_device_id}_{key}"
        self._attr_entity_category = entity_category

    async def async_press(self) -> None:
        await self._action_fn(self._user_device_id)
        await self.coordinator.async_request_refresh()
