from astrbot.api.star import Context, Star, register
from astrbot.core.computer.computer_client import (
    cleanup_sandbox_provider,
    detach_sandbox_provider,
    register_sandbox_provider,
)

from .provider import ShipyardNeoSandboxProvider


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
        try:
            await cleanup_sandbox_provider(self.provider.provider_id)
        finally:
            detach_sandbox_provider(self.provider.provider_id)
