from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime

import pytest

from openzues.database import Database
from openzues.schemas import ConversationTargetView, NotificationRouteView
from openzues.services.gateway_channels import GatewayChannelsService
from openzues.services.gateway_config import GatewayConfigService
from openzues.services.gateway_health import GatewayHealthService
from openzues.services.gateway_identity import GatewayIdentityService
from openzues.services.gateway_node_methods import (
    GatewayNodeMethodError,
    GatewayNodeMethodRequester,
    GatewayNodeMethodService,
)
from openzues.services.gateway_node_pairing import GatewayNodePairingService
from openzues.services.gateway_node_registry import (
    GatewayNodeConnect,
    GatewayNodeRegistry,
    KnownNode,
)
from openzues.services.gateway_skill_bins import GatewaySkillBinsService
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.hub import BroadcastHub


class FakeNodeConnection:
    def __init__(self, conn_id: str) -> None:
        self.conn_id = conn_id
        self.sent_events: list[dict[str, object | None]] = []

    def send_gateway_event(self, event: str, payload: object) -> None:
        self.sent_events.append({"event": event, "payload": payload})


class AutoReplyNodeConnection(FakeNodeConnection):
    def __init__(self, registry: GatewayNodeRegistry, conn_id: str) -> None:
        super().__init__(conn_id)
        self.registry = registry

    def send_gateway_event(self, event: str, payload: object) -> None:
        super().send_gateway_event(event, payload)
        if event != "node.invoke.request" or not isinstance(payload, dict):
            return
        request_id = str(payload.get("id") or "")
        node_id = str(payload.get("nodeId") or "")
        if not request_id or not node_id:
            return
        asyncio.get_running_loop().call_soon(
            lambda: self.registry.handle_invoke_result(
                request_id=request_id,
                node_id=node_id,
                ok=True,
                payload={"status": "done"},
                payload_json='{"status":"done"}',
                error=None,
            )
        )


def _register_ios_node(registry: GatewayNodeRegistry) -> None:
    registry.remember(
        KnownNode(
            node_id="node-1",
            display_name="Builder Phone",
            platform="ios",
            version="1.2.3",
            core_version="2.0.0",
            ui_version="3.0.0",
            client_id="saved-node-1",
            client_mode="mobile",
            device_family="iphone",
            model_identifier="iphone15,3",
            path_env="/workspace",
            caps=("voice", "canvas"),
            commands=("canvas.present",),
            permissions={"operator.read": True},
            paired=True,
            connected=False,
            approved_at_ms=99,
        )
    )
    registry.register(
        FakeNodeConnection("conn-node-1"),
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            client_mode="mobile",
            display_name="Builder Phone",
            platform="ios",
            version="1.2.3",
            core_version="2.0.0",
            ui_version="3.0.0",
            device_family="iphone",
            model_identifier="iphone15,3",
            caps=("voice", "canvas"),
            commands=("canvas.present",),
            permissions={"operator.read": True},
            path_env="/workspace",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=321,
    )


@pytest.mark.asyncio
async def test_node_methods_surface_openclaw_shaped_list_and_describe_payloads() -> None:
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    service = GatewayNodeMethodService(registry)

    listed = await service.call("node.list", {}, now_ms=1234)
    described = await service.call("node.describe", {"nodeId": "node-1"}, now_ms=1234)

    assert listed == {
        "ts": 1234,
        "nodes": [
            {
                "nodeId": "node-1",
                "displayName": "Builder Phone",
                "platform": "ios",
                "version": "1.2.3",
                "coreVersion": "2.0.0",
                "uiVersion": "3.0.0",
                "clientId": "live-node-1",
                "clientMode": "mobile",
                "remoteIp": "10.0.0.5",
                "deviceFamily": "iphone",
                "modelIdentifier": "iphone15,3",
                "pathEnv": "/workspace",
                "caps": ["canvas", "voice"],
                "commands": ["canvas.present"],
                "permissions": {"operator.read": True},
                "paired": True,
                "connected": True,
                "connectedAtMs": 321,
                "approvedAtMs": 99,
            }
        ],
    }
    assert described == {
        "ts": 1234,
        "nodeId": "node-1",
        "displayName": "Builder Phone",
        "platform": "ios",
        "version": "1.2.3",
        "coreVersion": "2.0.0",
        "uiVersion": "3.0.0",
        "clientId": "live-node-1",
        "clientMode": "mobile",
        "remoteIp": "10.0.0.5",
        "deviceFamily": "iphone",
        "modelIdentifier": "iphone15,3",
        "pathEnv": "/workspace",
        "caps": ["canvas", "voice"],
        "commands": ["canvas.present"],
        "permissions": {"operator.read": True},
        "paired": True,
        "connected": True,
        "connectedAtMs": 321,
        "approvedAtMs": 99,
    }


@pytest.mark.asyncio
async def test_voicewake_methods_surface_defaults_persist_updates_and_broadcast(
    tmp_path,
) -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-voicewake-node-1")
    registry.register(
        connection,
        GatewayNodeConnect(
            client_id="live-voicewake-node-1",
            device_id="voicewake-node-1",
            platform="ios",
        ),
    )
    hub = BroadcastHub()
    service = GatewayNodeMethodService(
        registry,
        hub=hub,
        voicewake_service=GatewayVoiceWakeService(tmp_path),
    )

    initial = await service.call("voicewake.get", {})

    async with hub.subscribe() as queue:
        updated = await service.call(
            "voicewake.set",
            {"triggers": ["  hello  ", "", "world  "]},
            now_ms=1234,
        )
        published = await asyncio.wait_for(queue.get(), timeout=1)

    reloaded = await service.call("voicewake.get", {})

    assert initial == {"triggers": ["openclaw", "claude", "computer"]}
    assert updated == {"triggers": ["hello", "world"]}
    assert reloaded == {"triggers": ["hello", "world"]}
    assert connection.sent_events[-1] == {
        "event": "voicewake.changed",
        "payload": {"triggers": ["hello", "world"]},
    }
    assert published["type"] == "gateway_event"
    assert published["event"] == "voicewake.changed"
    assert published["payload"] == {"triggers": ["hello", "world"]}
    assert isinstance(published["createdAt"], str)


@pytest.mark.asyncio
async def test_gateway_identity_get_returns_stable_persisted_device_identity(tmp_path) -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        gateway_identity_service=GatewayIdentityService(tmp_path),
    )

    first = await service.call("gateway.identity.get", {})
    second = await service.call("gateway.identity.get", {})

    assert first == second
    assert first["id"].startswith("gateway-")
    assert isinstance(first["publicKey"], str)
    assert len(first["publicKey"]) > 20
    assert (tmp_path / "settings" / "gateway-identity.json").exists()


