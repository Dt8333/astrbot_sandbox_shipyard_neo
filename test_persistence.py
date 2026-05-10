from types import SimpleNamespace

import pytest

from data.plugins.astrbot_sandbox_shipyard_neo import provider as provider_module
from data.plugins.astrbot_sandbox_shipyard_neo.booters import shipyard_neo


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


def test_shipyard_neo_provider_update_connect_info_preserves_existing_persistent_name():
    provider = provider_module.ShipyardNeoSandboxProvider()

    updated = provider.update_connect_info(
        {
            "connect_info": {
                "name": "Legacy",
                "persistent_name": "Original",
            }
        },
        sandbox_name="Renamed",
    )

    assert updated["name"] == "Renamed"
    assert updated["persistent_name"] == "Original"


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
    for key in ("ttl", "endpoint_url", "profile"):
        assert key in recorded
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


@pytest.mark.asyncio
async def test_shipyard_neo_auto_mode_generates_token_for_bay_and_client(monkeypatch):
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    recorded = {}

    class FakeBayManager:
        def __init__(self, *, access_token: str):
            recorded["manager_token"] = access_token

        async def ensure_running(self):
            return "http://127.0.0.1:8114"

        async def wait_healthy(self):
            return None

        async def read_credentials(self):
            raise AssertionError("random token should avoid reading credentials")

    class FakeSandbox:
        id = "sbx_generated"
        profile = "python-default"
        capabilities = []
        status = SimpleNamespace(value="ready")
        shell = SimpleNamespace()
        filesystem = SimpleNamespace()
        python = SimpleNamespace()

        async def refresh(self):
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeSandbox()

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )
    booter = ShipyardNeoBooter(endpoint_url="__auto__", access_token="")

    await booter.boot("ignored")

    assert recorded["manager_token"]
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": recorded["manager_token"],
    }


def test_shipyard_neo_provider_does_not_discover_credentials_for_auto_endpoint(
    monkeypatch,
):
    def fail_discovery(endpoint: str):
        raise AssertionError(f"should not discover credentials for {endpoint}")

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fail_discovery)

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {"provider_settings": {"sandbox": {}}}
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == provider_module.DEFAULT_SHIPYARD_NEO_ENDPOINT
    assert config["access_token"] == ""


def test_bay_manager_omits_empty_api_key_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="")

    assert all(
        env != "BAY_SECURITY__API_KEY=" for env in manager._build_container_env()
    )


def test_bay_manager_includes_api_key_env_when_token_is_configured():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")

    assert "BAY_SECURITY__API_KEY=token" in manager._build_container_env()


@pytest.mark.asyncio
async def test_shipyard_neo_provider_reports_persistent_sandbox_exists(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        async def __aenter__(self):
            calls.append("enter")
            return self

        async def __aexit__(self, exc_type, exc, tb):
            calls.append("exit")

        async def get_sandbox(self, sandbox_id: str):
            calls.append(("get", sandbox_id))
            return object()

    monkeypatch.setattr(shipyard_neo, "BayClient", FakeClient)

    provider = provider_module.ShipyardNeoSandboxProvider()

    exists = await provider.check_persistent_sandbox_exists(
        {
            "connect_info": {
                "endpoint_url": "https://example.com",
                "access_token": "token",
                "sandbox_id": "sbx_123",
            }
        }
    )

    assert exists is True
    assert calls == [
        ("init", {"endpoint_url": "https://example.com", "access_token": "token"}),
        "enter",
        ("get", "sbx_123"),
        "exit",
    ]


@pytest.mark.asyncio
async def test_shipyard_neo_provider_reports_missing_persistent_sandbox(monkeypatch):
    from shipyard_neo.errors import NotFoundError

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_sandbox(self, sandbox_id: str):
            raise NotFoundError()

    monkeypatch.setattr(shipyard_neo, "BayClient", lambda **kwargs: FakeClient())

    provider = provider_module.ShipyardNeoSandboxProvider()

    exists = await provider.check_persistent_sandbox_exists(
        {
            "connect_info": {
                "endpoint_url": "https://example.com",
                "access_token": "token",
                "sandbox_id": "sbx_123",
            }
        }
    )

    assert exists is False


@pytest.mark.asyncio
async def test_shipyard_neo_provider_uses_plugin_token_for_existence_check(
    monkeypatch,
):
    recorded = {}

    class FakeClient:
        def __init__(self, **kwargs):
            recorded.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_sandbox(self, sandbox_id: str):
            return object()

    monkeypatch.setattr(shipyard_neo, "BayClient", FakeClient)

    provider = provider_module.ShipyardNeoSandboxProvider(
        plugin_config={"shipyard_neo_access_token": "plugin-token"}
    )

    exists = await provider.check_persistent_sandbox_exists(
        {
            "connect_info": {
                "endpoint_url": "https://example.com",
                "sandbox_id": "sbx_123",
            }
        }
    )

    assert exists is True
    assert recorded["access_token"] == "plugin-token"
