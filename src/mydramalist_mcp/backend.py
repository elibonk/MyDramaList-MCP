"""SDK lifecycle, paced calls, authentication checks, and safe error results."""

import asyncio
import json
import time
from typing import Any

from curl_cffi.requests.exceptions import RequestException
from mdl import AsyncMDLClient, FileTokenStore, InMemoryTokenStore
from mdl._request import PreparedRequest
from mdl.errors import MDLNetworkError
from pydantic import BaseModel, ValidationError

from .catalog import Operation
from .config import Settings


class BackendError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


SENSITIVE_KEYS = {"access_token", "refresh_token", "token", "password", "authorization"}


def serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items() if k.lower() not in SENSITIVE_KEYS}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    return value


class Backend:
    def __init__(self, settings: Settings, client: Any = None):
        self.settings = settings
        if client is None:
            store = (
                InMemoryTokenStore(settings.access_token)
                if settings.access_token
                else FileTokenStore(settings.token_file)
            )
            client = AsyncMDLClient(token_store=store, timeout=settings.timeout)
        self.client = client
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def close(self) -> None:
        await self.client.aclose()

    def status(self) -> dict[str, Any]:
        return {
            "authenticated": bool(self.client.tokens.get_token()),
            "read_only": self.settings.read_only,
            "account_scope": "one configured MyDramaList account for all connected MCP clients",
            "client_version": "0.1.0",
            "authentication_note": (
                "A stored token is not proof it is valid. Use mdl_account_get_profile."
            ),
        }

    async def call(self, op: Operation, arguments: dict[str, Any]) -> Any:
        if op.write and self.settings.read_only:
            raise BackendError("read_only", "Writes are disabled by MDL_MCP_READ_ONLY.")
        async with self._lock:
            if op.private and not self.client.tokens.get_token():
                raise BackendError(
                    "authentication_required",
                    "Run mydramalist-mcp login on the host, "
                    "or configure MDL_ACCESS_TOKEN, then restart the server.",
                )
            delay = self.settings.request_interval - (time.monotonic() - self._last_call)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last_call = time.monotonic()
            try:
                # SDK 0.1.0 sends null for all omitted profile fields. Compact here to
                # preserve unrelated profile data on partial updates.
                if (op.group, op.method) == ("account", "update_profile_info"):
                    fields = {k: v for k, v in arguments.items() if v is not None}
                    if not fields:
                        raise BackendError(
                            "invalid_arguments", "Supply at least one profile field."
                        )
                    request = PreparedRequest(
                        "PATCH", "/users/settings", params={"setting": "account"}, json=fields
                    )
                    response = await self.client._transport.request(request)
                    return serialize(response.json if response.json is not None else response.text)
                method = getattr(getattr(self.client, op.group), op.method)
                return serialize(await method(**arguments))
            except MDLNetworkError as exc:
                messages = {
                    400: "MyDramaList rejected the request (400). Check fields, app version and "
                    "upstream API compatibility. The private API may have changed.",
                    401: "MyDramaList token expired or was rejected. It was cleared. Log in again "
                    "on the host and restart the server.",
                    403: "MyDramaList denied access (403). Check account permissions and upstream "
                    "transport compatibility.",
                    404: "MyDramaList resource or endpoint was not found (404).",
                    429: "MyDramaList rate limit reached (429). Wait before trying again.",
                }
                raise BackendError(
                    f"upstream_{exc.status_code}",
                    messages.get(exc.status_code, f"MyDramaList returned HTTP {exc.status_code}.")
                    + (
                        " No automatic retry was performed; check state before retrying a write."
                        if op.write
                        else ""
                    ),
                ) from None
            except (RequestException, TimeoutError, OSError):
                raise BackendError(
                    "transport_error",
                    "Could not reach MyDramaList. For writes, check current state before retrying.",
                ) from None
            except (ValidationError, json.JSONDecodeError):
                raise BackendError(
                    "upstream_schema_changed",
                    "MyDramaList response did not match "
                    "the client schema. Check the upstream package for an update. "
                    "For writes, check current state before retrying.",
                ) from None