@pytest.mark.asyncio
async def test_health_method_surfaces_control_plane_and_runtime_update_snapshot() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        health_service=GatewayHealthService(
            control_plane_role=lambda: "observer",
            owner_pid=lambda: 4242,
            lock_path=lambda: "/tmp/openzues.lock",
            runtime_update_snapshot=lambda: {
                "status": "idle",
                "current_revision": "abc123",
            },
        ),
    )

    health = await service.call("health", {})

    assert health == {
        "status": "ok",
        "controlPlane": "observer",
        "ownerPid": 4242,
        "lockPath": "/tmp/openzues.lock",
        "runtimeUpdate": {
            "status": "idle",
            "current_revision": "abc123",
        },
    }


@pytest.mark.asyncio
async def test_talk_config_returns_bounded_empty_snapshot_by_default() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("talk.config", {})

    assert payload == {"config": {}}


@pytest.mark.asyncio
async def test_talk_config_requires_talk_secrets_scope_for_remote_secret_reads() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="missing scope: operator.talk.secrets"):
        await service.call(
            "talk.config",
            {"includeSecrets": True},
            requester=GatewayNodeMethodRequester(caller_scopes=("operator.read",)),
        )


@pytest.mark.asyncio
async def test_tts_status_and_providers_surface_disabled_empty_runtime() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    status = await service.call("tts.status", {})
    providers = await service.call("tts.providers", {})

    assert status == {
        "enabled": False,
        "auto": "off",
        "provider": None,
        "fallbackProvider": None,
        "fallbackProviders": [],
        "prefsPath": None,
        "providerStates": [],
    }
    assert providers == {
        "providers": [],
        "active": None,
    }


@pytest.mark.asyncio
async def test_models_list_returns_bounded_catalog_defaults() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("models.list", {})

    assert payload == {
        "models": [
            {
                "id": "gpt-5.4",
                "name": "gpt-5.4",
                "provider": "openai",
                "isDefault": True,
            },
            {
                "id": "gpt-5.4-mini",
                "name": "gpt-5.4-mini",
                "provider": "openai",
            },
        ]
    }


@pytest.mark.asyncio
async def test_config_schema_returns_bounded_control_ui_bootstrap_schema() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("config.schema", {})

    assert payload["version"] == "openzues-control-ui-bootstrap-v1"
    assert payload["generatedAt"].endswith("Z")
    assert payload["schema"]["type"] == "object"
    assert payload["schema"]["properties"]["assistantName"]["type"] == "string"
    assert payload["schema"]["properties"]["localMediaPreviewRoots"]["type"] == "array"
    assert payload["schema"]["properties"]["embedSandbox"]["enum"] == [
        "strict",
        "scripts",
        "trusted",
    ]
    assert payload["uiHints"]["assistantName"]["label"] == "Assistant Name"
    assert payload["uiHints"]["assistantAvatar"]["placeholder"] == "/static/zues.svg"


@pytest.mark.asyncio
async def test_config_schema_lookup_returns_field_summary_and_children() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    root_lookup = await service.call("config.schema.lookup", {"path": ""})
    field_lookup = await service.call("config.schema.lookup", {"path": "assistantName"})

    assert root_lookup["path"] == ""
    assert root_lookup["children"][0]["key"] == "basePath"
    assert any(child["key"] == "assistantName" for child in root_lookup["children"])
    assistant_name_child = next(
        child for child in root_lookup["children"] if child["key"] == "assistantName"
    )
    assert assistant_name_child == {
        "key": "assistantName",
        "path": "assistantName",
        "type": "string",
        "required": True,
        "hasChildren": False,
        "hint": {"label": "Assistant Name"},
        "hintPath": "assistantName",
    }

    assert field_lookup == {
        "path": "assistantName",
        "schema": {
            "type": "string",
            "title": "Assistant Name",
        },
        "hint": {"label": "Assistant Name"},
        "hintPath": "assistantName",
        "children": [],
    }


@pytest.mark.asyncio
async def test_config_schema_lookup_rejects_unknown_path() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="config schema path not found"):
        await service.call("config.schema.lookup", {"path": "notReal"})


@pytest.mark.asyncio
async def test_tools_catalog_returns_bounded_openzues_toolset_inventory() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("tools.catalog", {})

    assert payload["agentId"] == "openzues"
    assert payload["profiles"] == [
        {"id": "minimal", "label": "Minimal"},
        {"id": "coding", "label": "Coding"},
        {"id": "messaging", "label": "Messaging"},
        {"id": "full", "label": "Full"},
    ]
    assert len(payload["groups"]) == 1
    group = payload["groups"][0]
    assert group["id"] == "openzues-toolsets"
    assert group["label"] == "OpenZues Toolsets"
    assert group["source"] == "core"
    assert [tool["id"] for tool in group["tools"]] == [
        "safe",
        "skills",
        "file",
        "terminal",
        "search",
        "vision",
        "image_gen",
        "browser",
        "cronjob",
        "messaging",
        "tts",
        "todo",
        "memory",
        "session_search",
        "clarify",
        "code_execution",
        "delegation",
        "homeassistant",
        "debugging",
    ]
    safe_tool = next(tool for tool in group["tools"] if tool["id"] == "safe")
    assert safe_tool == {
        "id": "safe",
        "label": "safe",
        "description": (
            "Use the safest available lane behavior and keep approval edges explicit."
        ),
        "source": "core",
        "defaultProfiles": ["coding", "full"],
    }
    tts_tool = next(tool for tool in group["tools"] if tool["id"] == "tts")
    assert tts_tool == {
        "id": "tts",
        "label": "tts",
        "description": "Prepare for voice or spoken output surfaces.",
        "source": "core",
        "defaultProfiles": ["messaging", "full"],
    }
    session_search_tool = next(
        tool for tool in group["tools"] if tool["id"] == "session_search"
    )
    assert session_search_tool["description"] == (
        "Search saved missions, checkpoints, and proof handoffs before "
        "restating the same uncertainty."
    )


