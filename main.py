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
                detach_sandbox_provider(provider_id)
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


def _unregister_shipyard_neo_builtin_tools() -> list[str]:
    unregister = getattr(
        tool_registry, "unregister_builtin_tools_by_module_prefix", None
    )
    if callable(unregister):
        return unregister(SHIPYARD_NEO_TOOL_MODULE_PREFIX)

    logger.debug(
        "Falling back to manual Shipyard Neo builtin tool unregistration; "
        "tool_registry.unregister_builtin_tools_by_module_prefix is unavailable or not callable."
    )

    # The fallback below mutates tool_registry's private caches because older core
    # versions do not expose a public unregister helper. It assumes the internal
    # name->class and class->name mappings stay in sync with the config rule map.
    removed: list[str] = []
    classes_by_name = getattr(tool_registry, "_builtin_tool_classes_by_name", None)
    names_by_class = getattr(tool_registry, "_builtin_tool_names_by_class", None)
    config_rules = getattr(tool_registry, "_BUILTIN_TOOL_CONFIG_RULES", None)
    if not isinstance(classes_by_name, dict) or not isinstance(names_by_class, dict):
        logger.debug(
            "Skipping manual Shipyard Neo builtin tool unregistration because "
            "tool_registry private caches are missing or unexpected: classes_by_name=%s names_by_class=%s config_rules=%s",
            type(classes_by_name).__name__,
            type(names_by_class).__name__,
            type(config_rules).__name__,
        )
        return removed

    for tool_cls in list(names_by_class):
        if not getattr(tool_cls, "__module__", "").startswith(
            SHIPYARD_NEO_TOOL_MODULE_PREFIX
        ):
            continue
        tool_name = names_by_class.pop(tool_cls, None)
        if not tool_name:
            continue
        if classes_by_name.get(tool_name) is tool_cls:
            classes_by_name.pop(tool_name, None)
        if isinstance(config_rules, dict):
            config_rules.pop(tool_name, None)
        removed.append(tool_name)
    return removed
