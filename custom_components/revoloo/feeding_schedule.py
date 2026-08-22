"""Sync a feeder's plans from a Home Assistant `schedule` helper entity.

The device's feeding-plan API (get/add/edit/delete_plan) has no day-of-week
concept: every plan is a single {time, quantity} pair that repeats every
day. A `schedule` helper is inherently weekly, so this flattens every day's
blocks that carry a `porties` data value into one shared daily plan list
and replaces whatever plans currently exist on the device. If different
days hold different blocks, that distinction is lost — the device cannot
represent it — so a warning is logged when that happens.
"""
from __future__ import annotations

import logging
from datetime import time as dt_time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api import RevolooApiClient
from .const import SCHEDULE_BLOCK_PORTIONS_KEY

_LOGGER = logging.getLogger(__name__)

_WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


async def async_sync_feeding_schedule(
    hass: HomeAssistant,
    client: RevolooApiClient,
    user_device_id: int,
    schedule_entity_id: str,
) -> None:
    """Replace a feeder's on-device plans with a schedule helper's blocks."""
    response = await hass.services.async_call(
        "schedule",
        "get_schedule",
        {"entity_id": schedule_entity_id},
        blocking=True,
        return_response=True,
    )
    schedule = (response or {}).get(schedule_entity_id, {})

    day_blocksets: list[set[tuple[str, int]]] = []
    for day in _WEEKDAYS:
        day_set: set[tuple[str, int]] = set()
        for block in schedule.get(day) or []:
            data = block.get("data") or {}
            portions = data.get(SCHEDULE_BLOCK_PORTIONS_KEY)
            if portions is None:
                continue
            from_value = block["from"]
            # get_schedule returns "from"/"to" as datetime.time objects on
            # some HA versions and as "HH:MM:SS" strings on others.
            if isinstance(from_value, dt_time):
                time_str = from_value.strftime("%H:%M")
            else:
                time_str = str(from_value)[:5]
            day_set.add((time_str, int(portions)))
        if day_set:
            day_blocksets.append(day_set)

    if not day_blocksets:
        raise HomeAssistantError(
            f"No blocks with a '{SCHEDULE_BLOCK_PORTIONS_KEY}' data value found "
            f"on {schedule_entity_id}"
        )

    merged: set[tuple[str, int]] = set().union(*day_blocksets)
    if any(day_set != merged for day_set in day_blocksets):
        _LOGGER.warning(
            "%s has different blocks on different days, but the feeder has no"
            " per-weekday plans — all of them will be merged into one"
            " daily-repeating schedule: %s",
            schedule_entity_id,
            sorted(merged),
        )

    existing_plans = await client.feeder_get_plans(user_device_id)
    for plan in existing_plans:
        await client.feeder_delete_plan(plan["plan_id"])
    for time_str, portions in sorted(merged):
        await client.feeder_add_plan(user_device_id, time_str, portions)