@pytest.mark.asyncio
async def test_tools_effective_requires_session_key_then_fails_as_explicit_unavailable() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="sessionKey must be a non-empty string"):
        await service.call("tools.effective", {})

    with pytest.raises(
        GatewayNodeMethodError,
        match="Effective tool inventory is not wired in OpenZues yet",
    ) as exc_info:
        await service.call("tools.effective", {"sessionKey": "openzues:thread:demo"})

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_commands_list_returns_bounded_native_operator_inventory() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("commands.list", {})

    commands = payload["commands"]
    assert commands
    assert {command["source"] for command in commands} == {"native"}
    assert {command["scope"] for command in commands} == {"native"}
    status_command = next(command for command in commands if command["name"] == "status")
    assert status_command == {
        "name": "status",
        "nativeName": "status",
        "description": "Emit the operator status summary as JSON.",
        "category": "operator",
        "source": "native",
        "scope": "native",
        "acceptsArgs": True,
        "args": [
            {
                "name": "json",
                "description": "Emit the operator status summary as JSON.",
                "type": "boolean",
            }
        ],
    }
    watch_command = next(command for command in commands if command["name"] == "watch")
    assert watch_command["acceptsArgs"] is True
    assert [argument["name"] for argument in watch_command["args"]] == [
        "host",
        "port",
        "url",
        "mission-id",
        "task-name",
        "json",
    ]


@pytest.mark.asyncio
async def test_commands_list_supports_scope_filters_and_omits_args_when_requested() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    text_payload = await service.call("commands.list", {"scope": "text"})
    native_payload = await service.call("commands.list", {"scope": "native", "includeArgs": False})

    assert text_payload == {"commands": []}
    assert native_payload["commands"]
    assert all("args" not in command for command in native_payload["commands"])


@pytest.mark.asyncio
async def test_commands_list_rejects_unknown_agent_id() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match='unknown agent id "other-agent"'):
        await service.call("commands.list", {"agentId": "other-agent"})


@pytest.mark.asyncio
async def test_config_get_returns_control_ui_bootstrap_snapshot() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        config_service=GatewayConfigService(
            assistant_name="OpenZues",
            assistant_avatar="/static/favicon.svg",
            assistant_agent_id="assistant-control-ui",
            server_version="9.9.9",
        ),
    )

    config = await service.call("config.get", {})

    assert config == {
        "basePath": "",
        "assistantName": "OpenZues",
        "assistantAvatar": "/static/favicon.svg",
        "assistantAgentId": "assistant-control-ui",
        "serverVersion": "9.9.9",
        "localMediaPreviewRoots": [],
        "embedSandbox": "scripts",
        "allowExternalEmbedUrls": False,
    }


@pytest.mark.asyncio
async def test_channels_status_returns_notification_route_inventory() -> None:
    async def fake_list_notification_route_views() -> list[NotificationRouteView]:
        return [
            NotificationRouteView(
                id=7,
                name="Deploy Room",
                kind="webhook",
                target="https://example.invalid/deploy-room",
                events=["mission/completed"],
                conversation_target=ConversationTargetView(
                    channel="slack",
                    account_id="workspace-bot",
                    peer_kind="channel",
                    peer_id="deploy-room",
                    summary="slack workspace-bot channel deploy-room",
                ),
                enabled=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        ]

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        channels_service=GatewayChannelsService(
            list_notification_route_views=fake_list_notification_route_views
        ),
    )

    channels = await service.call("channels.status", {})

    assert channels["routeCount"] == 1
    assert channels["enabledCount"] == 1
    assert channels["conversationTargetCount"] == 1
    assert channels["routes"][0]["name"] == "Deploy Room"
    assert channels["routes"][0]["conversation_target"]["channel"] == "slack"


@pytest.mark.asyncio
async def test_system_presence_surfaces_gateway_self_and_connected_entries(tmp_path) -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-managed-node-1"),
        GatewayNodeConnect(
            client_id="instance-7",
            device_id="7",
            client_mode="desktop",
            display_name="Managed Lane",
            platform="desktop",
        ),
        connected_at_ms=1_700_000_000_000 - 10_000,
    )
    registry.register(
        FakeNodeConnection("conn-mobile-node-1"),
        GatewayNodeConnect(
            client_id="mobile-node-1",
            device_id="node-1",
            client_mode="mobile",
            display_name="Builder Phone",
            platform="ios",
            version="1.2.3",
            device_family="iphone",
            model_identifier="iphone15,3",
        ),
        remote_ip="10.0.0.5",
        connected_at_ms=1_700_000_000_000 - 5_000,
    )
    registry.remember(
        KnownNode(
            node_id="offline-node",
            display_name="Offline Node",
            platform="ios",
            client_id="offline-node",
            client_mode="mobile",
            paired=True,
            connected=False,
        )
    )
    service = GatewayNodeMethodService(
        registry,
        gateway_identity_service=GatewayIdentityService(tmp_path),
    )

    result = await service.call("system-presence", {}, now_ms=1_700_000_000_000)

    assert "entries" in result
    entries = result["entries"]
    assert isinstance(entries, list)
    assert len(entries) == 3
    assert all(isinstance(entry, dict) for entry in entries)
    self_entry = next(
        entry for entry in entries if entry.get("reason") == "self"
    )
    assert self_entry["deviceId"].startswith("gateway-")
    assert self_entry["instanceId"] == self_entry["deviceId"]
    assert self_entry["mode"] == "backend"
    assert self_entry["roles"] == ["operator"]
    assert self_entry["scopes"] == []
    assert self_entry["ts"] == 1_700_000_000_000
    assert "gateway" in self_entry["tags"]
    assert "self" in self_entry["tags"]

    backend_entry = next(entry for entry in entries if entry.get("deviceId") == "7")
    assert backend_entry == {
        "deviceId": "7",
        "instanceId": "instance-7",
        "host": "Managed Lane",
        "platform": "desktop",
        "mode": "backend",
        "reason": "connect",
        "ts": 1_699_999_990_000,
        "roles": ["operator"],
        "scopes": [],
    }

    node_entry = next(entry for entry in entries if entry.get("deviceId") == "node-1")
    assert node_entry == {
        "deviceId": "node-1",
        "instanceId": "mobile-node-1",
        "host": "Builder Phone",
        "ip": "10.0.0.5",
        "version": "1.2.3",
        "platform": "ios",
        "deviceFamily": "iphone",
        "modelIdentifier": "iphone15,3",
        "mode": "node",
        "reason": "node-connected",
        "ts": 1_699_999_995_000,
        "roles": ["node"],
        "scopes": [],
    }
    assert not any(entry.get("deviceId") == "offline-node" for entry in entries)


