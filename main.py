import asyncio

from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.core.computer.computer_client import (
    cleanup_sandbox_provider,
    detach_sandbox_provider,
    register_sandbox_provider,
)
from astrbot.core.tools import registry as tool_registry

from .provider import ShipyardNeoSandboxProvider
from .tools.shipyard_neo import SHIPYARD_NEO_TOOL_MODULE_PREFIX


@register(
    "astrbot_sandbox_shipyard_neo",
    "AstrBot Team",
    "为 AstrBot 提供 Shipyard Neo 沙盒运行时。",
    "0.1.0",
)
class ShipyardNeoSandboxRuntimePlugin(Star):
    def __init__(self, context: Context, config=None) -> None:
        super().__init__(context)
        self.provider = ShipyardNeoSandboxProvider(plugin_config=config)
        register_sandbox_provider(
            self.provider,
            replace=True,
        )
        tool_registry.register_builtin_tools_by_module_prefix(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
        )

    async def terminate(self) -> None:
        provider = getattr(self, "provider", None)
        provider_id = getattr(provider, "provider_id", None) if provider else None
        try:
            if provider_id:
                await cleanup_sandbox_provider(provider_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(
                "Shipyard Neo sandbox provider cleanup failed during termination: provider=%s",
                provider_id,
                exc_info=True,
            )
            raise
        finally:
            if provider_id:
                _finalize_shipyard_neo_provider(
                    provider_id, getattr(self, "context", None)
                )


def _finalize_shipyard_neo_provider(provider_id: str, context: Context | None) -> None:
    detach_sandbox_provider(provider_id)
    _clear_shipyard_neo_builtin_tool_cache(context)
    try:
        removed = _unregister_shipyard_neo_builtin_tools()
    except Exception:
        logger.warning(
            "Shipyard Neo builtin tool cleanup failed during termination: provider=%s",
            provider_id,
            exc_info=True,
        )
    else:
        if removed:
            logger.info(
                "Unregistered %d builtin tool(s) for Shipyard Neo: %s",
                len(removed),
                ", ".join(removed),
            )


def _clear_shipyard_neo_builtin_tool_cache(context: Context | None) -> None:
    get_tool_manager = getattr(context, "get_llm_tool_manager", None)
    if not callable(get_tool_manager):
        logger.debug(
            "Skipping Shipyard Neo builtin tool cache clear: invalid or missing tool manager (context=%s, getter_type=%s)",
            type(context).__name__ if context is not None else "None",
            type(get_tool_manager).__name__,
        )
        return

    try:
        removed = get_tool_manager().clear_builtin_tool_cache_by_module_prefix(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
        )
    except Exception:
        logger.warning(
            "Shipyard Neo builtin tool cache cleanup failed during termination",
            exc_info=True,
        )
        return

    if removed:
        logger.info(
            "Cleared %d builtin tool cache entry(s) for Shipyard Neo: %s",
            len(removed),
            ", ".join(removed),
        )


def _unregister_shipyard_neo_builtin_tools() -> list[str]:
    removed = _unregister_shipyard_neo_builtin_tools_by_prefix_api()
    if removed is not None:
        return removed

    removed = _unregister_shipyard_neo_builtin_tools_via_public_iter_api()
    if removed is not None:
        return removed

    return _unregister_shipyard_neo_builtin_tools_via_legacy_private_caches()


def _unregister_shipyard_neo_builtin_tools_by_prefix_api() -> list[str] | None:
    unregister_by_prefix = getattr(
        tool_registry, "unregister_builtin_tools_by_module_prefix", None
    )
    if callable(unregister_by_prefix):
        return unregister_by_prefix(SHIPYARD_NEO_TOOL_MODULE_PREFIX)
    return None


def _unregister_shipyard_neo_builtin_tools_via_public_iter_api() -> list[str] | None:
    removed: list[str] = []
    iter_builtin_tool_classes = getattr(
        tool_registry, "iter_builtin_tool_classes", None
    )
    unregister_tool_class = getattr(
        tool_registry, "unregister_builtin_tool_class", None
    )
    if not (callable(iter_builtin_tool_classes) and callable(unregister_tool_class)):
        return None

    for tool_cls in tuple(iter_builtin_tool_classes()):
        if not getattr(tool_cls, "__module__", "").startswith(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
        ):
            continue
        tool_name = unregister_tool_class(tool_cls)
        if tool_name is not None:
            removed.append(tool_name)
    return removed


def _unregister_shipyard_neo_builtin_tools_via_legacy_private_caches() -> list[str]:
    removed: list[str] = []
    classes_by_name = getattr(tool_registry, "_builtin_tool_classes_by_name", None)
    names_by_class = getattr(tool_registry, "_builtin_tool_names_by_class", None)
    if not isinstance(classes_by_name, dict) or not isinstance(names_by_class, dict):
        logger.debug(
            "Shipyard Neo builtin tool unregister API is unavailable; skipping compatibility fallback"
        )
        return removed

    config_rules = getattr(tool_registry, "_BUILTIN_TOOL_CONFIG_RULES", None)
    for tool_name, tool_cls in list(classes_by_name.items()):
        if not getattr(tool_cls, "__module__", "").startswith(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
        ):
            continue
        classes_by_name.pop(tool_name, None)
        names_by_class.pop(tool_cls, None)
        if isinstance(config_rules, dict):
            config_rules.pop(tool_name, None)
        removed.append(tool_name)
    return removed
