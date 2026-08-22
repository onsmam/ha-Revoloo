"""Constants for the Revoloo (Notty Cat) integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "revoloo"

CONF_HZUID = "hzuid"

API_BASE_URL = "https://api.nottycat.com"
APP_ID = "1"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=10)
MIN_SCAN_INTERVAL = timedelta(seconds=15)
CONF_SCAN_INTERVAL = "scan_interval"

# Static app version headers copied from the captured Notty Cat app traffic.
# The backend does not appear to validate these beyond requiring their presence.
USER_AGENT = "Dart/3.7 (dart:io)"
APP_VERSION_HEADER = "4.1.0;android;6.0.1;default;A001"

# device_id -> API path segment. The get_user_devices endpoint returns a flat
# schema shared by all device types (wd_*, f_*, lb_* fields on every row) and
# does not expose a type string, so the app relies on this fixed device_id
# mapping to know which endpoints/fields apply to a given device.
DEVICE_TYPE_LITTER_BOX = "litter_box"
DEVICE_TYPE_WATER_DISPENSER = "water_dispenser"
DEVICE_TYPE_FEEDER = "feeder"

DEVICE_ID_TYPE_MAP = {
    2: DEVICE_TYPE_LITTER_BOX,
    3: DEVICE_TYPE_WATER_DISPENSER,
    4: DEVICE_TYPE_FEEDER,
}

LITTER_BOX_MODES = {
    1: "auto",
    2: "schedule",
    3: "smart",
}

WATER_DISPENSER_MODES = {
    0: "off",
    1: "continuous",
    2: "interval",
}

MANUFACTURER = "Notty Cat"

# The only "action" value ever observed for the litter/garbage-bag reminder
# reset calls; it both reconfigures the reminder cycle length and resets the
# remaining-days countdown to it. Other action codes are not known.
REMINDER_RESET_ACTION = 3

# litter_box/one_key "one_key" values. 1 was captured directly (manual
# clean). 2 and 3 are the device owner's own best guess from the app's UI,
# not captured traffic — LITTER_BOX_ONE_KEY_EMPTY is intentionally unused
# for now pending their confirmation.
LITTER_BOX_ONE_KEY_CLEAN = 1
LITTER_BOX_ONE_KEY_EMPTY = 2
LITTER_BOX_ONE_KEY_SMOOTH = 3

# Options-flow key prefix for "which `schedule.*` helper feeds this feeder's
# plans", keyed per feeder user_device_id since an account could have more
# than one feeder.
FEEDER_SCHEDULE_ENTITY_PREFIX = "feeder_schedule_entity_"

# Custom data key the device owner puts on schedule-helper blocks to carry
# the portion count for that block (see feeding_schedule.py).
SCHEDULE_BLOCK_PORTIONS_KEY = "porties"