@pytest.mark.asyncio
async def test_skills_bins_collects_declared_bins_from_skill_metadata(tmp_path) -> None:
    codex_home = tmp_path / ".codex"
    local_skill = codex_home / "skills" / "local-bin-test" / "SKILL.md"
    local_skill.parent.mkdir(parents=True, exist_ok=True)
    local_skill.write_text(
        """---
name: local-bin-test
description: local skill
metadata:
  requires:
    bins:
      - git
      - node
    anyBins:
      - python
  install:
    - bins:
        - uv
        - git
---
Body
""",
        encoding="utf-8",
    )
    plugin_skill = (
        codex_home
        / "plugins"
        / "cache"
        / "example-plugin"
        / "rev-1"
        / "skills"
        / "plugin-bin-test"
        / "SKILL.md"
    )
    plugin_skill.parent.mkdir(parents=True, exist_ok=True)
    plugin_skill.write_text(
        """---
name: plugin-bin-test
description: plugin skill
metadata:
  install:
    - bins:
        - bun
---
Body
""",
        encoding="utf-8",
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_bins_service=GatewaySkillBinsService(codex_home=codex_home, workspace_root=tmp_path),
    )

    result = await service.call("skills.bins", {})

    assert result == {"bins": ["bun", "git", "node", "python", "uv"]}


@pytest.mark.asyncio
async def test_skills_status_surfaces_local_skill_inventory_report(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "local-status-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: local-status-test
description: local skill status
platforms:
  - windows
metadata:
  skillKey: local-status
  always: true
  homepage: https://example.com/skill
  primaryEnv: OPENZUES_SKILL_TOKEN
  requires:
    bins:
      - missing-bin
    env:
      - OPENZUES_SKILL_TOKEN
  install:
    - id: uv
      kind: uv
      label: Install local-status-test
      bins:
        - missing-bin
---
Body
""",
        encoding="utf-8",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    result = await service.call("skills.status", {})

    assert result == {
        "workspaceDir": str(tmp_path),
        "managedSkillsDir": str(codex_home / "skills"),
        "skills": [
            {
                "name": "local-status-test",
                "description": "local skill status",
                "source": "codex-home",
                "bundled": True,
                "filePath": str(skill_path),
                "baseDir": str(skill_path.parent),
                "skillKey": "local-status",
                "primaryEnv": "OPENZUES_SKILL_TOKEN",
                "emoji": None,
                "homepage": "https://example.com/skill",
                "always": True,
                "disabled": False,
                "blockedByAllowlist": False,
                "eligible": False,
                "requirements": {
                    "bins": ["missing-bin"],
                    "env": ["OPENZUES_SKILL_TOKEN"],
                    "config": [],
                    "os": ["windows"],
                },
                "missing": {
                    "bins": ["missing-bin"],
                    "env": ["OPENZUES_SKILL_TOKEN"],
                    "config": [],
                    "os": [],
                },
                "configChecks": [],
                "install": [
                    {
                        "id": "uv",
                        "kind": "uv",
                        "label": "Install local-status-test",
                        "bins": ["missing-bin"],
                    }
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_skills_search_and_detail_surface_local_skill_catalog(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "local-search-skill" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: Local Search Skill
description: GitHub workflow search detail api test
version: 1.2.3
platforms:
  - windows
metadata:
  systems:
    - codex
---
Body
""",
        encoding="utf-8",
    )
    os.utime(skill_path, (1_700_000_000, 1_700_000_000))
    service = GatewayNodeMethodService(GatewayNodeRegistry())
    slug = "local/codex-home/local-search-skill"

    search = await service.call("skills.search", {"query": "github", "limit": 10})
    detail = await service.call("skills.detail", {"slug": slug})

    assert search == {
        "results": [
            {
                "score": 1.0,
                "slug": slug,
                "displayName": "Local Search Skill",
                "summary": "GitHub workflow search detail api test",
                "version": "1.2.3",
                "updatedAt": 1_700_000_000,
            }
        ]
    }
    assert detail == {
        "skill": {
            "slug": slug,
            "displayName": "Local Search Skill",
            "summary": "GitHub workflow search detail api test",
            "createdAt": 1_700_000_000,
            "updatedAt": 1_700_000_000,
        },
        "latestVersion": {
            "version": "1.2.3",
            "createdAt": 1_700_000_000,
        },
        "metadata": {
            "os": ["windows"],
            "systems": ["codex"],
        },
        "owner": {
            "handle": "local",
            "displayName": "Local Skill Catalog",
            "image": None,
        },
    }


@pytest.mark.asyncio
async def test_node_methods_surface_openclaw_shaped_pair_list_payloads() -> None:
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    registry.remember(
        KnownNode(
            node_id="node-2",
            display_name="Offline Tablet",
            platform="ios",
            version="2.0.0",
            core_version="2.1.0",
            ui_version="2.2.0",
            remote_ip="10.0.0.6",
            permissions={"operator.read": True},
            paired=True,
            connected=False,
            approved_at_ms=120,
        )
    )
    service = GatewayNodeMethodService(registry)

    pairing = await service.call("node.pair.list", {})

    assert pairing == {
        "pending": [],
        "paired": [
            {
                "nodeId": "node-2",
                "displayName": "Offline Tablet",
                "platform": "ios",
                "version": "2.0.0",
                "coreVersion": "2.1.0",
                "uiVersion": "2.2.0",
                "remoteIp": "10.0.0.6",
                "permissions": {"operator.read": True},
                "createdAtMs": None,
                "approvedAtMs": 120,
                "lastConnectedAtMs": None,
            },
            {
                "nodeId": "node-1",
                "displayName": "Builder Phone",
                "platform": "ios",
                "version": "1.2.3",
                "coreVersion": "2.0.0",
                "uiVersion": "3.0.0",
                "remoteIp": "10.0.0.5",
                "permissions": {"operator.read": True},
                "createdAtMs": None,
                "approvedAtMs": 99,
                "lastConnectedAtMs": 321,
            },
        ],
    }


