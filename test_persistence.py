import json
from types import SimpleNamespace

import pytest

from data.plugins.astrbot_sandbox_shipyard_neo import main as plugin_main
from data.plugins.astrbot_sandbox_shipyard_neo import provider as provider_module
from data.plugins.astrbot_sandbox_shipyard_neo.booters import shipyard_neo
from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo_endpoint import (
    DEFAULT_SHIPYARD_NEO_ENDPOINT,
    SHIPYARD_NEO_AUTO_ENDPOINT,
    is_shipyard_neo_auto_endpoint,
    normalize_shipyard_neo_endpoint,
)


class FakeReadySandbox:
    def __init__(
        self,
        sandbox_id: str = "sbx_fake",
        profile: str = "python-default",
        capabilities: list[str] | None = None,
    ):
        self.id = sandbox_id
        self.profile = profile
        self.capabilities = [] if capabilities is None else capabilities
        self.status = SimpleNamespace(value="ready")
        self.shell = SimpleNamespace()
        self.filesystem = SimpleNamespace()
        self.python = SimpleNamespace()
        self.browser = SimpleNamespace()

    async def refresh(self):
        return None


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


def test_shipyard_neo_provider_defaults_to_local_endpoint_when_unconfigured():
    provider = provider_module.ShipyardNeoSandboxProvider()

    config = provider.build_create_config(
        SimpleNamespace(get_config=lambda umo: {"provider_settings": {"sandbox": {}}}),
        "dashboard",
    )

    assert config["endpoint_url"] == DEFAULT_SHIPYARD_NEO_ENDPOINT
    assert config["access_token"] == ""


@pytest.mark.parametrize(
    "endpoint_value, expected_endpoint, expected_auto",
    [
        ("http://localhost:8114", DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("http://127.0.0.1:8114/", DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("https://127.0.0.1:8114", "https://127.0.0.1:8114", False),
        ("http://127.0.0.1:9000", "http://127.0.0.1:9000", False),
    ],
)
def test_shipyard_neo_provider_normalizes_localhost_and_rejects_non_auto_endpoints(
    endpoint_value,
    expected_endpoint,
    expected_auto,
    monkeypatch,
):
    discovered: list[str] = []

    def fake_discover(endpoint: str) -> str:
        discovered.append(endpoint)
        return "discovered-token"

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fake_discover)
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": endpoint_value,
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == expected_endpoint
    assert config["access_token"] == ("" if expected_auto else "discovered-token")
    assert discovered == ([] if expected_auto else [expected_endpoint])
    assert is_shipyard_neo_auto_endpoint(config["endpoint_url"]) is expected_auto


@pytest.mark.parametrize(
    "endpoint_value, expected_endpoint, expected_auto",
    [
        (None, DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        (SHIPYARD_NEO_AUTO_ENDPOINT, DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        (" http://localhost:8114/ ", DEFAULT_SHIPYARD_NEO_ENDPOINT, True),
        ("http://127.0.0.1:9000", "http://127.0.0.1:9000", False),
    ],
)
def test_shipyard_neo_endpoint_helper_centralizes_normalization(
    endpoint_value, expected_endpoint, expected_auto
):
    normalized = normalize_shipyard_neo_endpoint(endpoint_value)

    assert normalized == expected_endpoint
    assert is_shipyard_neo_auto_endpoint(normalized) is expected_auto


@pytest.mark.asyncio
async def test_shipyard_neo_terminate_detaches_even_if_cleanup_fails(monkeypatch):
    calls = []

    class FakeProvider:
        provider_id = "shipyard_neo"

    async def fake_cleanup(provider_id):
        calls.append(("cleanup", provider_id))
        raise RuntimeError("cleanup failed")

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    monkeypatch.setattr(plugin_main, "cleanup_sandbox_provider", fake_cleanup)
    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)

    plugin = plugin_main.ShipyardNeoSandboxRuntimePlugin.__new__(
        plugin_main.ShipyardNeoSandboxRuntimePlugin
    )
    plugin.provider = FakeProvider()

    with pytest.raises(RuntimeError, match="cleanup failed"):
        await plugin.terminate()

    assert calls == [("cleanup", "shipyard_neo"), ("detach", "shipyard_neo")]


@pytest.mark.asyncio
async def test_shipyard_neo_terminate_detaches_on_successful_cleanup(monkeypatch):
    calls = []

    class FakeProvider:
        provider_id = "shipyard_neo"

    async def fake_cleanup(provider_id):
        calls.append(("cleanup", provider_id))

    def fake_detach(provider_id):
        calls.append(("detach", provider_id))

    monkeypatch.setattr(plugin_main, "cleanup_sandbox_provider", fake_cleanup)
    monkeypatch.setattr(plugin_main, "detach_sandbox_provider", fake_detach)

    plugin = plugin_main.ShipyardNeoSandboxRuntimePlugin.__new__(
        plugin_main.ShipyardNeoSandboxRuntimePlugin
    )
    plugin.provider = FakeProvider()

    await plugin.terminate()

    assert calls == [("cleanup", "shipyard_neo"), ("detach", "shipyard_neo")]


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

    class FakeClient:
        async def __aenter__(self):
            return self

        async def get_sandbox(self, sandbox_id: str):
            raise NotFoundError()

        async def create_sandbox(self, *, profile: str, ttl: int):
            recorded.append(("create", profile, ttl))
            return FakeReadySandbox("new_sbx", profile, capabilities=["browser"])

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
        SHIPYARD_NEO_AUTO_ENDPOINT,
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

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeReadySandbox("sbx_generated")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )
    booter = ShipyardNeoBooter(
        endpoint_url=SHIPYARD_NEO_AUTO_ENDPOINT,
        access_token="",
    )

    await booter.boot("ignored")

    assert recorded["manager_token"]
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": recorded["manager_token"],
    }


