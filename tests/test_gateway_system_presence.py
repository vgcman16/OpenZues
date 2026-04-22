from __future__ import annotations

from dataclasses import dataclass

from openzues.services import gateway_system_presence as system_presence


@dataclass(slots=True)
class _FakeIdentity:
    id: str


class _FakeIdentityService:
    def __init__(self, *, device_id: str) -> None:
        self._identity = _FakeIdentity(id=device_id)

    def load(self) -> _FakeIdentity:
        return self._identity


@dataclass(slots=True)
class _FakeKnownNode:
    node_id: str
    connected: bool = True
    client_id: str | None = None
    client_mode: str | None = None
    display_name: str | None = None
    platform: str | None = None
    remote_ip: str | None = None
    version: str | None = None
    device_family: str | None = None
    model_identifier: str | None = None
    connected_at_ms: int | None = None


class _FakeRegistry:
    def __init__(self, nodes: list[_FakeKnownNode]) -> None:
        self._nodes = list(nodes)

    def list_known_nodes(self) -> list[_FakeKnownNode]:
        return list(self._nodes)


def _clear_package_version_cache() -> None:
    system_presence._package_version.cache_clear()


def test_gateway_system_presence_package_version_prefers_openzues_version_env(monkeypatch) -> None:
    monkeypatch.setattr(system_presence, "_runtime_package_version", lambda: "0.1.0-runtime")
    monkeypatch.setenv("OPENZUES_VERSION", "9.9.9-cli")
    monkeypatch.setenv("OPENZUES_SERVICE_VERSION", "2.4.6-service")
    monkeypatch.setenv("npm_package_version", "1.0.0-package")
    _clear_package_version_cache()

    try:
        assert system_presence._package_version() == "9.9.9-cli"
    finally:
        _clear_package_version_cache()


def test_gateway_system_presence_package_version_prefers_runtime_version_over_service_markers(
    monkeypatch,
) -> None:
    monkeypatch.setattr(system_presence, "_runtime_package_version", lambda: "0.1.0-runtime")
    monkeypatch.setenv("OPENZUES_VERSION", " ")
    monkeypatch.setenv("OPENZUES_SERVICE_VERSION", "2.4.6-service")
    monkeypatch.setenv("npm_package_version", "1.0.0-package")
    _clear_package_version_cache()

    try:
        assert system_presence._package_version() == "0.1.0-runtime"
    finally:
        _clear_package_version_cache()


def test_gateway_system_presence_self_entry_includes_gateway_metadata(monkeypatch) -> None:
    monkeypatch.setattr(system_presence, "_self_host", lambda: "gateway-host")
    monkeypatch.setattr(system_presence, "_self_ip", lambda host: "192.168.0.10")
    monkeypatch.setattr(system_presence, "_package_version", lambda: "0.1.0")
    monkeypatch.setattr(system_presence, "_self_platform", lambda: "windows 11")
    monkeypatch.setattr(system_presence, "_self_device_family", lambda: "Windows")
    monkeypatch.setattr(system_presence, "_self_model_identifier", lambda: "amd64")

    service = system_presence.GatewaySystemPresenceService(
        _FakeRegistry([]),
        gateway_identity_service=_FakeIdentityService(device_id="gateway-self"),
    )

    payload = service.build_snapshot(now_ms=1_700_000_000_000)

    assert payload == {
        "entries": [
            {
                "deviceId": "gateway-self",
                "instanceId": "gateway-self",
                "host": "gateway-host",
                "ip": "192.168.0.10",
                "version": "0.1.0",
                "platform": "windows 11",
                "deviceFamily": "Windows",
                "modelIdentifier": "amd64",
                "mode": "backend",
                "reason": "self",
                "roles": ["operator"],
                "scopes": [],
                "tags": ["gateway", "self"],
                "ts": 1_700_000_000_000,
                "text": "Gateway: gateway-host (192.168.0.10) \u00b7 app 0.1.0 \u00b7 mode backend \u00b7 reason self",
            }
        ]
    }


def test_gateway_system_presence_keeps_self_entry_sorted_before_connected_nodes(
    monkeypatch,
) -> None:
    monkeypatch.setattr(system_presence, "_self_host", lambda: "gateway-host")
    monkeypatch.setattr(system_presence, "_self_ip", lambda host: None)
    monkeypatch.setattr(system_presence, "_package_version", lambda: None)
    monkeypatch.setattr(system_presence, "_self_platform", lambda: None)
    monkeypatch.setattr(system_presence, "_self_device_family", lambda: None)
    monkeypatch.setattr(system_presence, "_self_model_identifier", lambda: None)

    service = system_presence.GatewaySystemPresenceService(
        _FakeRegistry(
            [
                _FakeKnownNode(
                    node_id="backend-7",
                    client_id="instance-7",
                    client_mode="desktop",
                    display_name="Managed Lane",
                    platform="desktop",
                    connected_at_ms=123,
                ),
                _FakeKnownNode(
                    node_id="node-1",
                    client_id="mobile-node-1",
                    client_mode="mobile",
                    display_name="Builder Phone",
                    platform="ios",
                    remote_ip="10.0.0.5",
                    version="1.2.3",
                    device_family="iphone",
                    model_identifier="iphone15,3",
                    connected_at_ms=456,
                ),
            ]
        ),
        gateway_identity_service=_FakeIdentityService(device_id="gateway-self"),
    )

    entries = service.build_snapshot(now_ms=1_700_000_000_000)["entries"]

    assert [entry["deviceId"] for entry in entries] == ["gateway-self", "node-1", "backend-7"]
    assert entries[0]["text"] == "Gateway: gateway-host \u00b7 mode backend \u00b7 reason self"


def test_gateway_system_presence_self_entry_falls_back_to_hostname_when_ip_lookup_fails(
    monkeypatch,
) -> None:
    def _raise_lookup_error(*_args, **_kwargs):
        raise OSError("uv_interface_addresses failed")

    monkeypatch.setattr(system_presence, "_self_host", lambda: "gateway-host")
    monkeypatch.setattr(system_presence.socket, "getaddrinfo", _raise_lookup_error)
    monkeypatch.setattr(system_presence, "_package_version", lambda: None)
    monkeypatch.setattr(system_presence, "_self_platform", lambda: None)
    monkeypatch.setattr(system_presence, "_self_device_family", lambda: None)
    monkeypatch.setattr(system_presence, "_self_model_identifier", lambda: None)

    service = system_presence.GatewaySystemPresenceService(
        _FakeRegistry([]),
        gateway_identity_service=_FakeIdentityService(device_id="gateway-self"),
    )

    payload = service.build_snapshot(now_ms=1_700_000_000_000)

    assert payload == {
        "entries": [
            {
                "deviceId": "gateway-self",
                "instanceId": "gateway-self",
                "host": "gateway-host",
                "ip": "gateway-host",
                "mode": "backend",
                "reason": "self",
                "roles": ["operator"],
                "scopes": [],
                "tags": ["gateway", "self"],
                "ts": 1_700_000_000_000,
                "text": "Gateway: gateway-host (gateway-host) \u00b7 mode backend \u00b7 reason self",
            }
        ]
    }
