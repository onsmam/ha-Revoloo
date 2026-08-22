"""Switch platform for the Revoloo integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_FEEDER, DEVICE_TYPE_LITTER_BOX, DEVICE_TYPE_WATER_DISPENSER
from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo switches from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator
    client = coordinator.client

    entities: list[SwitchEntity] = []
    for user_device_id, device in coordinator.data.devices.items():
        if device.device_type == DEVICE_TYPE_WATER_DISPENSER:
            entities.append(RevolooUvcSwitch(coordinator, user_device_id))
            entities.append(
                RevolooLedSwitch(
                    coordinator,
                    user_device_id,
                    client.water_dispenser_set_led,
                    entity_category=EntityCategory.CONFIG,
                )
            )
            entities.append(
                RevolooReminderSwitch(
                    coordinator,
                    user_device_id,
                    key="filter_reminder",
                    translation_key="filter_reminder",
                    state_info_key="open_filter_remind",
                    set_fn=client.water_dispenser_set_filter_remind_enabled,
                )
            )
        elif device.device_type == DEVICE_TYPE_LITTER_BOX:
            entities.append(RevolooKeyLockSwitch(coordinator, user_device_id))
            entities.append(
                RevolooReminderSwitch(
                    coordinator,
                    user_device_id,
                    key="litter_reminder",
                    translation_key="litter_reminder",
                    state_info_key="open_litter_remind",
                    cycle_time_info_key="default_remaining_days",
                    set_fn=client.litter_box_set_litter_remind_enabled,
                )
            )
            entities.append(
                RevolooReminderSwitch(
                    coordinator,
                    user_device_id,
                    key="garbage_bag_reminder",
                    translation_key="garbage_bag_reminder",
                    state_info_key="open_garbagebag_remind",
                    cycle_time_info_key="garbage_bag_cycle_time",
                    set_fn=client.litter_box_set_garbage_bag_remind_enabled,
                )
            )
        elif device.device_type == DEVICE_TYPE_FEEDER:
            entities.append(
                RevolooLedSwitch(coordinator, user_device_id, client.feeder_set_led)
            )
            entities.append(RevolooDesiccantReminderSwitch(coordinator, user_device_id))
            entities.append(RevolooFunctionLockSwitch(coordinator, user_device_id))
    async_add_entities(entities)


class RevolooUvcSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the water dispenser's UVC sterilization lamp."""

    _attr_translation_key = "uvc_switch"
    _attr_entity_category = EntityCategory.CONFIG

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


class RevolooKeyLockSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the litter box's button lock."""

    _attr_translation_key = "key_lock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_key_lock"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("switch_key"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.litter_box_set_key(self._user_device_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.litter_box_set_key(self._user_device_id, False)
        await self.coordinator.async_request_refresh()


class RevolooReminderSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables a litter box reminder notification.

    Turning on re-sends the reminder's current cycle_time (the API requires
    it on the "on" action); turning off sends no cycle_time, matching what
    the app itself does.
    """

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        *,
        key: str,
        translation_key: str,
        state_info_key: str,
        cycle_time_info_key: str | None = None,
        set_fn: Callable[[int, bool, int | None], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self._state_info_key = state_info_key
        self._cycle_time_info_key = cycle_time_info_key
        self._set_fn = set_fn
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{user_device_id}_{key}"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get(self._state_info_key))

    async def async_turn_on(self, **kwargs) -> None:
        cycle_time = (
            self.device.info.get(self._cycle_time_info_key)
            if self._cycle_time_info_key
            else None
        )
        await self._set_fn(self._user_device_id, True, cycle_time)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_fn(self._user_device_id, False, None)
        await self.coordinator.async_request_refresh()


class RevolooLedSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables a device's LED.

    The set_led calls also carry the do-not-disturb schedule, so the current
    values are passed straight through to avoid clobbering them.
    """

    _attr_translation_key = "led"

    def __init__(
        self,
        coordinator: RevolooCoordinator,
        user_device_id: int,
        set_led_fn: Callable[[int, bool, str, str], Awaitable[None]],
        *,
        entity_category: EntityCategory | None = None,
    ) -> None:
        super().__init__(coordinator, user_device_id)
        self._set_led_fn = set_led_fn
        self._attr_unique_id = f"{user_device_id}_led"
        self._attr_entity_category = entity_category

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("led"))

    async def _async_set_led(self, led: bool) -> None:
        await self._set_led_fn(
            self._user_device_id,
            led,
            self.device.info.get("dnd_begin_time") or "",
            self.device.info.get("dnd_end_time") or "",
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_led(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_led(False)


class RevolooDesiccantReminderSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the feeder's desiccant replacement reminder."""

    _attr_translation_key = "desiccant_reminder"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_desiccant_reminder"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("open_desiccant_remind"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.feeder_set_desiccant_reminder(
            self._user_device_id, True
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.feeder_set_desiccant_reminder(
            self._user_device_id, False
        )
        await self.coordinator.async_request_refresh()


class RevolooFunctionLockSwitch(RevolooDeviceEntity, SwitchEntity):
    """Enables/disables the feeder's function button lock."""

    _attr_translation_key = "function_lock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_function_lock"

    @property
    def is_on(self) -> bool:
        return bool(self.device.info.get("lock"))

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.client.feeder_set_lock(self._user_device_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.client.feeder_set_lock(self._user_device_id, False)
        await self.coordinator.async_request_refresh()
