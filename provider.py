from __future__ import annotations

import json
import os
import uuid
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.core.computer.booters.base import ComputerBooter
from astrbot.core.computer.sandbox_timeouts import resolve_sandbox_timeout
from astrbot.core.star.context import Context

from .booters import shipyard_neo as shipyard_neo_booter
from .booters.shipyard_neo import ShipyardNeoBooter
from .booters.shipyard_neo_endpoint import (
    is_shipyard_neo_auto_endpoint,
    normalize_shipyard_neo_endpoint,
)

BootHook = Callable[[Context, str, str, dict], Awaitable[ComputerBooter]]
_SHIPYARD_NEO_TTL_KEY = "sandbox_ttl"
_SHIPYARD_NEO_TTL_ALIASES = ("shipyard_neo_ttl",)
_SHIPYARD_NEO_DEFAULT_TTL_SECONDS = 3600
_SHIPYARD_NEO_IDLE_TIMEOUT_KEY = "sandbox_idle_timeout"
_SHIPYARD_NEO_IDLE_TIMEOUT_ALIASES = ("shipyard_neo_idle_timeout",)
_SHIPYARD_NEO_DEFAULT_IDLE_TIMEOUT_SECONDS = 0.0
DOCKER_UNAVAILABLE_ERROR = "Docker is not installed or not running"


def _is_docker_unavailable_error(exc: Exception) -> bool:
    detail = str(exc).lower()
    return (
        "cannot connect to docker engine" in detail
        or "failed to connect to docker daemon" in detail
        or DOCKER_UNAVAILABLE_ERROR.lower() in detail
        or ("cannot connect to unix socket" in detail and "docker.sock" in detail)
    )


def _discover_bay_credentials(endpoint: str) -> str:
    candidates: list[Path] = []
    bay_data_dir = os.environ.get("BAY_DATA_DIR")
    if bay_data_dir:
        candidates.append(Path(bay_data_dir) / "credentials.json")
    candidates.append(Path.cwd() / "credentials.json")
    for cred_path in candidates:
        if not cred_path.is_file():
            continue
        try:
            data = json.loads(cred_path.read_text(encoding="utf-8"))
            api_key = data.get("api_key", "")
            if api_key:
                return api_key
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("[Computer] Failed to read %s: %s", cred_path, exc)
    return ""


