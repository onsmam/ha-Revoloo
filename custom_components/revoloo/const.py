"""Constants for the Revoloo (Notty Cat) integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "revoloo"

CONF_HZUID = "hzuid"

API_BASE_URL = "https://api.nottycat.com"
APP_ID = "1"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
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