@pytest.mark.asyncio
async def test_node_pair_request_persists_and_refreshes_openclaw_pending_entries(
    tmp_path,
) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
    )

    first = await service.call(
        "node.pair.request",
        {
            "nodeId": "pair-node-1",
            "displayName": "Builder Phone",
            "platform": "ios",
            "version": "1.2.3",
            "coreVersion": "2.0.0",
            "uiVersion": "3.0.0",
            "deviceFamily": "iphone",
            "modelIdentifier": "iphone15,3",
            "caps": ["voice", "canvas"],
            "commands": ["canvas.present"],
            "remoteIp": "10.0.0.5",
        },
        now_ms=1_000,
    )
    second = await service.call(
        "node.pair.request",
        {
            "nodeId": "pair-node-1",
            "displayName": "Builder Phone Updated",
            "platform": "ios",
            "version": "1.2.3",
            "coreVersion": "2.0.0",
            "uiVersion": "3.0.0",
            "deviceFamily": "iphone",
            "modelIdentifier": "iphone15,3",
            "caps": ["voice", "canvas"],
            "commands": ["canvas.present"],
            "remoteIp": "10.0.0.6",
            "silent": True,
        },
        now_ms=2_000,
    )
    pairing = await service.call("node.pair.list", {})

    assert first["status"] == "pending"
    assert first["created"] is True
    request_id = first["request"]["requestId"]
    assert first["request"] == {
        "requestId": request_id,
        "nodeId": "pair-node-1",
        "displayName": "Builder Phone",
        "platform": "ios",
        "version": "1.2.3",
        "coreVersion": "2.0.0",
        "uiVersion": "3.0.0",
        "deviceFamily": "iphone",
        "modelIdentifier": "iphone15,3",
        "caps": ["voice", "canvas"],
        "commands": ["canvas.present"],
        "remoteIp": "10.0.0.5",
        "ts": 1_000,
    }
    assert second == {
        "status": "pending",
        "request": {
            "requestId": request_id,
            "nodeId": "pair-node-1",
            "displayName": "Builder Phone Updated",
            "platform": "ios",
            "version": "1.2.3",
            "coreVersion": "2.0.0",
            "uiVersion": "3.0.0",
            "deviceFamily": "iphone",
            "modelIdentifier": "iphone15,3",
            "caps": ["voice", "canvas"],
            "commands": ["canvas.present"],
            "remoteIp": "10.0.0.6",
            "ts": 2_000,
        },
        "created": False,
    }
    assert pairing == {
        "pending": [
            {
                "requestId": request_id,
                "nodeId": "pair-node-1",
                "displayName": "Builder Phone Updated",
                "platform": "ios",
                "version": "1.2.3",
                "coreVersion": "2.0.0",
                "uiVersion": "3.0.0",
                "remoteIp": "10.0.0.6",
                "ts": 2_000,
                "commands": ["canvas.present"],
                "requiredApproveScopes": ["operator.pairing", "operator.write"],
            }
        ],
        "paired": [],
    }


@pytest.mark.asyncio
async def test_node_pair_request_broadcasts_requested_event_only_for_new_requests(
    tmp_path,
) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    hub = BroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
        hub=hub,
    )

    async with hub.subscribe() as queue:
        created = await service.call(
            "node.pair.request",
            {
                "nodeId": "pair-node-event-1",
                "displayName": "Event Phone",
                "platform": "ios",
            },
            now_ms=1_000,
        )
        first_broadcast = await asyncio.wait_for(queue.get(), timeout=1.0)
        refreshed = await service.call(
            "node.pair.request",
            {
                "nodeId": "pair-node-event-1",
                "displayName": "Event Phone Updated",
                "platform": "ios",
            },
            now_ms=2_000,
        )
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get(), timeout=0.05)

    assert created["created"] is True
    assert refreshed["created"] is False
    assert first_broadcast["type"] == "gateway_event"
    assert first_broadcast["event"] == "node.pair.requested"
    assert first_broadcast["payload"] == created["request"]
    assert isinstance(first_broadcast["createdAt"], str)


@pytest.mark.asyncio
async def test_node_pair_reject_removes_pending_request(tmp_path) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
    )

    created = await service.call(
        "node.pair.request",
        {
            "nodeId": "pair-node-2",
            "displayName": "Reject Me",
            "platform": "ios",
        },
        now_ms=1_000,
    )
    request_id = created["request"]["requestId"]

    rejected = await service.call("node.pair.reject", {"requestId": request_id})
    pairing = await service.call("node.pair.list", {})

    assert rejected == {
        "requestId": request_id,
        "nodeId": "pair-node-2",
    }
    assert pairing == {
        "pending": [],
        "paired": [],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "decision"),
    [
        ("node.pair.approve", "approved"),
        ("node.pair.reject", "rejected"),
    ],
)
async def test_node_pair_resolution_broadcasts_openclaw_resolved_event(
    tmp_path,
    method: str,
    decision: str,
) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    hub = BroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
        hub=hub,
    )
    requester = GatewayNodeMethodRequester(
        caller_scopes=("operator.pairing", "operator.admin")
    )

    created = await service.call(
        "node.pair.request",
        {
            "nodeId": f"pair-node-event-{decision}",
            "displayName": "Event Node",
            "platform": "macos",
            "commands": ["system.run"],
        },
        now_ms=1_000,
    )
    request_id = created["request"]["requestId"]

    async with hub.subscribe() as queue:
        if method == "node.pair.approve":
            await service.call(
                method,
                {"requestId": request_id},
                requester=requester,
                now_ms=2_000,
            )
        else:
            await service.call(
                method,
                {"requestId": request_id},
                now_ms=2_000,
            )
        broadcast = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert broadcast["type"] == "gateway_event"
    assert broadcast["event"] == "node.pair.resolved"
    assert broadcast["payload"] == {
        "requestId": request_id,
        "nodeId": f"pair-node-event-{decision}",
        "decision": decision,
        "ts": 2_000,
    }
    assert isinstance(broadcast["createdAt"], str)


@pytest.mark.asyncio
async def test_node_pair_approve_verify_and_rename_lifecycle(tmp_path) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
    )
    requester = GatewayNodeMethodRequester(
        caller_scopes=("operator.pairing", "operator.admin")
    )

    created = await service.call(
        "node.pair.request",
        {
            "nodeId": "pair-node-3",
            "displayName": "Approve Me",
            "platform": "macos",
            "commands": ["system.run"],
            "remoteIp": "10.0.0.9",
        },
        now_ms=1_000,
    )
    request_id = created["request"]["requestId"]

    approved = await service.call(
        "node.pair.approve",
        {"requestId": request_id},
        requester=requester,
        now_ms=2_000,
    )
    token = approved["node"]["token"]
    verified = await service.call(
        "node.pair.verify",
        {"nodeId": "pair-node-3", "token": token},
    )
    renamed = await service.call(
        "node.rename",
        {"nodeId": "pair-node-3", "displayName": "Renamed Node"},
    )
    pairing = await service.call("node.pair.list", {})

    assert approved == {
        "requestId": request_id,
        "node": {
            "nodeId": "pair-node-3",
            "token": token,
            "displayName": "Approve Me",
            "platform": "macos",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "remoteIp": "10.0.0.9",
            "permissions": None,
            "createdAtMs": 2_000,
            "approvedAtMs": 2_000,
            "lastConnectedAtMs": None,
        },
    }
    assert isinstance(token, str)
    assert len(token) == 43
    assert verified == {
        "ok": True,
        "node": {
            "nodeId": "pair-node-3",
            "token": token,
            "displayName": "Approve Me",
            "platform": "macos",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "remoteIp": "10.0.0.9",
            "permissions": None,
            "createdAtMs": 2_000,
            "approvedAtMs": 2_000,
            "lastConnectedAtMs": None,
        },
    }
    assert renamed == {
        "nodeId": "pair-node-3",
        "displayName": "Renamed Node",
    }
    assert pairing == {
        "pending": [],
        "paired": [
            {
                "nodeId": "pair-node-3",
                "displayName": "Renamed Node",
                "platform": "macos",
                "version": None,
                "coreVersion": None,
                "uiVersion": None,
                "remoteIp": "10.0.0.9",
                "permissions": None,
                "createdAtMs": 2_000,
                "approvedAtMs": 2_000,
                "lastConnectedAtMs": None,
            }
        ],
    }


