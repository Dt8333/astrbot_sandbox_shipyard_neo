from types import SimpleNamespace

import pytest

from data.plugins.astrbot_sandbox_shipyard_neo import provider as provider_module


def test_shipyard_neo_provider_connect_info_tracks_sandbox_id():
    provider = provider_module.ShipyardNeoSandboxProvider()

    info = provider.build_connect_info(
        "Named",
        {
            "endpoint_url": "https://example.com",
            "profile": "python-default",
            "persistent_name": "neo-1",
            "sandbox_id": "sbx_123",
        },
    )

    assert info["persistent_name"] == "neo-1"
    assert info["sandbox_id"] == "sbx_123"


@pytest.mark.asyncio
async def test_shipyard_neo_provider_passes_reconnect_metadata(monkeypatch):
    recorded = {}

    class FakeBooter:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

        async def boot(self, session_id: str):
            recorded["boot_session_id"] = session_id

    monkeypatch.setattr(provider_module, "ShipyardNeoBooter", FakeBooter)

    provider = provider_module.ShipyardNeoSandboxProvider()
    booter = await provider.create_booter(
        context=SimpleNamespace(),
        session_id="dashboard",
        sandbox_id="neo-1",
        config={
            "endpoint_url": "https://example.com",
            "access_token": "token",
            "profile": "python-default",
            "ttl": 3600,
        },
    )

    assert recorded["persistent"] is True
    assert recorded["persistent_name"] == "neo-1"
    assert recorded["resume"] is False
    assert getattr(booter, "sandbox_id") == "neo-1"
