from __future__ import annotations

import json
import os
import uuid
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from astrbot.api import logger
from astrbot.core.computer.booters.base import ComputerBooter
from astrbot.core.star.context import Context

from .booters.shipyard_neo import ShipyardNeoBooter

BootHook = Callable[[Context, str, str, dict], Awaitable[ComputerBooter]]


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
        "get_execution_history",
        "annotate_execution",
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
        endpoint = merged.get("shipyard_neo_endpoint", "")
        token = merged.get("shipyard_neo_access_token", "")
        if not token:
            token = _discover_bay_credentials(endpoint)
        return {
            "endpoint_url": endpoint,
            "access_token": token,
            "profile": merged.get("shipyard_neo_profile", "python-default"),
            "ttl": merged.get("shipyard_neo_ttl", 3600),
        }

    def build_connect_info(self, sandbox_name: str, config: dict) -> dict:
        return {
            "name": sandbox_name,
            "endpoint_url": config.get("endpoint_url"),
            "profile": config.get("profile"),
            "persistent_name": config.get("persistent_name") or sandbox_name,
            "sandbox_id": config.get("sandbox_id"),
        }

    def update_connect_info(self, record: dict, *, sandbox_name: str) -> dict:
        connect_info = dict(record.get("connect_info") or {})
        connect_info["name"] = sandbox_name
        return connect_info

    def get_idle_timeout(self, context: Context, session_id: str) -> float:
        return 0.0

    async def create_booter(
        self, context: Context, session_id: str, sandbox_id: str, config: dict
    ) -> ComputerBooter:
        if self._boot_hook is not None:
            return await self._boot_hook(context, session_id, sandbox_id, config)
        client = ShipyardNeoBooter(
            **config,
            persistent=True,
            persistent_name=str(config.get("persistent_name") or sandbox_id).strip(),
            resume=bool(config.get("resume", False)),
            existing_sandbox_id=config.get("sandbox_id"),
        )
        await client.boot(uuid.uuid5(uuid.NAMESPACE_DNS, session_id).hex)
        setattr(client, "sandbox_id", sandbox_id)
        return client

    async def destroy_booter(self, booter: ComputerBooter, record: dict) -> None:
        await booter.shutdown(delete_sandbox=True)