class ShipyardNeoSandboxProvider:
    provider_id = "shipyard_neo"
    capabilities = {"shell", "python", "filesystem", "browser"}
    supports_persistent_reconnect = True
    tool_names = {
        "astrbot_execute_browser",
        "astrbot_execute_browser_batch",
        "astrbot_run_browser_skill",
        "astrbot_get_execution_history",
        "astrbot_annotate_execution",
        "astrbot_create_skill_payload",
        "astrbot_get_skill_payload",
        "astrbot_create_skill_candidate",
        "astrbot_list_skill_candidates",
        "astrbot_evaluate_skill_candidate",
        "astrbot_promote_skill_candidate",
        "astrbot_list_skill_releases",
        "astrbot_rollback_skill_release",
        "astrbot_sync_skill_release",
    }

    def __init__(
        self,
        boot_hook: BootHook | None = None,
        *,
        plugin_config: Mapping[str, Any] | None = None,
    ) -> None:
        self.plugin_config: dict[str, Any] = (
            dict(plugin_config) if plugin_config is not None else {}
        )
        self._boot_hook = boot_hook

    @staticmethod
    def _persistent_name(config: dict, fallback: str) -> str:
        return str(config.get("persistent_name") or fallback).strip()

    def _merged_sandbox_config(self, context: Context, session_id: str) -> dict:
        """Return sandbox config with plugin_config as base and user settings overriding."""
        config = context.get_config(umo=session_id)
        merged = dict(self.plugin_config)
        sandbox_cfg = config.get("provider_settings", {}).get("sandbox", {})
        if isinstance(sandbox_cfg, dict):
            merged.update(sandbox_cfg)
        else:
            logger.warning(
                "[Computer] Expected dict for provider_settings.sandbox, got %s. Ignoring.",
                type(sandbox_cfg).__name__,
            )
        return merged

    def build_create_config(self, context: Context, session_id: str) -> dict:
        merged = self._merged_sandbox_config(context, session_id)
        raw_endpoint = merged.get("shipyard_neo_endpoint")
        if raw_endpoint is not None and not isinstance(raw_endpoint, str):
            raise TypeError("shipyard_neo_endpoint must be a string")
        endpoint = normalize_shipyard_neo_endpoint(
            raw_endpoint if isinstance(raw_endpoint, str) else None
        )
        raw_token = merged.get("shipyard_neo_access_token")
        if raw_token is not None and not isinstance(raw_token, str):
            raise TypeError("shipyard_neo_access_token must be a string")
        token = raw_token.strip() if isinstance(raw_token, str) else ""
        if not token and not is_shipyard_neo_auto_endpoint(endpoint):
            token = _discover_bay_credentials(endpoint)
        return {
            "endpoint_url": endpoint,
            "access_token": token,
            "profile": merged.get(
                "shipyard_neo_profile", ShipyardNeoBooter.DEFAULT_PROFILE
            ),
            "ttl": resolve_sandbox_timeout(
                merged,
                _SHIPYARD_NEO_TTL_KEY,
                aliases=_SHIPYARD_NEO_TTL_ALIASES,
                default=_SHIPYARD_NEO_DEFAULT_TTL_SECONDS,
            ),
        }

    def build_connect_info(self, sandbox_name: str, config: dict) -> dict:
        return {
            "name": sandbox_name,
            "endpoint_url": config.get("endpoint_url"),
            "profile": config.get("profile"),
            "persistent_name": self._persistent_name(config, sandbox_name),
            "sandbox_id": config.get("sandbox_id"),
        }

    def update_connect_info(self, record: dict, *, sandbox_name: str) -> dict:
        connect_info = dict(record.get("connect_info") or {})
        connect_info["name"] = sandbox_name
        connect_info["persistent_name"] = self._persistent_name(
            connect_info, sandbox_name
        )
        return connect_info

    def get_idle_timeout(self, context: Context, session_id: str) -> float:
        merged = self._merged_sandbox_config(context, session_id)
        return float(
            resolve_sandbox_timeout(
                merged,
                _SHIPYARD_NEO_IDLE_TIMEOUT_KEY,
                aliases=_SHIPYARD_NEO_IDLE_TIMEOUT_ALIASES,
                default=_SHIPYARD_NEO_DEFAULT_IDLE_TIMEOUT_SECONDS,
            )
        )

    async def check_persistent_sandbox_exists(self, record: dict) -> bool:
        connect_info = dict(record.get("connect_info") or {})
        sandbox_id = str(connect_info.get("sandbox_id") or "").strip()
        if not sandbox_id:
            return True

        endpoint_url = str(connect_info.get("endpoint_url") or "").strip()
        access_token = str(
            connect_info.get("access_token")
            or self.plugin_config.get("shipyard_neo_access_token")
            or ""
        ).strip()
        if not access_token:
            access_token = _discover_bay_credentials(endpoint_url)
        if not endpoint_url or not access_token:
            return True

        try:
            from shipyard_neo.errors import NotFoundError, SandboxExpiredError
        except ImportError:
            return True

        client_cls = getattr(shipyard_neo_booter, "BayClient", None)
        if client_cls is None:
            return True

        client = client_cls(
            endpoint_url=endpoint_url,
            access_token=access_token,
        )
        async with client:
            try:
                await client.get_sandbox(sandbox_id)
            except (NotFoundError, SandboxExpiredError):
                return False
        return True

    async def create_booter(
        self, context: Context, session_id: str, sandbox_id: str, config: dict
    ) -> ComputerBooter:
        if self._boot_hook is not None:
            return await self._boot_hook(context, session_id, sandbox_id, config)
        booter_config = {
            **{key: value for key, value in config.items() if key != "sandbox_id"},
            "persistent": True,
            "persistent_name": self._persistent_name(config, sandbox_id),
            "resume": bool(config.get("resume", False)),
            "existing_sandbox_id": config.get("sandbox_id"),
            "sandbox_id": sandbox_id,
        }
        client = ShipyardNeoBooter(
            **booter_config,
        )
        try:
            await client.boot(uuid.uuid5(uuid.NAMESPACE_DNS, session_id).hex)
        except RuntimeError as exc:
            if _is_docker_unavailable_error(exc):
                raise RuntimeError(DOCKER_UNAVAILABLE_ERROR) from exc
            raise
        return client

    async def destroy_booter(self, booter: ComputerBooter, record: dict) -> None:
        await booter.shutdown(delete_sandbox=True)
