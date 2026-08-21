"""Base entities for the Revoloo integration."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RevolooCoordinator, RevolooDevice


class RevolooDeviceEntity(CoordinatorEntity[RevolooCoordinator]):
    """Base entity tied to one physical Revoloo device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RevolooCoordinator, user_device_id: int) -> None:
        super().__init__(coordinator)
        self._user_device_id = user_device_id
        device = self.device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(user_device_id))},
            name=device.info.get("alias") or device.info.get("device_name"),
            manufacturer=MANUFACTURER,
            model=device.info.get("device_name"),
            sw_version=device.upgrade.get("src_version") or None,
        )

    @property
    def device(self) -> RevolooDevice:
        return self.coordinator.data.devices[self._user_device_id]

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._user_device_id in self.coordinator.data.devices
        )


class RevolooPetEntity(CoordinatorEntity[RevolooCoordinator]):
    """Base entity tied to one pet (cat)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RevolooCoordinator, pet_id: int) -> None:
        super().__init__(coordinator)
        self._pet_id = pet_id
        pet = self.pet
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"pet_{pet_id}")},
            name=pet.get("name"),
            manufacturer=MANUFACTURER,
            model=pet.get("breed_name"),
        )

    @property
    def pet(self) -> dict:
        return self.coordinator.data.pets[self._pet_id]

    @property
    def available(self) -> bool:
        return super().available and self._pet_id in self.coordinator.data.pets

    @property
    def entity_picture(self) -> str | None:
        return self.pet.get("image_url") or None
