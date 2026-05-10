from types import SimpleNamespace

import pytest

from data.plugins.astrbot_sandbox_shipyard_neo import provider as provider_module


def test_shipyard_neo_provider_connect_info_tracks_sandbox_id():
    provider = provider_module.ShipyardNeoSandboxProvider()
    assert (
        provider_module.ShipyardNeoSandboxProvider.supports_persistent_reconnect is True
    )

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


def test_shipyard_neo_provider_update_connect_info_populates_legacy_persistent_name():
    provider = provider_module.ShipyardNeoSandboxProvider()

    updated = provider.update_connect_info(
        {"connect_info": {"name": "Legacy"}},
        sandbox_name="Renamed",
    )

    assert updated["name"] == "Renamed"
    assert updated["persistent_name"] == "Renamed"


@pytest.mark.asyncio
async def test_shipyard_neo_provider_passes_reconnect_metadata(monkeypatch):
    recorded = {}

    class FakeBooter:
        def __init__(self, **kwargs):
            recorded.update(kwargs)
            self.sandbox_id = kwargs.get("sandbox_id")

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
    assert recorded["sandbox_id"] == "neo-1"
    assert getattr(booter, "sandbox_id") == "neo-1"


@pytest.mark.asyncio
async def test_shipyard_neo_provider_uses_config_overrides_without_keyword_conflicts(
    monkeypatch,
):
    recorded = {}

    class FakeBooter:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

        async def boot(self, session_id: str):
            recorded["boot_session_id"] = session_id

    monkeypatch.setattr(provider_module, "ShipyardNeoBooter", FakeBooter)

    provider = provider_module.ShipyardNeoSandboxProvider()
    await provider.create_booter(
        context=SimpleNamespace(),
        session_id="dashboard",
        sandbox_id="neo-2",
        config={
            "endpoint_url": "https://example.com",
            "access_token": "token",
            "profile": "python-default",
            "ttl": 3600,
            "persistent_name": " neo-custom ",
            "resume": True,
            "sandbox_id": "sbx_existing",
        },
    )

    assert recorded["persistent"] is True
    assert recorded["persistent_name"] == "neo-custom"
    assert recorded["resume"] is True
    assert recorded["existing_sandbox_id"] == "sbx_existing"


@pytest.mark.asyncio
async def test_shipyard_neo_booter_resume_falls_back_when_sandbox_missing(monkeypatch):
    from shipyard_neo.errors import NotFoundError

    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    recorded = []

    class FakeSandbox:
        def __init__(self, sandbox_id: str, profile: str = "python-default"):
            self.id = sandbox_id
            self.profile = profile
            self.capabilities = ["browser"]
            self.status = SimpleNamespace(value="ready")
            self.shell = SimpleNamespace()
            self.filesystem = SimpleNamespace()
            self.python = SimpleNamespace()
            self.browser = SimpleNamespace()

        async def refresh(self):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def get_sandbox(self, sandbox_id: str):
            raise NotFoundError()

        async def create_sandbox(self, *, profile: str, ttl: int):
            recorded.append(("create", profile, ttl))
            return FakeSandbox("new_sbx", profile)

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        lambda **kwargs: FakeClient(),
    )

    async def fake_resolve_profile(self, client):
        return "python-default"

    monkeypatch.setattr(ShipyardNeoBooter, "_resolve_profile", fake_resolve_profile)

    booter = ShipyardNeoBooter(
        endpoint_url="https://example.com",
        access_token="token",
        resume=True,
        existing_sandbox_id="stale_sbx",
        sandbox_id="neo-1",
    )

    await booter.boot("ignored")

    assert recorded == [("create", "python-default", 3600)]
