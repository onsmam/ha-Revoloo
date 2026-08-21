"""Update platform for the Revoloo integration.

Read-only: the capture did not include an endpoint to trigger an OTA
install, only /device/check_upgrade to report available firmware.
"""
from __future__ import annotations

from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import RevolooCoordinator
from .entity import RevolooDeviceEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Revoloo firmware update entities from a config entry."""
    coordinator: RevolooCoordinator = entry.runtime_data.coordinator

    async_add_entities(
        RevolooUpdate(coordinator, user_device_id)
        for user_device_id in coordinator.data.devices
    )


class RevolooUpdate(RevolooDeviceEntity, UpdateEntity):
    """Firmware update status for a Revoloo device."""

    _attr_translation_key = "firmware"

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator, user_device_id)
        self._attr_unique_id = f"{user_device_id}_firmware"

    @property
    def installed_version(self) -> str | None:
        return self.device.upgrade.get("src_version") or None

    @property
    def latest_version(self) -> str | None:
        return self.device.upgrade.get("dest_version") or self.installed_version

    @property
    def release_summary(self) -> str | None:
        return self.device.upgrade.get("firmware_desc") or None

    @property
    def in_progress(self) -> bool:
        return bool(self.device.upgrade.get("task_status"))