@pytest.mark.asyncio
async def test_shipyard_neo_local_default_triggers_auto_start(monkeypatch):
    recorded = {}

    class FakeBayManager:
        def __init__(self, *, access_token: str):
            recorded["manager_token"] = access_token

        async def ensure_running(self):
            return "http://127.0.0.1:8114"

        async def wait_healthy(self):
            return None

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            del profile, ttl
            return FakeReadySandbox("sbx_local_default")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )

    booter = shipyard_neo.ShipyardNeoBooter(
        endpoint_url=DEFAULT_SHIPYARD_NEO_ENDPOINT,
        access_token="",
    )

    await booter.boot("ignored")

    assert recorded["manager_token"]
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": recorded["manager_token"],
    }


@pytest.mark.asyncio
async def test_shipyard_neo_auto_mode_reuses_configured_token(monkeypatch):
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        SHIPYARD_NEO_AUTO_ENDPOINT,
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
            raise AssertionError("configured token should avoid reading credentials")

    class FakeClient:
        def __init__(self, **kwargs):
            recorded["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeReadySandbox("sbx_configured")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager.BayContainerManager",
        FakeBayManager,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        FakeClient,
    )
    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.secrets.token_urlsafe",
        lambda n: (_ for _ in ()).throw(AssertionError("token should be reused")),
    )

    booter = ShipyardNeoBooter(
        endpoint_url=SHIPYARD_NEO_AUTO_ENDPOINT,
        access_token="configured-token",
    )

    await booter.boot("ignored")

    assert recorded["manager_token"] == "configured-token"
    assert recorded["client_kwargs"] == {
        "endpoint_url": "http://127.0.0.1:8114",
        "access_token": "configured-token",
    }


@pytest.mark.parametrize(
    "endpoint_value, access_token, expected_endpoint, expected_token",
    [
        (None, "", DEFAULT_SHIPYARD_NEO_ENDPOINT, ""),
        (
            SHIPYARD_NEO_AUTO_ENDPOINT,
            "",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "",
        ),
        ("   ", "", DEFAULT_SHIPYARD_NEO_ENDPOINT, ""),
        (
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "",
        ),
        (
            SHIPYARD_NEO_AUTO_ENDPOINT,
            "pre-configured-token",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "pre-configured-token",
        ),
        (
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "pre-configured-token",
            DEFAULT_SHIPYARD_NEO_ENDPOINT,
            "pre-configured-token",
        ),
    ],
)
def test_shipyard_neo_provider_auto_like_endpoints_do_not_trigger_discovery(
    monkeypatch,
    endpoint_value,
    access_token,
    expected_endpoint,
    expected_token,
):
    def fail_discovery(endpoint: str):
        raise AssertionError(f"should not discover credentials for {endpoint}")

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fail_discovery)

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": endpoint_value,
                    "shipyard_neo_access_token": access_token,
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == expected_endpoint
    assert config["access_token"] == expected_token


def test_shipyard_neo_provider_rejects_non_string_endpoint():
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": {"url": "http://127.0.0.1:8114"},
                }
            }
        }
    )

    with pytest.raises(TypeError, match="shipyard_neo_endpoint must be a string"):
        provider.build_create_config(context, "dashboard")


def test_shipyard_neo_provider_discovers_credentials_for_non_auto_endpoint(
    monkeypatch,
):
    recorded = {}

    def fake_discover_bay_credentials(endpoint: str) -> str:
        recorded["endpoint"] = endpoint
        return "discovered-token"

    monkeypatch.setattr(
        provider_module,
        "_discover_bay_credentials",
        fake_discover_bay_credentials,
    )

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": " https://bay.example.com ",
                    "shipyard_neo_access_token": "",
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert recorded["endpoint"] == "https://bay.example.com"
    assert config["endpoint_url"] == "https://bay.example.com"
    assert config["access_token"] == "discovered-token"


def test_shipyard_neo_provider_rejects_non_string_access_token():
    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_access_token": {"token": "secret"},
                }
            }
        }
    )

    with pytest.raises(TypeError, match="shipyard_neo_access_token must be a string"):
        provider.build_create_config(context, "dashboard")