@pytest.mark.asyncio
async def test_node_pair_approve_respects_explicit_caller_scope_requirements(tmp_path) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
    )
    requester = GatewayNodeMethodRequester(caller_scopes=("operator.pairing",))

    created = await service.call(
        "node.pair.request",
        {
            "nodeId": "pair-node-4",
            "displayName": "Needs Admin",
            "platform": "macos",
            "commands": ["system.run"],
        },
        now_ms=1_000,
    )
    request_id = created["request"]["requestId"]

    with pytest.raises(ValueError, match="missing scope: operator.admin"):
        await service.call(
            "node.pair.approve",
            {"requestId": request_id},
            requester=requester,
            now_ms=2_000,
        )

    pairing = await service.call("node.pair.list", {})
    assert pairing["pending"] == [
        {
            "requestId": request_id,
            "nodeId": "pair-node-4",
            "displayName": "Needs Admin",
            "platform": "macos",
            "version": None,
            "coreVersion": None,
            "uiVersion": None,
            "remoteIp": None,
            "ts": 1_000,
            "commands": ["system.run"],
            "requiredApproveScopes": ["operator.pairing", "operator.admin"],
        }
    ]
    assert pairing["paired"] == []


@pytest.mark.asyncio
async def test_node_list_and_describe_include_persisted_approved_nodes(tmp_path) -> None:
    database = Database(tmp_path / "data" / "openzues-test.db")
    await database.initialize()
    pairing_service = GatewayNodePairingService(database)
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        pairing_service=pairing_service,
    )
    requester = GatewayNodeMethodRequester(
        caller_scopes=("operator.pairing", "operator.admin")
    )

    created = await service.call(
        "node.pair.request",
        {
            "nodeId": "pair-node-5",
            "displayName": "Catalog Node",
            "platform": "linux",
            "version": "1.0.0",
            "coreVersion": "2.0.0",
            "uiVersion": "3.0.0",
            "deviceFamily": "server",
            "modelIdentifier": "vm-standard",
            "caps": ["shell"],
            "commands": ["system.run"],
            "remoteIp": "10.0.0.11",
        },
        now_ms=1_000,
    )
    request_id = created["request"]["requestId"]
    await service.call(
        "node.pair.approve",
        {"requestId": request_id},
        requester=requester,
        now_ms=2_000,
    )

    listed = await service.call("node.list", {}, now_ms=3_000)
    described = await service.call("node.describe", {"nodeId": "pair-node-5"}, now_ms=3_000)

    assert listed == {
        "ts": 3_000,
        "nodes": [
            {
                "nodeId": "pair-node-5",
                "displayName": "Catalog Node",
                "platform": "linux",
                "version": "1.0.0",
                "coreVersion": "2.0.0",
                "uiVersion": "3.0.0",
                "clientId": None,
                "clientMode": None,
                "remoteIp": "10.0.0.11",
                "deviceFamily": "server",
                "modelIdentifier": "vm-standard",
                "pathEnv": None,
                "caps": ["shell"],
                "commands": ["system.run"],
                "permissions": None,
                "paired": True,
                "connected": False,
                "connectedAtMs": None,
                "approvedAtMs": 2_000,
            }
        ],
    }
    assert described == {
        "ts": 3_000,
        "nodeId": "pair-node-5",
        "displayName": "Catalog Node",
        "platform": "linux",
        "version": "1.0.0",
        "coreVersion": "2.0.0",
        "uiVersion": "3.0.0",
        "clientId": None,
        "clientMode": None,
        "remoteIp": "10.0.0.11",
        "deviceFamily": "server",
        "modelIdentifier": "vm-standard",
        "pathEnv": None,
        "caps": ["shell"],
        "commands": ["system.run"],
        "permissions": None,
        "paired": True,
        "connected": False,
        "connectedAtMs": None,
        "approvedAtMs": 2_000,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params"),
    [
        ("node.invoke.result", {"id": "req-1", "nodeId": "node-1", "ok": True}),
        ("node.pending.pull", {}),
        ("node.pending.ack", {"ids": ["pending-1"]}),
        ("node.pending.drain", {"maxItems": 1}),
    ],
)
async def test_node_methods_require_connected_identity_for_node_only_calls(
    method: str,
    params: dict[str, object],
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="requires a connected device identity"):
        await service.call(method, params)


@pytest.mark.asyncio
async def test_node_methods_surface_pending_pull_ack_and_drain_payloads() -> None:
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    queued = registry.enqueue_pending_action(
        node_id="node-1",
        command="canvas.present",
        params_json='{"screen":"main"}',
        idempotency_key="idem-canvas",
        enqueued_at_ms=555,
    )
    registry.enqueue_pending_action(
        node_id="node-1",
        command="system.run",
        params_json='{"command":"whoami"}',
        idempotency_key="idem-system-run",
        enqueued_at_ms=556,
    )
    pending_work = registry.enqueue_pending_work(
        node_id="node-1",
        work_type="location.request",
        priority="high",
        expires_in_ms=5_000,
        payload={"reason": "gps"},
    )
    requester = GatewayNodeMethodRequester(node_id="node-1")
    service = GatewayNodeMethodService(registry)

    pulled = await service.call("node.pending.pull", {}, requester=requester, now_ms=556)
    acked = await service.call(
        "node.pending.ack",
        {"ids": [queued.id]},
        requester=requester,
        now_ms=556,
    )
    drained = await service.call("node.pending.drain", {"maxItems": 1}, requester=requester)

    assert pulled == {
        "nodeId": "node-1",
        "actions": [
            {
                "id": queued.id,
                "command": "canvas.present",
                "paramsJSON": '{"screen":"main"}',
                "enqueuedAtMs": 555,
            }
        ],
    }
    assert acked == {
        "nodeId": "node-1",
        "ackedIds": [queued.id],
        "remainingCount": 0,
    }
    assert drained == {
        "nodeId": "node-1",
        "revision": 1,
        "items": [
            {
                "id": pending_work.item.id,
                "type": "location.request",
                "priority": "high",
                "createdAtMs": pending_work.item.created_at_ms,
                "expiresAtMs": pending_work.item.expires_at_ms,
                "payload": {"reason": "gps"},
            }
        ],
        "hasMore": True,
    }


