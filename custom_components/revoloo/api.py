"""Thin async client for the Notty Cat / Revoloo cloud API.

Reverse engineered from a mitmproxy capture of the official app traffic.
There is no known token refresh or login flow, so the bearer token and the
`hzuid` header value are supplied by the user and used as-is on every call.
"""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    API_BASE_URL,
    APP_ID,
    APP_VERSION_HEADER,
    REMINDER_RESET_ACTION,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = ClientTimeout(total=20)


class RevolooApiError(Exception):
    """Raised on any API/backend error."""


class RevolooAuthError(RevolooApiError):
    """Raised when the token/hzuid pair is rejected by the backend."""


class RevolooApiClient:
    """Client for the api.nottycat.com REST API used by the Revoloo devices."""

    def __init__(
        self,
        session: ClientSession,
        token: str,
        hzuid: str,
        time_zone: str = "UTC",
    ) -> None:
        self._session = session
        self._token = token
        self._hzuid = hzuid
        self._time_zone = time_zone

    def _headers(self) -> dict[str, str]:
        return {
            "authorization": self._token,
            "hzuid": self._hzuid,
            "content-type": "application/json",
            "accept": "application/json, text/plain, */*",
            "xjiang-language": "en",
            "time_zone": self._time_zone,
            "user-agent": USER_AGENT,
            "user-aagent": APP_VERSION_HEADER,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{API_BASE_URL}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json_body,
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise RevolooAuthError(
                        f"Authentication rejected by API ({resp.status})"
                    )
                if resp.status >= 400:
                    text = await resp.text()
                    raise RevolooApiError(
                        f"Unexpected status {resp.status} for {path}: {text[:200]}"
                    )
                payload: dict[str, Any] = await resp.json(content_type=None)
        except ClientError as err:
            raise RevolooApiError(f"Connection error calling {path}: {err}") from err

        if not payload.get("success", False):
            code = payload.get("code")
            message = payload.get("message", "")
            if code in (401, 403):
                raise RevolooAuthError(message or "Authentication rejected")
            raise RevolooApiError(f"API returned an error for {path}: {message}")

        return payload

    # -- Account -----------------------------------------------------------

    async def verify_token(self) -> dict[str, Any]:
        return await self._request("GET", "/account/verify_token")

    async def user_info(self) -> dict[str, Any]:
        return await self._request("GET", "/user/info")

    # -- Devices & pets ------------------------------------------------------

    async def get_user_devices(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", f"/device/get_user_devices/{APP_ID}")
        return payload.get("data", [])

    async def get_info(self, device_type: str, user_device_id: int) -> dict[str, Any]:
        payload = await self._request(
            "GET", f"/device/{device_type}/get_info/{user_device_id}"
        )
        return payload.get("data", {})

    async def pet_data_list(
        self, device_type: str, user_device_id: int
    ) -> list[dict[str, Any]]:
        payload = await self._request(
            "GET", f"/device/{device_type}/pet_data_list/{user_device_id}"
        )
        return payload.get("data", [])

    async def check_upgrade(self, user_device_id: int) -> dict[str, Any]:
        payload = await self._request(
            "GET", f"/device/check_upgrade/{user_device_id}"
        )
        return payload.get("data", {})

    async def pet_list(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/pet/list")
        return payload.get("data", [])

    # -- Litter box controls -------------------------------------------------

    async def litter_box_one_key(self, user_device_id: int, one_key: int = 1) -> None:
        await self._request(
            "POST",
            "/device/litter_box/one_key",
            json_body={"user_device_id": user_device_id, "one_key": one_key},
        )

    async def litter_box_set_auto_delay(self, user_device_id: int, delay: int) -> None:
        await self._request(
            "POST",
            "/device/litter_box/set_auto_delay",
            json_body={"user_device_id": user_device_id, "delay": delay},
        )

    async def litter_box_set_mode(self, user_device_id: int, mode: int) -> None:
        await self._request(
            "POST",
            "/device/litter_box/set_mode",
            json_body={"user_device_id": user_device_id, "mode": mode},
        )

    async def litter_box_set_key(self, user_device_id: int, enabled: bool) -> None:
        await self._request(
            "POST",
            "/device/litter_box/set_key",
            json_body={"user_device_id": user_device_id, "switch": 1 if enabled else 0},
        )

    async def litter_box_set_litter_remind(
        self, user_device_id: int, cycle_time: int
    ) -> None:
        await self._request(
            "POST",
            "/device/litter_box/set_litter_remind",
            json_body={
                "user_device_id": user_device_id,
                "action": REMINDER_RESET_ACTION,
                "cycle_time": cycle_time,
            },
        )

    async def litter_box_set_garbage_bag_remind(
        self, user_device_id: int, cycle_time: int
    ) -> None:
        await self._request(
            "POST",
            "/device/litter_box/set_garbage_bag_remind",
            json_body={
                "user_device_id": user_device_id,
                "action": REMINDER_RESET_ACTION,
                "cycle_time": cycle_time,
            },
        )

    # -- Water dispenser controls --------------------------------------------

    async def water_dispenser_change_mode(
        self, user_device_id: int, mode: int
    ) -> None:
        await self._request(
            "POST",
            "/device/water_dispenser/change_mode",
            json_body={"user_device_id": user_device_id, "mode": mode},
        )

    async def water_dispenser_set_uvc(
        self, user_device_id: int, uvc_switch: bool
    ) -> None:
        await self._request(
            "POST",
            "/device/water_dispenser/uvc",
            json_body={
                "user_device_id": user_device_id,
                "uvc_switch": 1 if uvc_switch else 0,
            },
        )

    async def water_dispenser_reset_filter(self, user_device_id: int) -> None:
        await self._request(
            "POST",
            "/device/water_dispenser/set_filter",
            json_body={"user_device_id": user_device_id, "action": 3},
        )

    async def water_dispenser_sterilize(self, user_device_id: int) -> None:
        await self._request(
            "POST",
            "/device/water_dispenser/sterilize",
            json_body={"user_device_id": user_device_id},
        )

    async def water_dispenser_set_led(
        self,
        user_device_id: int,
        led: bool,
        dnd_begin_time: str = "",
        dnd_end_time: str = "",
    ) -> None:
        await self._request(
            "POST",
            "/device/water_dispenser/set_led",
            json_body={
                "user_device_id": user_device_id,
                "led": 1 if led else 0,
                "dnd_begin_time": dnd_begin_time,
                "dnd_end_time": dnd_end_time,
            },
        )

    # -- Feeder controls ------------------------------------------------------

    async def feeder_one_key(self, user_device_id: int, qty: int = 1) -> None:
        await self._request(
            "POST",
            "/device/feeder/one_key",
            json_body={"user_device_id": user_device_id, "qty": qty},
        )

    async def feeder_set_desiccant_reminder(
        self, user_device_id: int, enabled: bool
    ) -> None:
        await self._request(
            "POST",
            "/device/feeder/set_desiccant",
            json_body={"user_device_id": user_device_id, "action": 1 if enabled else 2},
        )

    async def feeder_reset_desiccant(self, user_device_id: int) -> None:
        await self._request(
            "POST",
            "/device/feeder/set_desiccant",
            json_body={"user_device_id": user_device_id, "action": 3},
        )

    async def feeder_set_lock(self, user_device_id: int, enabled: bool) -> None:
        await self._request(
            "POST",
            "/device/feeder/set_lock",
            json_body={"user_device_id": user_device_id, "lock": 1 if enabled else 2},
        )

    async def feeder_set_led(
        self,
        user_device_id: int,
        led: bool,
        dnd_begin_time: str = "",
        dnd_end_time: str = "",
    ) -> None:
        await self._request(
            "POST",
            "/device/feeder/set_led",
            json_body={
                "user_device_id": user_device_id,
                "led": 1 if led else 0,
                "dnd_begin_time": dnd_begin_time,
                "dnd_end_time": dnd_end_time,
            },
        )