def test_shipyard_neo_provider_strips_access_token_without_discovery(monkeypatch):
    def fail_discovery(endpoint: str):
        raise AssertionError(f"should not discover credentials for {endpoint}")

    monkeypatch.setattr(provider_module, "_discover_bay_credentials", fail_discovery)

    provider = provider_module.ShipyardNeoSandboxProvider()
    context = SimpleNamespace(
        get_config=lambda umo: {
            "provider_settings": {
                "sandbox": {
                    "shipyard_neo_endpoint": " https://bay.example.com ",
                    "shipyard_neo_access_token": " configured-token ",
                }
            }
        }
    )

    config = provider.build_create_config(context, "dashboard")

    assert config["endpoint_url"] == "https://bay.example.com"
    assert config["access_token"] == "configured-token"


def _assert_core_bay_env(env: list[str]) -> None:
    assert "BAY_SECURITY__ALLOW_ANONYMOUS=false" in env
    assert "BAY_DATA_DIR=/app/data" in env
    assert any(entry.startswith("BAY_SERVER__HOST=") for entry in env)
    assert any(entry.startswith("BAY_SERVER__PORT=") for entry in env)


def test_bay_manager_omits_empty_api_key_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="")
    env = manager.build_container_env()

    _assert_core_bay_env(env)
    assert all(not entry.startswith("BAY_SECURITY__API_KEY=") for entry in env)


def test_bay_manager_includes_api_key_env_when_token_is_configured():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")
    env = manager.build_container_env()

    _assert_core_bay_env(env)
    assert "BAY_SECURITY__API_KEY=token" in env


def test_bay_manager_configures_pullable_default_profile_image():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        DEFAULT_SHIP_RUNTIME_IMAGE,
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")
    env = manager.build_container_env()
    profiles_env = next(item for item in env if item.startswith("BAY_PROFILES="))

    profiles = json.loads(profiles_env.removeprefix("BAY_PROFILES="))

    assert profiles[0]["id"] == "python-default"
    assert profiles[0]["image"] == DEFAULT_SHIP_RUNTIME_IMAGE
    assert profiles[0]["resources"] == {"cpus": 1.0, "memory": "1g"}
    assert profiles[0]["capabilities"] == ["filesystem", "shell", "python"]
    assert profiles[0]["idle_timeout"] == 1800


def test_bay_manager_detects_mismatched_existing_container_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")

    assert manager.container_env_matches({"Config": {"Env": []}}) is False


def test_bay_manager_accepts_matching_existing_container_env():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="token")

    assert (
        manager.container_env_matches(
            {"Config": {"Env": manager.build_container_env()}}
        )
        is True
    )


def test_bay_manager_matches_without_access_token():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="")
    env = manager.build_container_env()

    assert "BAY_SECURITY__API_KEY=" not in env
    assert manager.container_env_matches({"Config": {"Env": env}}) is True


def test_bay_manager_rejects_different_api_key():
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.bay_manager import (
        BayContainerManager,
    )

    manager = BayContainerManager(access_token="new-token")
    desired_env = manager.build_container_env()

    # Simulate an existing container with an old API key
    stale_env = [
        item for item in desired_env if not item.startswith("BAY_SECURITY__API_KEY=")
    ]
    stale_env.append("BAY_SECURITY__API_KEY=old-token")

    assert manager.container_env_matches({"Config": {"Env": stale_env}}) is False


@pytest.mark.asyncio
async def test_shipyard_neo_boot_closes_client_when_readiness_fails(monkeypatch):
    from data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo import (
        ShipyardNeoBooter,
    )

    calls = []

    class FakeClient:
        async def __aenter__(self):
            calls.append("enter")
            return self

        async def __aexit__(self, exc_type, exc, tb):
            calls.append(("exit", exc_type, exc))

        async def list_profiles(self):
            return SimpleNamespace(items=[])

        async def create_sandbox(self, *, profile: str, ttl: int):
            return FakeReadySandbox("failed_sbx")

    monkeypatch.setattr(
        "data.plugins.astrbot_sandbox_shipyard_neo.booters.shipyard_neo.BayClient",
        lambda **kwargs: FakeClient(),
    )

    async def fail_readiness(self, sandbox):
        raise RuntimeError("sandbox failed")

    monkeypatch.setattr(ShipyardNeoBooter, "_wait_until_ready", fail_readiness)

    booter = ShipyardNeoBooter(
        endpoint_url="https://example.com",
        access_token="token",
    )

    with pytest.raises(RuntimeError, match="sandbox failed"):
        await booter.boot("ignored")

    assert calls[0] == "enter"
    exit_call = calls[1]
    assert exit_call[0] == "exit"
    assert exit_call[1] is RuntimeError
    assert isinstance(exit_call[2], RuntimeError)
    assert str(exit_call[2]) == "sandbox failed"
    assert booter.bay_client is None


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