@pytest.mark.asyncio
async def test_node_pending_enqueue_matches_openclaw_shape_and_rejects_default_priority() -> None:
    registry = GatewayNodeRegistry()
    registry.remember(
        KnownNode(
            node_id="node-1",
            display_name="Offline Builder",
            platform="ios",
            paired=True,
            connected=False,
        )
    )
    service = GatewayNodeMethodService(registry)

    queued = await service.call(
        "node.pending.enqueue",
        {
            "nodeId": "node-1",
            "type": "location.request",
            "priority": "high",
            "expiresInMs": 5_000,
            "wake": True,
        },
    )

    assert queued["nodeId"] == "node-1"
    assert queued["revision"] == 1
    assert queued["queued"]["type"] == "location.request"
    assert queued["queued"]["priority"] == "high"
    assert queued["wakeTriggered"] is False

    with pytest.raises(ValueError, match="priority"):
        await service.call(
            "node.pending.enqueue",
            {
                "nodeId": "node-1",
                "type": "location.request",
                "priority": "default",
            },
        )


@pytest.mark.asyncio
async def test_node_pending_enqueue_attempts_saved_lane_wake_when_requested() -> None:
    registry = GatewayNodeRegistry()
    registry.remember(
        KnownNode(
            node_id="node-1",
            display_name="Offline Builder",
            platform="desktop",
            client_id="node-1",
            client_mode="desktop",
            paired=True,
            connected=False,
        )
    )
    wake_calls: list[str] = []

    async def fake_wake(node_id: str) -> bool:
        wake_calls.append(node_id)
        return True

    service = GatewayNodeMethodService(registry, wake_node=fake_wake)

    queued = await service.call(
        "node.pending.enqueue",
        {
            "nodeId": "node-1",
            "type": "location.request",
            "priority": "high",
            "wake": True,
        },
    )

    assert wake_calls == ["node-1"]
    assert queued["wakeTriggered"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "message"),
    [
        (
            "skills.install",
            {"source": "clawhub", "slug": "openclaw/example"},
            "ClawHub skill install is not wired in OpenZues yet",
        ),
        (
            "skills.update",
            {"skillKey": "example-skill", "enabled": True},
            "Skill config patching is not wired in OpenZues yet",
        ),
        (
            "node.canvas.capability.refresh",
            {},
            "canvas host unavailable for this node session",
        ),
        (
            "node.event",
            {"event": "heartbeat", "payload": {"ok": True}},
            "node.event is not wired to a server-node-events runtime yet",
        ),
        (
            "last-heartbeat",
            {},
            "last-heartbeat is unavailable until gateway events are wired",
        ),
        (
            "tts.enable",
            {},
            "TTS runtime not wired in OpenZues yet",
        ),
        (
            "tts.disable",
            {},
            "TTS runtime not wired in OpenZues yet",
        ),
        (
            "tts.setProvider",
            {"provider": "example"},
            "TTS runtime not wired in OpenZues yet",
        ),
        (
            "tts.convert",
            {"text": "Hello from Zues"},
            "TTS conversion runtime not wired in OpenZues yet",
        ),
        (
            "talk.mode",
            {"enabled": True},
            "Talk mode broadcast is not wired in OpenZues yet",
        ),
        (
            "talk.speak",
            {"text": "Hello from talk mode."},
            "Talk synthesis runtime not wired in OpenZues yet",
        ),
    ],
)
async def test_known_node_methods_can_fail_as_explicitly_unavailable(
    method: str,
    params: dict[str, object],
    message: str,
) -> None:
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    requester = GatewayNodeMethodRequester(node_id="node-1")
    service = GatewayNodeMethodService(registry)

    with pytest.raises(GatewayNodeMethodError, match=message) as exc_info:
        await service.call(method, params, requester=requester)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_node_event_records_event_and_broadcasts_when_runtime_wired(tmp_path) -> None:
    database = Database(tmp_path / "node-event.db")
    await database.initialize()
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    hub = BroadcastHub()
    requester = GatewayNodeMethodRequester(node_id="node-1")
    service = GatewayNodeMethodService(registry, database=database, hub=hub)

    async with hub.subscribe() as queue:
        response = await service.call(
            "node.event",
            {"event": "heartbeat", "payload": {"ok": True}},
            requester=requester,
        )
        broadcast = await asyncio.wait_for(queue.get(), timeout=1.0)

    events = await database.list_events()

    assert response == {"ok": True}
    assert len(events) == 1
    assert events[0]["instance_id"] is None
    assert events[0]["thread_id"] is None
    assert events[0]["method"] == "node.event"
    assert events[0]["payload"]["nodeId"] == "node-1"
    assert events[0]["payload"]["event"] == "heartbeat"
    assert events[0]["payload"]["payload"] == {"ok": True}
    assert json.loads(events[0]["payload"]["payloadJSON"]) == {"ok": True}

    assert broadcast["type"] == "node_event"
    assert broadcast["nodeId"] == "node-1"
    assert broadcast["event"] == "heartbeat"
    assert broadcast["payload"] == {"ok": True}
    assert json.loads(str(broadcast["payloadJSON"])) == {"ok": True}
    assert isinstance(broadcast["createdAt"], str)


@pytest.mark.asyncio
async def test_last_heartbeat_surfaces_latest_recorded_heartbeat(tmp_path) -> None:
    database = Database(tmp_path / "last-heartbeat.db")
    await database.initialize()
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    registry.register(
        FakeNodeConnection("conn-node-2"),
        GatewayNodeConnect(
            client_id="live-node-2",
            device_id="node-2",
            client_mode="desktop",
            display_name="Managed Lane",
            platform="desktop",
        ),
        connected_at_ms=654,
    )
    service = GatewayNodeMethodService(registry, database=database)

    await service.call(
        "node.event",
        {"event": "heartbeat", "payload": {"ok": True, "source": "node-1"}},
        requester=GatewayNodeMethodRequester(node_id="node-1"),
    )
    await service.call(
        "node.event",
        {"event": "status", "payload": {"ok": True, "source": "node-1"}},
        requester=GatewayNodeMethodRequester(node_id="node-1"),
    )
    await service.call(
        "node.event",
        {"event": "heartbeat", "payload": {"ok": True, "source": "node-2"}},
        requester=GatewayNodeMethodRequester(node_id="node-2"),
    )

    heartbeat = await service.call("last-heartbeat", {})

    assert heartbeat == {
        "heartbeat": {
            "nodeId": "node-2",
            "displayName": "Managed Lane",
            "platform": "desktop",
            "event": "heartbeat",
            "payload": {"ok": True, "source": "node-2"},
            "payloadJSON": '{"ok": true, "source": "node-2"}',
            "createdAt": heartbeat["heartbeat"]["createdAt"],
        }
    }
    assert isinstance(heartbeat["heartbeat"]["createdAt"], str)


@pytest.mark.asyncio
async def test_last_heartbeat_returns_none_when_no_heartbeat_is_recorded(tmp_path) -> None:
    database = Database(tmp_path / "last-heartbeat-empty.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    heartbeat = await service.call("last-heartbeat", {})

    assert heartbeat == {"heartbeat": None}


@pytest.mark.asyncio
async def test_node_canvas_capability_refresh_rotates_scoped_host_url() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-canvas-node-1"),
        GatewayNodeConnect(
            client_id="live-canvas-node-1",
            device_id="node-1",
            platform="ios",
            canvas_host_url="http://127.0.0.1:18789",
        ),
    )
    requester = GatewayNodeMethodRequester(node_id="node-1")
    service = GatewayNodeMethodService(registry)

    response = await service.call(
        "node.canvas.capability.refresh",
        {},
        requester=requester,
        now_ms=1_700_000_000_000,
    )

    session = registry.get("node-1")
    assert session is not None
    assert response["canvasCapability"] == session.canvas_capability
    assert response["canvasCapabilityExpiresAtMs"] == session.canvas_capability_expires_at_ms
    assert response["canvasCapabilityExpiresAtMs"] == 1_700_000_600_000
    assert response["canvasHostUrl"] == (
        f"http://127.0.0.1:18789/__openclaw__/cap/{response['canvasCapability']}"
    )


@pytest.mark.asyncio
async def test_node_invoke_result_completes_pending_registry_invoke() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-node-1")
    registry.register(
        connection,
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            platform="windows",
            commands=("system.run",),
        ),
    )
    requester = GatewayNodeMethodRequester(node_id="node-1")
    service = GatewayNodeMethodService(registry)

    invoke_task = asyncio.create_task(
        registry.invoke(
            node_id="node-1",
            command="system.run",
            params={"command": "whoami"},
            timeout_ms=250,
            idempotency_key="idem-system-run",
        )
    )
    await asyncio.sleep(0)
    request = connection.sent_events[0]
    request_payload = request["payload"]
    assert isinstance(request_payload, dict)

    result = await service.call(
        "node.invoke.result",
        {
            "id": str(request_payload["id"]),
            "nodeId": "node-1",
            "ok": True,
            "payload": {"status": "done"},
            "payloadJSON": '{"status":"done"}',
        },
        requester=requester,
    )
    invoke_result = await invoke_task

    assert result == {"ok": True}
    assert invoke_result.ok is True
    assert invoke_result.payload == {"status": "done"}
    assert invoke_result.payload_json == '{"status":"done"}'


@pytest.mark.asyncio
async def test_node_invoke_result_rejects_cross_node_spoofing() -> None:
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    registry.register(
        FakeNodeConnection("conn-node-2"),
        GatewayNodeConnect(
            client_id="live-node-2",
            device_id="node-2",
            platform="ios",
            commands=("canvas.present",),
        ),
    )
    requester = GatewayNodeMethodRequester(node_id="node-2")
    service = GatewayNodeMethodService(registry)

    with pytest.raises(ValueError, match="nodeId does not match connected device identity"):
        await service.call(
            "node.invoke.result",
            {"id": "req-1", "nodeId": "node-1", "ok": True},
            requester=requester,
        )


@pytest.mark.asyncio
async def test_node_invoke_returns_openclaw_shaped_success_payload() -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-node-1")
    registry.register(
        connection,
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            platform="windows",
            commands=("system.run",),
        ),
    )
    service = GatewayNodeMethodService(registry)

    invoke_task = asyncio.create_task(
        service.call(
            "node.invoke",
            {
                "nodeId": "node-1",
                "command": "system.run",
                "params": {"command": "whoami"},
                "timeoutMs": 250,
                "idempotencyKey": "idem-system-run",
            },
        )
    )
    await asyncio.sleep(0)
    request = connection.sent_events[0]
    request_payload = request["payload"]
    assert isinstance(request_payload, dict)

    registry.handle_invoke_result(
        request_id=str(request_payload["id"]),
        node_id="node-1",
        ok=True,
        payload={"status": "done"},
        payload_json='{"status":"done"}',
    )

    assert await invoke_task == {
        "ok": True,
        "nodeId": "node-1",
        "command": "system.run",
        "payload": {"status": "done"},
        "payloadJSON": '{"status":"done"}',
    }


@pytest.mark.asyncio
async def test_node_invoke_attempts_saved_lane_wake_before_failing_not_connected() -> None:
    registry = GatewayNodeRegistry()
    registry.remember(
        KnownNode(
            node_id="node-1",
            display_name="Wakeable Builder",
            platform="windows",
            client_id="node-1",
            client_mode="desktop",
            commands=("system.run",),
            paired=True,
            connected=False,
        )
    )
    wake_calls: list[str] = []

    async def fake_wake(node_id: str) -> bool:
        wake_calls.append(node_id)
        registry.register(
            AutoReplyNodeConnection(registry, "conn-node-1"),
            GatewayNodeConnect(
                client_id="node-1",
                device_id=node_id,
                client_mode="desktop",
                display_name="Wakeable Builder",
                platform="windows",
                commands=("system.run",),
            ),
        )
        return True

    service = GatewayNodeMethodService(registry, wake_node=fake_wake)

    result = await service.call(
        "node.invoke",
        {
            "nodeId": "node-1",
            "command": "system.run",
            "params": {"command": "whoami"},
            "timeoutMs": 250,
            "idempotencyKey": "idem-system-run",
        },
    )

    assert wake_calls == ["node-1"]
    assert result == {
        "ok": True,
        "nodeId": "node-1",
        "command": "system.run",
        "payload": {"status": "done"},
        "payloadJSON": '{"status":"done"}',
    }


@pytest.mark.asyncio
async def test_node_invoke_rejects_commands_the_node_did_not_declare() -> None:
    registry = GatewayNodeRegistry()
    registry.register(
        FakeNodeConnection("conn-node-1"),
        GatewayNodeConnect(
            client_id="live-node-1",
            device_id="node-1",
            platform="windows",
            commands=("system.which",),
        ),
    )
    service = GatewayNodeMethodService(registry)

    with pytest.raises(ValueError, match='does not support "system.run"'):
        await service.call(
            "node.invoke",
            {
                "nodeId": "node-1",
                "command": "system.run",
                "params": {"command": "whoami"},
                "idempotencyKey": "idem-system-run",
            },
        )
