from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from openzues.database import Database, utcnow
from openzues.schemas import (
    ConversationTargetView,
    IntegrationView,
    NotificationRouteView,
    TaskBlueprintCreate,
)
from openzues.services.gateway_agent_files import GatewayAgentFilesService
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
from openzues.services.gateway_sessions import GatewaySessionsService
from openzues.services.gateway_skill_bins import GatewaySkillBinsService
from openzues.services.gateway_skill_clawhub import GatewaySkillClawHubService
from openzues.services.gateway_skill_install import GatewaySkillInstallService
from openzues.services.gateway_talk_mode import GatewayTalkModeService
from openzues.services.gateway_tts import GatewayTtsService
from openzues.services.gateway_tts_runtime import (
    GatewayTtsRuntimeService,
    GatewayTtsSynthesisResult,
)
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
from openzues.services.gateway_wake import GatewayWakeService
from openzues.services.gateway_wizard import GatewayWizardService
from openzues.services.hub import BroadcastHub
from openzues.services.session_keys import build_launch_session_key, resolve_thread_session_keys


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


class FakeCronTaskRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    async def __call__(self, task_id: int, *, trigger: str = "manual") -> object:
        self.calls.append((task_id, trigger))
        return type("FakeMission", (), {"id": 52})()


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


def _task_blueprint_payload(
    objective_template: str,
    *,
    model: str = "gpt-5.4",
) -> dict[str, object]:
    return {
        "objective_template": objective_template,
        "conversation_target": None,
        "run_until_complete": False,
        "continuation_cooldown_minutes": 10,
        "completion_marker": None,
        "cwd": None,
        "model": model,
        "reasoning_effort": None,
        "collaboration_mode": None,
        "max_turns": None,
        "use_builtin_agents": True,
        "run_verification": True,
        "auto_commit": False,
        "pause_on_approval": True,
        "allow_auto_reflexes": True,
        "auto_recover": True,
        "auto_recover_limit": 2,
        "reflex_cooldown_seconds": 900,
        "allow_failover": True,
        "toolsets": [],
        "enabled": True,
    }


async def _create_scheduled_mission(
    database: Database,
    *,
    name: str,
    objective: str,
    status: str,
    task_blueprint_id: int,
    thread_id: str,
    session_key: str = "launch:mode:workspace_affinity",
    last_checkpoint: str | None = None,
    last_error: str | None = None,
    model: str = "gpt-5.4",
) -> int:
    mission_id = await database.create_mission(
        name=name,
        objective=objective,
        status=status,
        instance_id=7,
        project_id=None,
        thread_id=thread_id,
        session_key=session_key,
        conversation_target=None,
        cwd="C:/workspace",
        model=model,
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
        task_blueprint_id=task_blueprint_id,
    )
    updates: dict[str, object] = {}
    if last_checkpoint is not None:
        updates["last_checkpoint"] = last_checkpoint
    if last_error is not None:
        updates["last_error"] = last_error
    if updates:
        await database.update_mission(mission_id, **updates)
    return mission_id


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
    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
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
async def test_talk_mode_persists_updates_and_broadcast(tmp_path) -> None:
    registry = GatewayNodeRegistry()
    connection = FakeNodeConnection("conn-talk-mode-node-1")
    registry.register(
        connection,
        GatewayNodeConnect(
            client_id="live-talk-mode-node-1",
            device_id="talk-mode-node-1",
            platform="ios",
        ),
    )
    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        registry,
        hub=hub,
        talk_mode_service=GatewayTalkModeService(tmp_path),
    )

    async with hub.subscribe() as queue:
        updated = await service.call(
            "talk.mode",
            {"enabled": True, "phase": "listening"},
            now_ms=1234,
        )
        published = await asyncio.wait_for(queue.get(), timeout=1)

    reloaded = GatewayTalkModeService(tmp_path).load()

    assert updated == {
        "enabled": True,
        "phase": "listening",
    }
    assert reloaded.enabled is True
    assert reloaded.phase == "listening"
    assert connection.sent_events[-1] == {
        "event": "talk.mode",
        "payload": {
            "enabled": True,
            "phase": "listening",
        },
    }
    assert published["type"] == "gateway_event"
    assert published["event"] == "talk.mode"
    assert published["payload"] == {
        "enabled": True,
        "phase": "listening",
    }
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
        "providerStates": [
            {
                "id": "elevenlabs",
                "label": "ElevenLabs",
                "available": False,
                "selected": False,
            },
            {
                "id": "microsoft",
                "label": "Microsoft",
                "available": True,
                "selected": False,
            },
            {
                "id": "minimax",
                "label": "MiniMax",
                "available": False,
                "selected": False,
            },
            {
                "id": "openai",
                "label": "OpenAI",
                "available": False,
                "selected": False,
            },
        ],
    }
    assert providers == {
        "providers": ["elevenlabs", "microsoft", "minimax", "openai"],
        "active": None,
    }


@pytest.mark.asyncio
async def test_tts_pref_methods_persist_local_state_and_surface_status(tmp_path) -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_service=GatewayTtsService(tmp_path),
    )

    enabled = await service.call("tts.enable", {})
    selected = await service.call("tts.setProvider", {"provider": "edge"})
    providers = await service.call("tts.providers", {})
    disabled = await service.call("tts.disable", {})
    reloaded = await GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_service=GatewayTtsService(tmp_path),
    ).call("tts.status", {})

    assert enabled["enabled"] is True
    assert enabled["auto"] == "on"
    assert enabled["provider"] is None
    assert enabled["prefsPath"] is not None
    assert selected["provider"] == "microsoft"
    assert selected["enabled"] is True
    assert providers == {
        "providers": ["elevenlabs", "microsoft", "minimax", "openai"],
        "active": "microsoft",
    }
    assert disabled["enabled"] is False
    assert disabled["auto"] == "off"
    assert disabled["provider"] == "microsoft"
    assert reloaded["enabled"] is False
    assert reloaded["provider"] == "microsoft"
    assert reloaded["prefsPath"] == enabled["prefsPath"]
    provider_states = {entry["id"]: entry for entry in reloaded["providerStates"]}
    assert provider_states["microsoft"]["available"] is True
    assert provider_states["microsoft"]["selected"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["   ", "not-a-real-provider"])
async def test_tts_set_provider_rejects_blank_or_unknown_provider_ids(
    tmp_path,
    provider: str,
) -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_service=GatewayTtsService(tmp_path),
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match="Invalid provider\\. Use a registered TTS provider id\\.",
    ) as exc_info:
        await service.call("tts.setProvider", {"provider": provider})

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400
    assert (await service.call("tts.status", {}))["provider"] is None


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
async def test_models_auth_status_returns_validated_unavailable_contract() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call("models.authStatus", {"refresh": True})

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == (
        "models.authStatus is unavailable until model auth health runtime is wired"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "message"),
    [
        (
            "device.pair.list",
            {},
            "device.pair.list is unavailable until device auth pairing runtime is wired",
        ),
        (
            "device.pair.approve",
            {"requestId": "device-request-1"},
            "device.pair.approve is unavailable until device auth pairing runtime is wired",
        ),
        (
            "device.pair.reject",
            {"requestId": "device-request-1"},
            "device.pair.reject is unavailable until device auth pairing runtime is wired",
        ),
        (
            "device.pair.remove",
            {"deviceId": "device-1"},
            "device.pair.remove is unavailable until device auth pairing runtime is wired",
        ),
        (
            "device.token.rotate",
            {
                "deviceId": "device-1",
                "role": "operator",
                "scopes": ["operator.read"],
            },
            "device.token.rotate is unavailable until device auth token runtime is wired",
        ),
        (
            "device.token.revoke",
            {"deviceId": "device-1", "role": "operator"},
            "device.token.revoke is unavailable until device auth token runtime is wired",
        ),
    ],
)
async def test_device_family_returns_explicit_unavailable_contract(
    method: str,
    params: dict[str, object],
    message: str,
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "message"),
    [
        (
            "plugin.approval.list",
            {},
            "plugin.approval.list is unavailable until plugin approval runtime is wired",
        ),
        (
            "plugin.approval.request",
            {
                "pluginId": "alpha-plugin",
                "title": "Install alpha plugin",
                "description": "Approve installation of the alpha plugin bundle.",
                "severity": "warning",
                "toolName": "plugin.install",
                "toolCallId": "call-1",
                "agentId": "agent-1",
                "sessionKey": "session-1",
                "turnSourceChannel": "slack",
                "turnSourceTo": "ops",
                "turnSourceAccountId": "acct-1",
                "turnSourceThreadId": 42,
                "timeoutMs": 30_000,
                "twoPhase": True,
            },
            "plugin.approval.request is unavailable until plugin approval runtime is wired",
        ),
        (
            "plugin.approval.waitDecision",
            {"id": "plugin:approval-1"},
            "plugin.approval.waitDecision is unavailable until plugin approval runtime is wired",
        ),
        (
            "plugin.approval.resolve",
            {"id": "plugin:approval-1", "decision": "allow-once"},
            "plugin.approval.resolve is unavailable until plugin approval runtime is wired",
        ),
    ],
)
async def test_plugin_approval_family_returns_explicit_unavailable_contract(
    method: str,
    params: dict[str, object],
    message: str,
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "message"),
    [
        (
            "exec.approval.get",
            {"id": "approval-1"},
            "exec.approval.get is unavailable until exec approval runtime is wired",
        ),
        (
            "exec.approval.list",
            {},
            "exec.approval.list is unavailable until exec approval runtime is wired",
        ),
        (
            "exec.approval.request",
            {
                "id": "approval-1",
                "command": "npm test",
                "commandArgv": ["npm", "test"],
                "env": {"CI": "1"},
                "cwd": "C:/workspace",
                "host": "desktop",
                "security": "strict",
                "ask": "manual",
                "agentId": "agent-1",
                "resolvedPath": "C:/workspace/package.json",
                "sessionKey": "session-1",
                "turnSourceChannel": "slack",
                "turnSourceTo": "ops",
                "turnSourceAccountId": "acct-1",
                "turnSourceThreadId": "thread-1",
                "timeoutMs": 30_000,
                "twoPhase": True,
            },
            "exec.approval.request is unavailable until exec approval runtime is wired",
        ),
        (
            "exec.approval.waitDecision",
            {"id": "approval-1"},
            "exec.approval.waitDecision is unavailable until exec approval runtime is wired",
        ),
        (
            "exec.approval.resolve",
            {"id": "approval-1", "decision": "allow-once"},
            "exec.approval.resolve is unavailable until exec approval runtime is wired",
        ),
    ],
)
async def test_exec_approval_family_returns_explicit_unavailable_contract(
    method: str,
    params: dict[str, object],
    message: str,
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "message"),
    [
        (
            "exec.approvals.get",
            {},
            "exec.approvals.get is unavailable until exec approval policy config runtime is wired",
        ),
        (
            "exec.approvals.set",
            {
                "file": {
                    "version": 1,
                    "socket": {"path": "C:/tmp/approvals.sock", "token": "secret-token"},
                    "defaults": {
                        "security": "strict",
                        "ask": "manual",
                        "askFallback": "deny",
                        "autoAllowSkills": True,
                    },
                    "agents": {
                        "main": {
                            "security": "strict",
                            "ask": "manual",
                            "askFallback": "deny",
                            "autoAllowSkills": False,
                            "allowlist": [
                                {
                                    "id": "entry-1",
                                    "pattern": "npm",
                                    "argPattern": "test",
                                    "lastUsedAt": 1,
                                    "lastUsedCommand": "npm test",
                                    "lastResolvedPath": "C:/workspace/package.json",
                                }
                            ],
                        }
                    },
                },
                "baseHash": "abc123",
            },
            "exec.approvals.set is unavailable until exec approval policy config runtime is wired",
        ),
        (
            "exec.approvals.node.get",
            {"nodeId": "node-1"},
            "exec.approvals.node.get is unavailable until exec approval policy "
            "config runtime is wired",
        ),
        (
            "exec.approvals.node.set",
            {
                "nodeId": "node-1",
                "file": {
                    "version": 1,
                    "defaults": {
                        "security": "strict",
                        "ask": "manual",
                        "askFallback": "deny",
                        "autoAllowSkills": True,
                    },
                },
                "baseHash": "node-hash",
            },
            "exec.approvals.node.set is unavailable until exec approval policy "
            "config runtime is wired",
        ),
    ],
)
async def test_exec_approvals_family_returns_explicit_unavailable_contract(
    method: str,
    params: dict[str, object],
    message: str,
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == message


@pytest.mark.asyncio
async def test_set_heartbeats_returns_explicit_unavailable_contract() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call("set-heartbeats", {"enabled": True})

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == (
        "set-heartbeats is unavailable until gateway heartbeat toggle runtime is wired"
    )


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
async def test_tools_effective_returns_bounded_effective_inventory_from_session_toolsets() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-tools-effective-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-tools-effective.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-effective-tools",
    ).session_key
    await database.create_mission(
        name="Effective Tool Mission",
        objective="Keep the effective tool posture aligned with the session.",
        status="active",
        instance_id=7,
        project_id=None,
        task_blueprint_id=None,
        thread_id="thread-effective-tools",
        session_key=session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=["hermes-cli"],
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="sessionKey must be a non-empty string"):
        await service.call("tools.effective", {})

    payload = await service.call(
        "tools.effective",
        {"sessionKey": session_key, "agentId": "main"},
    )

    assert payload["agentId"] == "main"
    assert payload["profile"] == "coding"
    assert len(payload["groups"]) == 1
    group = payload["groups"][0]
    assert group["id"] == "core"
    assert group["label"] == "Built-in tools"
    assert group["source"] == "core"
    assert [tool["id"] for tool in group["tools"]] == [
        "safe",
        "skills",
        "file",
        "terminal",
        "search",
        "delegation",
        "debugging",
    ]
    assert group["tools"][0]["rawDescription"] == group["tools"][0]["description"]


@pytest.mark.asyncio
async def test_chat_history_returns_openclaw_shaped_control_chat_projection() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-history-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-chat-history.db")
    await database.initialize()
    await database.append_control_chat_message(
        role="user",
        content="Need the latest parity checkpoint.",
        session_key="openzues:thread:demo",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The status bridge is landed and verified.",
        session_key="openzues:thread:demo",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "chat.history",
        {"sessionKey": "openzues:thread:demo", "limit": 2},
    )

    assert payload == {
        "sessionKey": "openzues:thread:demo",
        "sessionId": None,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Need the latest parity checkpoint."}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "The status bridge is landed and verified."}],
            },
        ],
        "thinkingLevel": None,
        "fastMode": None,
        "verboseLevel": None,
        "traceLevel": None,
    }


@pytest.mark.asyncio
async def test_chat_history_applies_tail_char_budget_to_latest_message() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-history-char-budget"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-chat-history.db")
    await database.initialize()
    await database.append_control_chat_message(
        role="user",
        content="Older context stays behind the cutoff.",
        session_key="openzues:thread:demo",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="checkpoint",
        session_key="openzues:thread:demo",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "chat.history",
        {"sessionKey": "openzues:thread:demo", "limit": 2, "maxChars": 4},
    )

    assert payload["messages"] == [
        {"role": "assistant", "content": [{"type": "text", "text": "oint"}]}
    ]


@pytest.mark.asyncio
async def test_chat_send_returns_run_ack_from_injected_control_chat_bridge() -> None:
    observed: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
    )

    with pytest.raises(ValueError, match="sessionKey must be a non-empty string"):
        await service.call("chat.send", {})

    payload = await service.call(
        "chat.send",
        {
            "sessionKey": "openzues:thread:demo",
            "message": "status",
            "thinking": "low",
            "deliver": False,
            "timeoutMs": 30_000,
            "idempotencyKey": "run-chat-send-1",
        },
    )

    assert observed == {
        "session_key": "openzues:thread:demo",
        "message": "status",
        "idempotency_key": "run-chat-send-1",
        "thinking": "low",
        "deliver": False,
        "timeout_ms": 30_000,
    }
    assert payload == {"runId": "run-chat-send-1", "status": "ok"}


@pytest.mark.asyncio
async def test_chat_inject_appends_assistant_message_and_publishes_session_message_event() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-chat-inject-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-chat-inject.db")
    await database.initialize()

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    session_key = resolve_thread_session_keys(
        base_session_key=build_launch_session_key(
            mode="workspace_affinity",
            preferred_instance_id=None,
            task_id=None,
            project_id=None,
            operator_id=None,
        ),
        thread_id="thread-chat-inject-1",
    ).session_key
    await database.create_mission(
        name="Gateway Chat Inject Loop",
        objective="Inspect transcript injection parity.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-chat-inject-1",
        session_key=session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="sessionKey must be a non-empty string"):
        await service.call("chat.inject", {})

    with pytest.raises(ValueError, match="session not found"):
        await service.call(
            "chat.inject",
            {
                "sessionKey": "launch:mode:workspace_affinity:thread:missing",
                "message": "Injected parity note",
            },
        )

    payload = await service.call(
        "chat.inject",
        {
            "sessionKey": session_key,
            "message": "Injected parity note",
            "label": "Parity Note",
        },
        now_ms=444,
    )

    assert payload == {"ok": True, "messageId": "1"}
    rows = await database.list_control_chat_messages(limit=10, session_key=session_key)
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["role"] == "assistant"
    assert rows[0]["content"] == "Injected parity note"
    assert rows[0]["target_label"] == "Parity Note"
    assert rows[0]["session_key"] == session_key

    session_message_events = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "session.message"
    ]
    assert len(session_message_events) == 1
    assert session_message_events[0]["payload"]["sessionKey"] == session_key
    assert session_message_events[0]["payload"]["messageId"] == "1"
    assert session_message_events[0]["payload"]["messageSeq"] == 1
    assert session_message_events[0]["payload"]["message"] == {
        "id": "1",
        "role": "assistant",
        "content": [{"type": "text", "text": "Injected parity note"}],
    }

    sessions_changed_events = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert len(sessions_changed_events) == 1
    assert sessions_changed_events[0]["payload"]["sessionKey"] == session_key
    assert sessions_changed_events[0]["payload"]["phase"] == "message"
    assert sessions_changed_events[0]["payload"]["messageId"] == "1"


@pytest.mark.asyncio
async def test_sessions_send_routes_key_to_bounded_control_chat_runtime() -> None:
    observed: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
    )

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.send", {})

    payload = await service.call(
        "sessions.send",
        {
            "key": "openzues:thread:demo",
            "message": "status",
            "thinking": "low",
            "timeoutMs": 30_000,
            "idempotencyKey": "run-session-send-1",
        },
    )

    assert observed == {
        "session_key": "openzues:thread:demo",
        "message": "status",
        "idempotency_key": "run-session-send-1",
        "thinking": "low",
        "deliver": None,
        "timeout_ms": 30_000,
    }
    assert payload == {"runId": "run-session-send-1", "status": "ok"}


@pytest.mark.asyncio
async def test_chat_abort_interrupts_tracked_gateway_run_with_injected_runtime() -> None:
    observed_interrupt: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    async def fake_chat_abort_service(
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        observed_interrupt.update({"session_key": session_key, "run_id": run_id})
        return {"ok": True}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
        chat_abort_service=fake_chat_abort_service,
    )

    await service.call(
        "chat.send",
        {
            "sessionKey": "openzues:thread:demo",
            "message": "status",
            "idempotencyKey": "run-chat-send-1",
        },
    )
    payload = await service.call(
        "chat.abort",
        {"sessionKey": "openzues:thread:demo", "runId": "run-chat-send-1"},
    )

    assert observed_interrupt == {
        "session_key": "openzues:thread:demo",
        "run_id": "run-chat-send-1",
    }
    assert payload == {"ok": True, "aborted": True, "runIds": ["run-chat-send-1"]}


@pytest.mark.asyncio
async def test_chat_abort_treats_empty_run_id_as_session_scoped_abort() -> None:
    observed_interrupt: dict[str, str | None] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    async def fake_chat_abort_service(
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        observed_interrupt.update({"session_key": session_key, "run_id": run_id})
        return {"ok": True}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
        chat_abort_service=fake_chat_abort_service,
    )

    await service.call(
        "chat.send",
        {
            "sessionKey": "openzues:thread:demo",
            "message": "status",
            "idempotencyKey": "run-chat-send-1",
        },
    )
    payload = await service.call(
        "chat.abort",
        {"sessionKey": "openzues:thread:demo", "runId": ""},
    )

    assert observed_interrupt == {
        "session_key": "openzues:thread:demo",
        "run_id": None,
    }
    assert payload == {"ok": True, "aborted": True, "runIds": ["run-chat-send-1"]}


@pytest.mark.asyncio
async def test_sessions_send_publishes_openclaw_sessions_changed_gateway_event() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-send-event-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-send-event.db")
    await database.initialize()

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"traceLevel": "verbose"},
    )

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
        chat_send_service=fake_chat_send_service,
    )

    payload = await service.call(
        "sessions.send",
        {
            "key": session_key,
            "message": "status",
            "idempotencyKey": "run-session-send-1",
        },
        now_ms=111,
    )

    assert payload == {"runId": "run-session-send-1", "status": "ok"}
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert len(sessions_changed) == 1
    assert sessions_changed[0]["payload"] == {
        "sessionKey": session_key,
        "reason": "send",
        "ts": 111,
        "updatedAt": sessions_changed[0]["payload"]["updatedAt"],
        "sessionId": None,
        "kind": "global",
        "subject": "Operator control chat",
        "displayName": "OpenZues Control Chat",
        "systemSent": None,
        "abortedLastRun": None,
        "thinkingLevel": None,
        "verboseLevel": None,
        "traceLevel": "verbose",
        "inputTokens": None,
        "outputTokens": None,
        "totalTokens": None,
        "contextTokens": None,
        "modelProvider": "openai",
        "model": "gpt-5.4",
        "space": None,
    }
    assert isinstance(sessions_changed[0]["createdAt"], str)
    assert isinstance(sessions_changed[0]["payload"]["updatedAt"], int)


@pytest.mark.asyncio
async def test_chat_abort_does_not_interrupt_when_run_id_is_not_the_tracked_gateway_run() -> None:
    called = False

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    async def fake_chat_abort_service(
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        del session_key, run_id
        nonlocal called
        called = True
        return {"ok": True}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
        chat_abort_service=fake_chat_abort_service,
    )

    await service.call(
        "chat.send",
        {
            "sessionKey": "openzues:thread:demo",
            "message": "status",
            "idempotencyKey": "run-chat-send-1",
        },
    )
    payload = await service.call(
        "chat.abort",
        {"sessionKey": "openzues:thread:demo", "runId": "run-chat-send-2"},
    )

    assert called is False
    assert payload == {"ok": True, "aborted": False, "runIds": []}


@pytest.mark.asyncio
async def test_sessions_abort_translates_tracked_gateway_run_into_session_status_payload() -> (
    None
):
    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    async def fake_chat_abort_service(
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        del session_key, run_id
        return {"ok": True}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
        chat_abort_service=fake_chat_abort_service,
    )

    await service.call(
        "sessions.send",
        {
            "key": "openzues:thread:demo",
            "message": "status",
            "idempotencyKey": "run-session-send-1",
        },
    )
    payload = await service.call("sessions.abort", {"key": "openzues:thread:demo"})

    assert payload == {
        "ok": True,
        "abortedRunId": "run-session-send-1",
        "status": "aborted",
    }


@pytest.mark.asyncio
async def test_sessions_steer_interrupts_tracked_run_before_sending_follow_up() -> None:
    events: list[tuple[str, str, str | None]] = []

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del thinking, deliver, timeout_ms
        events.append(("send", session_key, idempotency_key))
        return {"runId": idempotency_key, "status": "ok"}

    async def fake_chat_abort_service(
        *,
        session_key: str,
        run_id: str | None,
    ) -> dict[str, object]:
        events.append(("abort", session_key, run_id))
        return {"ok": True}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        chat_send_service=fake_chat_send_service,
        chat_abort_service=fake_chat_abort_service,
    )

    await service.call(
        "sessions.send",
        {
            "key": "openzues:thread:demo",
            "message": "status",
            "idempotencyKey": "run-session-send-1",
        },
    )
    payload = await service.call(
        "sessions.steer",
        {
            "key": "openzues:thread:demo",
            "message": "redirect",
            "idempotencyKey": "run-session-steer-1",
        },
    )

    assert events == [
        ("send", "openzues:thread:demo", "run-session-send-1"),
        ("abort", "openzues:thread:demo", None),
        ("send", "openzues:thread:demo", "run-session-steer-1"),
    ]
    assert payload == {"runId": "run-session-steer-1", "status": "ok"}


@pytest.mark.asyncio
async def test_sessions_steer_fails_explicitly_until_interrupt_runtime_is_wired() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.steer", {})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.steer",
            {
                "key": "openzues:thread:demo",
                "message": "status",
                "thinking": "low",
                "timeoutMs": 30_000,
                "idempotencyKey": "run-session-steer-1",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.steer is unavailable until control chat interruption is wired"
    )


@pytest.mark.asyncio
async def test_sessions_abort_fails_as_explicit_unavailable_until_runtime_is_wired() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.abort", {})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.abort",
            {"key": "openzues:thread:demo", "runId": "run-session-send-1"},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "chat.abort is unavailable until control chat cancellation is wired"
    )


@pytest.mark.asyncio
async def test_sessions_reset_clears_transcript_and_preserves_session_entry() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-reset-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-reset.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-reset-service",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"label": "Parity Reset Session"},
    )
    await database.append_control_chat_message(
        role="user",
        content="Please clear this transcript.",
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The transcript is still present before reset.",
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Noise from another session.",
        session_key=resolve_thread_session_keys(
            base_session_key=main_session_key,
            thread_id="thread-other-service",
        ).session_key,
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.reset", {})

    with pytest.raises(ValueError, match="reason must be one of: new, reset"):
        await service.call(
            "sessions.reset",
            {"key": "openzues:thread:demo", "reason": "broken"},
        )

    payload = await service.call(
        "sessions.reset",
        {"key": session_key, "reason": "new"},
        now_ms=444,
    )

    assert payload["ok"] is True
    assert payload["key"] == session_key
    assert payload["entry"]["key"] == session_key
    assert payload["entry"]["kind"] == "thread"
    assert payload["entry"]["sessionId"] == "thread-reset-service"
    assert payload["entry"]["label"] == "Parity Reset Session"
    assert isinstance(payload["entry"]["updatedAt"], int)
    assert payload["entry"]["updatedAt"] > 0

    history_payload = await service.call(
        "chat.history",
        {"sessionKey": session_key, "limit": 10},
    )
    assert history_payload["messages"] == []

    messages_payload = await service.call(
        "sessions.get",
        {"key": session_key, "limit": 10},
    )
    assert messages_payload == {"messages": []}

    assert await database.count_control_chat_messages(session_key=session_key) == 0
    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-other-service",
    ).session_key
    assert await database.count_control_chat_messages(session_key=other_session_key) == 1

    sessions_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=555,
    )
    assert [session["key"] for session in sessions_payload["sessions"]] == [
        main_session_key,
        session_key,
    ]

    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert [event["payload"]["reason"] for event in sessions_changed] == ["new"]
    assert sessions_changed[0]["payload"]["sessionKey"] == session_key


@pytest.mark.asyncio
async def test_sessions_delete_removes_metadata_backed_session_and_transcript() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-delete-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-delete.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-delete-service",
    ).session_key
    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-other-service",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"label": "Parity Delete Session"},
    )
    await database.append_control_chat_message(
        role="user",
        content="Please delete this transcript.",
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The transcript is still present before delete.",
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Noise from another session.",
        session_key=other_session_key,
    )
    archive_dir = database.path.parent / "gateway-session-archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    stale_archive = archive_dir / "other-session-deleted-20260301T000000Z.jsonl"
    recent_archive = archive_dir / "other-session-deleted-20260417T000000Z.jsonl"
    ignored_file = archive_dir / "readme.txt"
    stale_archive.write_text("stale\n", encoding="utf-8")
    recent_archive.write_text("recent\n", encoding="utf-8")
    ignored_file.write_text("ignore\n", encoding="utf-8")

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.delete", {})

    with pytest.raises(ValueError, match="deleteTranscript must be a boolean"):
        await service.call(
            "sessions.delete",
            {"key": "openzues:thread:demo", "deleteTranscript": "yes"},
        )

    payload = await service.call(
        "sessions.delete",
        {"key": session_key},
        now_ms=int(datetime(2026, 4, 18, 12, 0, tzinfo=UTC).timestamp() * 1000),
    )

    assert payload["ok"] is True
    assert payload["key"] == session_key
    assert payload["deleted"] is True
    assert len(payload["archived"]) == 1
    archived_path = Path(payload["archived"][0])
    assert archived_path.exists()
    archived_lines = archived_path.read_text(encoding="utf-8").splitlines()
    assert len(archived_lines) == 2
    archived_records = [json.loads(line) for line in archived_lines]
    assert [record["role"] for record in archived_records] == ["user", "assistant"]
    assert all(record["sessionKey"] == session_key for record in archived_records)
    assert all(record["reason"] == "deleted" for record in archived_records)
    assert not stale_archive.exists()
    assert recent_archive.exists()
    assert ignored_file.exists()
    assert await database.get_gateway_session_metadata(session_key) is None
    assert await database.count_control_chat_messages(session_key=session_key) == 0
    assert await database.count_control_chat_messages(session_key=other_session_key) == 1

    history_payload = await service.call(
        "chat.history",
        {"sessionKey": session_key, "limit": 10},
    )
    assert history_payload["messages"] == []

    messages_payload = await service.call(
        "sessions.get",
        {"key": session_key, "limit": 10},
    )
    assert messages_payload == {"messages": []}

    sessions_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=777,
    )
    assert [session["key"] for session in sessions_payload["sessions"]] == [main_session_key]

    with pytest.raises(ValueError, match="unknown session key"):
        await service.call("sessions.resolve", {"key": session_key})

    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert [event["payload"]["reason"] for event in sessions_changed] == ["delete"]
    assert sessions_changed[0]["payload"]["sessionKey"] == session_key


@pytest.mark.asyncio
async def test_sessions_compact_archives_trimmed_control_chat_messages_into_checkpoint_inventory(
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compact-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compact.db")
    await database.initialize()
    session_key = "openzues:thread:demo"
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    second_id = await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    third_id = await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )
    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
    )

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compact", {})

    with pytest.raises(ValueError, match="maxLines must be between 1 and 1000000"):
        await service.call("sessions.compact", {"key": session_key, "maxLines": 0})

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key, "maxLines": 2},
        now_ms=1_700_000_000_123,
    )

    assert compacted["ok"] is True
    assert compacted["key"] == session_key
    assert compacted["compacted"] is True
    assert compacted["kept"] == 2
    assert compacted["archivedCount"] == 2
    checkpoint_id = str(compacted["checkpointId"])
    remaining_messages = await database.list_control_chat_messages(
        limit=10,
        session_key=session_key,
    )
    assert [message["id"] for message in remaining_messages] == [third_id]

    inventory = await service.call("sessions.compaction.list", {"key": session_key})

    assert inventory["ok"] is True
    assert inventory["key"] == session_key
    assert inventory["checkpoints"] == [
        {
            "checkpointId": checkpoint_id,
            "sessionKey": session_key,
            "sessionId": session_key,
            "createdAt": 1_700_000_000_123,
            "reason": "manual",
            "summary": "Alpha line 1 Alpha line 2 Bravo line 1",
            "firstKeptEntryId": str(third_id),
            "preCompaction": {
                "sessionId": session_key,
                "entryId": str(second_id),
            },
            "postCompaction": {
                "sessionId": session_key,
                "entryId": str(third_id),
            },
        }
    ]

    checkpoint_payload = await service.call(
        "sessions.compaction.get",
        {"key": session_key, "checkpointId": checkpoint_id},
    )

    assert checkpoint_payload == {
        "ok": True,
        "key": session_key,
        "checkpoint": inventory["checkpoints"][0],
    }
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert len(sessions_changed) == 1
    assert sessions_changed[0]["payload"]["sessionKey"] == session_key
    assert sessions_changed[0]["payload"]["reason"] == "compact"
    assert sessions_changed[0]["payload"]["compacted"] is True
    assert sessions_changed[0]["payload"]["compactionCheckpointCount"] == 1
    assert (
        sessions_changed[0]["payload"]["latestCompactionCheckpoint"]
        == inventory["checkpoints"][0]
    )


@pytest.mark.asyncio
async def test_sessions_compact_without_max_lines_rewrites_history_into_summary_message() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-summary-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-summary.db")
    await database.initialize()
    session_key = "openzues:thread:demo"
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    third_id = await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="user",
        content="Delta line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Echo line 1",
        mission_id=None,
        session_key=session_key,
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
    )

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key},
        now_ms=1_700_000_000_123,
    )

    assert compacted["ok"] is True
    assert compacted["key"] == session_key
    assert compacted["compacted"] is True
    assert compacted["archivedCount"] == 3
    checkpoint_id = str(compacted["checkpointId"])

    remaining_messages = await database.list_control_chat_messages(
        limit=10,
        session_key=session_key,
    )
    assert [message["role"] for message in remaining_messages] == [
        "system",
        "user",
        "assistant",
    ]
    assert remaining_messages[0]["action_kind"] == "compaction_summary"
    assert remaining_messages[0]["content"] == (
        "Compaction summary of earlier turns:\n"
        "Alpha line 1 Alpha line 2 Bravo line 1 Charlie line 1 Charlie line 2"
    )
    assert [message["content"] for message in remaining_messages[1:]] == [
        "Delta line 1",
        "Echo line 1",
    ]

    inventory = await service.call("sessions.compaction.list", {"key": session_key})

    assert inventory["ok"] is True
    assert inventory["key"] == session_key
    assert inventory["checkpoints"] == [
        {
            "checkpointId": checkpoint_id,
            "sessionKey": session_key,
            "sessionId": session_key,
            "createdAt": 1_700_000_000_123,
            "reason": "summary",
            "summary": "Alpha line 1 Alpha line 2 Bravo line 1 Charlie line 1 Charlie line 2",
            "firstKeptEntryId": str(remaining_messages[0]["id"]),
            "preCompaction": {
                "sessionId": session_key,
                "entryId": str(third_id),
            },
            "postCompaction": {
                "sessionId": session_key,
                "entryId": str(remaining_messages[0]["id"]),
            },
        }
    ]
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert len(sessions_changed) == 1
    assert sessions_changed[0]["payload"]["sessionKey"] == session_key
    assert sessions_changed[0]["payload"]["reason"] == "compact"
    assert sessions_changed[0]["payload"]["compacted"] is True
    assert sessions_changed[0]["payload"]["compactionCheckpointCount"] == 1
    assert (
        sessions_changed[0]["payload"]["latestCompactionCheckpoint"]
        == inventory["checkpoints"][0]
    )


@pytest.mark.asyncio
async def test_sessions_compaction_restore_rehydrates_snapshot_after_summary_compaction() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-summary-restore-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-summary-restore.db")
    await database.initialize()
    session_key = "openzues:thread:demo"
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="user",
        content="Delta line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Echo line 1",
        mission_id=None,
        session_key=session_key,
    )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=BroadcastHub(),
    )

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key},
        now_ms=1_700_000_000_123,
    )
    checkpoint_id = str(compacted["checkpointId"])

    await database.append_control_chat_message(
        role="assistant",
        content="Foxtrot line 1",
        mission_id=None,
        session_key=session_key,
    )

    restored = await service.call(
        "sessions.compaction.restore",
        {"key": session_key, "checkpointId": checkpoint_id},
        now_ms=1_700_000_000_456,
    )
    restored_messages = await database.list_control_chat_messages(
        limit=10,
        session_key=session_key,
    )

    assert restored["ok"] is True
    assert restored["key"] == session_key
    assert restored["checkpoint"]["checkpointId"] == checkpoint_id
    assert [message["content"] for message in restored_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
        "Delta line 1",
        "Echo line 1",
    ]


@pytest.mark.asyncio
async def test_sessions_compaction_branch_rehydrates_snapshot_after_summary_compaction() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-summary-branch-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-summary-branch.db")
    await database.initialize()
    session_key = "openzues:thread:demo"
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="user",
        content="Delta line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Echo line 1",
        mission_id=None,
        session_key=session_key,
    )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=BroadcastHub(),
    )

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key},
        now_ms=1_700_000_000_123,
    )
    checkpoint_id = str(compacted["checkpointId"])

    branched = await service.call(
        "sessions.compaction.branch",
        {"key": session_key, "checkpointId": checkpoint_id},
        now_ms=1_700_000_000_456,
    )
    branch_key = str(branched["key"])
    source_messages = await database.list_control_chat_messages(
        limit=10,
        session_key=session_key,
    )
    branch_messages = await database.list_control_chat_messages(
        limit=10,
        session_key=branch_key,
    )

    assert branched["ok"] is True
    assert branched["sourceKey"] == session_key
    assert branched["checkpoint"]["checkpointId"] == checkpoint_id
    assert [message["content"] for message in source_messages] == [
        "Compaction summary of earlier turns:\n"
        "Alpha line 1 Alpha line 2 Bravo line 1 Charlie line 1 Charlie line 2",
        "Delta line 1",
        "Echo line 1",
    ]
    assert [message["content"] for message in branch_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
        "Delta line 1",
        "Echo line 1",
    ]


@pytest.mark.asyncio
async def test_sessions_compaction_restore_rehydrates_snapshot_and_publishes_event() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-restore-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-restore.db")
    await database.initialize()
    session_key = "openzues:thread:demo"
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"traceLevel": "verbose"},
    )
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
    )

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.restore", {})

    with pytest.raises(ValueError, match="checkpointId must be a non-empty string"):
        await service.call(
            "sessions.compaction.restore",
            {"key": session_key},
        )

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key, "maxLines": 2},
        now_ms=1_700_000_000_123,
    )
    checkpoint_id = str(compacted["checkpointId"])

    await database.append_control_chat_message(
        role="assistant",
        content="Delta line 1",
        mission_id=None,
        session_key=session_key,
    )

    restored = await service.call(
        "sessions.compaction.restore",
        {"key": session_key, "checkpointId": checkpoint_id},
        now_ms=1_700_000_000_456,
    )
    restored_messages = await database.list_control_chat_messages(
        limit=10,
        session_key=session_key,
    )
    checkpoint_payload = await service.call(
        "sessions.compaction.get",
        {"key": session_key, "checkpointId": checkpoint_id},
    )

    assert restored["ok"] is True
    assert restored["key"] == session_key
    assert restored["sessionId"] == restored["entry"]["sessionId"]
    assert restored["checkpoint"] == checkpoint_payload["checkpoint"]
    assert restored["entry"]["key"] == session_key
    assert restored["entry"]["kind"] == "thread"
    assert restored["entry"]["traceLevel"] == "verbose"
    assert isinstance(restored["entry"]["updatedAt"], int)
    assert restored["entry"]["updatedAt"] > 0
    assert [message["content"] for message in restored_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
    ]
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert [event["payload"]["reason"] for event in sessions_changed] == [
        "compact",
        "checkpoint-restore",
    ]
    assert sessions_changed[-1]["payload"]["sessionKey"] == session_key
    assert sessions_changed[-1]["payload"]["traceLevel"] == "verbose"


@pytest.mark.asyncio
async def test_sessions_compaction_list_returns_empty_inventory_for_unknown_session() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-list-empty-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-list-empty.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.list", {})

    payload = await service.call("sessions.compaction.list", {"key": "openzues:thread:demo"})

    assert payload == {"ok": True, "key": "openzues:thread:demo", "checkpoints": []}


@pytest.mark.asyncio
async def test_sessions_compaction_get_rejects_unknown_checkpoint() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-get-missing-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-get-missing.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.get", {})

    with pytest.raises(ValueError, match="checkpointId must be a non-empty string"):
        await service.call("sessions.compaction.get", {"key": "openzues:thread:demo"})

    with pytest.raises(ValueError, match="checkpoint not found: checkpoint-001"):
        await service.call(
            "sessions.compaction.get",
            {"key": "openzues:thread:demo", "checkpointId": "checkpoint-001"},
        )


@pytest.mark.asyncio
async def test_sessions_compaction_branch_rehydrates_snapshot_into_new_session_key() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-compaction-branch-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-compaction-branch.db")
    await database.initialize()
    session_key = "openzues:thread:demo"
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"label": "Parity Session", "model": "gpt-5.4-mini"},
    )
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
    )

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.branch", {})

    with pytest.raises(ValueError, match="checkpointId must be a non-empty string"):
        await service.call(
            "sessions.compaction.branch",
            {"key": session_key},
        )

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key, "maxLines": 2},
        now_ms=1_700_000_000_123,
    )
    checkpoint_id = str(compacted["checkpointId"])

    await database.append_control_chat_message(
        role="assistant",
        content="Delta line 1",
        mission_id=None,
        session_key=session_key,
    )

    branched = await service.call(
        "sessions.compaction.branch",
        {"key": session_key, "checkpointId": checkpoint_id},
        now_ms=1_700_000_000_789,
    )
    branch_key = branched["key"]
    source_messages = await database.list_control_chat_messages(limit=10, session_key=session_key)
    branch_messages = await database.list_control_chat_messages(limit=10, session_key=branch_key)
    branch_metadata = await database.get_gateway_session_metadata(branch_key)
    checkpoint_payload = await service.call(
        "sessions.compaction.get",
        {"key": session_key, "checkpointId": checkpoint_id},
    )

    assert branched["ok"] is True
    assert branched["sourceKey"] == session_key
    assert branch_key != session_key
    assert branched["sessionId"] == branched["entry"]["sessionId"]
    assert branched["checkpoint"] == checkpoint_payload["checkpoint"]
    assert branched["entry"]["key"] == branch_key
    assert branched["entry"]["kind"] == "thread"
    assert branched["entry"]["label"] == "Parity Session (checkpoint)"
    assert branched["entry"]["parentSessionKey"] == session_key
    assert branched["entry"]["model"] == "gpt-5.4-mini"
    assert isinstance(branched["entry"]["updatedAt"], int)
    assert branched["entry"]["updatedAt"] > 0
    assert [message["content"] for message in source_messages] == [
        "Charlie line 1\nCharlie line 2",
        "Delta line 1",
    ]
    assert [message["content"] for message in branch_messages] == [
        "Alpha line 1\nAlpha line 2",
        "Bravo line 1",
        "Charlie line 1\nCharlie line 2",
    ]
    assert branch_metadata is not None
    assert branch_metadata["metadata"] == {
        "label": "Parity Session (checkpoint)",
        "model": "gpt-5.4-mini",
        "parentSessionKey": session_key,
    }
    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert [event["payload"]["reason"] for event in sessions_changed] == [
        "compact",
        "checkpoint-branch",
        "checkpoint-branch",
    ]
    assert sessions_changed[-2]["payload"]["sessionKey"] == session_key
    assert sessions_changed[-1]["payload"]["sessionKey"] == branch_key


@pytest.mark.asyncio
async def test_sessions_preview_returns_current_session_items_and_missing_unknown_key() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-preview-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-preview.db")
    await database.initialize()
    session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.append_control_chat_message(
        role="user",
        content="Ship parity.",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Preview ready.",
        mission_id=None,
        session_key=session_key,
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="keys must be a non-empty string array"):
        await service.call("sessions.preview", {})

    with pytest.raises(ValueError, match="maxChars must be between 20 and 1000000"):
        await service.call(
            "sessions.preview",
            {"keys": ["openzues:thread:demo"], "maxChars": 10},
        )

    payload = await service.call(
        "sessions.preview",
        {"keys": [session_key, "openzues:thread:missing"], "limit": 12, "maxChars": 240},
        now_ms=111,
    )

    assert payload == {
        "ts": 111,
        "previews": [
            {
                "key": session_key,
                "status": "ok",
                "items": [
                    {"role": "user", "text": "Ship parity."},
                    {"role": "assistant", "text": "Preview ready."},
                ],
            },
            {
                "key": "openzues:thread:missing",
                "status": "missing",
                "items": [],
            },
        ],
    }


@pytest.mark.asyncio
async def test_push_test_fails_as_missing_apns_registration() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=r"node ios-node-1 has no APNs registration \(connect iOS node first\)",
    ) as exc_info:
        await service.call(
            "push.test",
            {
                "nodeId": "ios-node-1",
                "title": "OpenZues",
                "body": "Push parity ping.",
                "environment": "production",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_connect_fails_as_explicit_invalid_request() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="connect is only valid as the first request",
    ) as exc_info:
        await service.call("connect", {})

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params"),
    [
        (
            "web.login.start",
            {
                "force": True,
                "timeoutMs": 30_000,
                "verbose": True,
                "accountId": "telegram-primary",
            },
        ),
        (
            "web.login.wait",
            {
                "timeoutMs": 30_000,
                "accountId": "telegram-primary",
            },
        ),
    ],
)
async def test_web_login_methods_fail_as_explicit_provider_unavailable(
    method: str,
    params: dict[str, object],
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="web login provider is not available",
    ) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params"),
    [
        (
            "web.login.start",
            {
                "force": True,
                "timeoutMs": 30_000,
                "verbose": True,
                "accountId": "   ",
            },
        ),
        (
            "web.login.wait",
            {
                "timeoutMs": 30_000,
                "accountId": "   ",
            },
        ),
    ],
)
async def test_web_login_methods_allow_blank_account_id(
    method: str,
    params: dict[str, object],
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="web login provider is not available",
    ) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_channels_logout_allows_blank_account_id() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="channel telegram does not support logout",
    ) as exc_info:
        await service.call(
            "channels.logout",
            {
                "channel": "telegram",
                "accountId": "   ",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_channels_logout_rejects_blank_channel_as_invalid_params() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=r"invalid channels\.logout params:",
    ) as exc_info:
        await service.call(
            "channels.logout",
            {
                "channel": "   ",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_channels_logout_fails_as_explicit_unsupported_channel() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="channel telegram does not support logout",
    ) as exc_info:
        await service.call(
            "channels.logout",
            {
                "channel": "telegram",
                "accountId": "primary",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_channels_logout_rejects_invalid_channel_shape() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="invalid channels.logout channel",
    ) as exc_info:
        await service.call(
            "channels.logout",
            {
                "channel": "not-a-real-channel",
                "accountId": "primary",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_logs_tail_returns_latest_workspace_log_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    older = logs_root / "openzues-older.log"
    newer = logs_root / "openzues-newer.log"
    older.write_text("old line\n", encoding="utf-8")
    newer.write_text("new line\n", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, None)

    service = GatewayNodeMethodService(GatewayNodeRegistry())
    payload = await service.call(
        "logs.tail",
        {
            "limit": 10,
            "maxBytes": 1_000,
        },
    )

    assert payload == {
        "file": str(newer),
        "cursor": newer.stat().st_size,
        "size": newer.stat().st_size,
        "lines": ["new line"],
        "truncated": False,
        "reset": False,
    }


@pytest.mark.asyncio
async def test_update_run_triggers_runtime_update_tick_and_returns_fresh_view() -> None:
    payload: dict[str, object] = {
        "headline": "Runtime self-update is watching the repo",
        "summary": "The current process is aligned with the checked-out repo revision.",
        "enabled": True,
        "repo_root": "C:/workspace/OpenZues",
        "startup_revision": "rev-a",
        "current_revision": "rev-a",
        "pending_revision": None,
        "pending_restart": False,
        "restart_in_progress": False,
        "safe_to_restart": True,
        "last_checked_at": None,
        "last_restart_at": None,
        "last_error": None,
        "auto_restart": True,
    }
    tick_calls: list[str] = []

    async def fake_tick() -> bool:
        tick_calls.append("tick")
        payload.update(
            {
                "headline": "A newer repo revision is waiting for a safe boundary",
                "summary": (
                    "OpenZues sees a newer checked-out revision, but it is still waiting "
                    "for live missions to reach a restart-safe checkpoint."
                ),
                "current_revision": "rev-b",
                "pending_revision": "rev-b",
                "pending_restart": True,
                "safe_to_restart": False,
                "last_checked_at": "2026-04-18T16:20:00Z",
            }
        )
        return False

    async def fake_view() -> dict[str, object]:
        return dict(payload)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        runtime_update_tick=fake_tick,
        runtime_update_view=fake_view,
    )
    result = await service.call("update.run", {})

    assert tick_calls == ["tick"]
    assert result == payload


@pytest.mark.asyncio
async def test_update_run_accepts_upstream_optional_restart_request_params() -> None:
    payload: dict[str, object] = {
        "headline": "Runtime self-update is watching the repo",
        "summary": "The current process is aligned with the checked-out repo revision.",
        "enabled": True,
        "repo_root": "C:/workspace/OpenZues",
        "startup_revision": "rev-a",
        "current_revision": "rev-a",
        "pending_revision": None,
        "pending_restart": False,
        "restart_in_progress": False,
        "safe_to_restart": True,
        "last_checked_at": "2026-04-19T01:02:03Z",
        "last_restart_at": None,
        "last_error": None,
        "auto_restart": True,
    }
    tick_calls: list[str] = []

    async def fake_tick() -> bool:
        tick_calls.append("tick")
        return False

    async def fake_view() -> dict[str, object]:
        return dict(payload)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        runtime_update_tick=fake_tick,
        runtime_update_view=fake_view,
    )
    result = await service.call(
        "update.run",
        {
            "sessionKey": "agent:main:thread:demo",
            "deliveryContext": {
                "channel": "slack",
                "to": "user:U123",
                "accountId": "default",
                "threadId": 1771242986529939,
            },
            "note": "Restart after the bounded parity patch.",
            "restartDelayMs": 0,
            "timeoutMs": 5_000,
        },
    )

    assert tick_calls == ["tick"]
    assert result == payload


@pytest.mark.asyncio
async def test_wizard_methods_drive_bounded_gateway_wizard_runtime() -> None:
    state: dict[str, object] = {
        "mode": "local",
        "project_path": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        wizard_service=GatewayWizardService(
            load_session=load_session,
            save_session=save_session,
        ),
    )

    start = await service.call(
        "wizard.start",
        {"mode": "remote", "workspace": "C:/workspace/OpenZues"},
    )
    session_id = start["sessionId"]
    step = start["step"]

    assert isinstance(session_id, str)
    assert start["done"] is False
    assert start["status"] == "running"
    assert step == {
        "id": step["id"],
        "type": "text",
        "title": "Task Name",
        "message": "Name the recurring setup task.",
        "executor": "client",
    }

    status = await service.call("wizard.status", {"sessionId": session_id})
    assert status == {"status": "running"}

    done = await service.call(
        "wizard.next",
        {
            "sessionId": session_id,
            "answer": {
                "stepId": step["id"],
                "value": "Parity Loop",
            },
        },
    )

    assert done == {"done": True, "status": "done"}
    assert state == {
        "flow": "advanced",
        "mode": "remote",
        "project_path": "C:/workspace/OpenZues",
        "task_name": "Parity Loop",
    }

    with pytest.raises(ValueError, match="wizard not found"):
        await service.call("wizard.status", {"sessionId": session_id})


@pytest.mark.asyncio
async def test_wizard_cancel_discards_unapplied_draft() -> None:
    state: dict[str, object] = {
        "mode": "local",
        "project_path": None,
        "task_name": None,
    }

    async def load_session() -> dict[str, object]:
        return dict(state)

    async def save_session(patch: dict[str, object]) -> dict[str, object]:
        state.update(patch)
        return dict(state)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        wizard_service=GatewayWizardService(
            load_session=load_session,
            save_session=save_session,
        ),
    )

    start = await service.call("wizard.start", {})
    session_id = start["sessionId"]

    assert start["done"] is False
    assert start["status"] == "running"
    assert start["step"] == {
        "id": start["step"]["id"],
        "type": "text",
        "title": "Workspace",
        "message": "Enter the workspace path to stage for setup.",
        "placeholder": "C:/workspace",
        "executor": "client",
    }

    cancel = await service.call("wizard.cancel", {"sessionId": session_id})

    assert cancel == {"status": "cancelled", "error": "cancelled"}
    assert state == {
        "mode": "local",
        "project_path": None,
        "task_name": None,
    }


@pytest.mark.asyncio
async def test_sessions_messages_subscribe_returns_stateless_ack_without_connection_context() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.messages.subscribe", {})

    payload = await service.call(
        "sessions.messages.subscribe",
        {"key": "  MAIN  "},
    )

    assert payload == {"subscribed": False, "key": "agent:main:main"}


@pytest.mark.asyncio
async def test_sessions_messages_unsubscribe_returns_stateless_ack_without_connection_context() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.messages.unsubscribe", {})

    payload = await service.call(
        "sessions.messages.unsubscribe",
        {"key": "  MAIN  "},
    )

    assert payload == {"subscribed": False, "key": "agent:main:main"}


@pytest.mark.asyncio
async def test_sessions_messages_subscribe_filters_by_client_id() -> None:
    hub = BroadcastHub()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), hub=hub)

    async with hub.subscribe(client_id="client-1") as subscribed_queue:
        async with hub.subscribe(client_id="client-2") as other_queue:
            payload = await service.call(
                "sessions.messages.subscribe",
                {"key": "  MAIN  "},
                requester=GatewayNodeMethodRequester(client_id="client-1"),
            )

            assert payload == {"subscribed": True, "key": "agent:main:main"}

            await hub.publish(
                {
                    "type": "gateway_event",
                    "event": "session.message",
                    "payload": {"sessionKey": "agent:main:main"},
                    "createdAt": utcnow(),
                }
            )

            delivered = await asyncio.wait_for(subscribed_queue.get(), timeout=0.2)
            assert delivered["event"] == "session.message"
            assert delivered["payload"]["sessionKey"] == "agent:main:main"
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(other_queue.get(), timeout=0.05)

            await hub.publish(
                {
                    "type": "gateway_event",
                    "event": "session.message",
                    "payload": {"sessionKey": "launch:mode:workspace_affinity"},
                    "createdAt": utcnow(),
                }
            )

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(subscribed_queue.get(), timeout=0.05)

            payload = await service.call(
                "sessions.messages.unsubscribe",
                {"key": "  MAIN  "},
                requester=GatewayNodeMethodRequester(client_id="client-1"),
            )

            assert payload == {"subscribed": False, "key": "agent:main:main"}

            await hub.publish(
                {
                    "type": "gateway_event",
                    "event": "session.message",
                    "payload": {"sessionKey": "agent:main:main"},
                    "createdAt": utcnow(),
                }
            )

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(subscribed_queue.get(), timeout=0.05)


@pytest.mark.asyncio
async def test_sessions_subscribe_returns_stateless_ack_without_connection_context() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("sessions.subscribe", {})

    assert payload == {"subscribed": False}


@pytest.mark.asyncio
async def test_sessions_subscribe_registers_client_scoped_filter_when_client_id_present() -> None:
    hub = BroadcastHub()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), hub=hub)

    async with hub.subscribe(client_id="client-1") as subscribed_queue:
        async with hub.subscribe(client_id="client-2") as other_queue:
            payload = await service.call(
                "sessions.subscribe",
                {},
                requester=GatewayNodeMethodRequester(client_id="client-1"),
            )

            assert payload == {"subscribed": True}

            await hub.publish(
                {
                    "type": "gateway_event",
                    "event": "sessions.changed",
                    "payload": {"sessionKey": "agent:main:main", "reason": "send"},
                    "createdAt": utcnow(),
                }
            )

            delivered = await asyncio.wait_for(subscribed_queue.get(), timeout=0.2)
            assert delivered["event"] == "sessions.changed"
            assert delivered["payload"]["reason"] == "send"
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(other_queue.get(), timeout=0.05)

            payload = await service.call(
                "sessions.unsubscribe",
                {},
                requester=GatewayNodeMethodRequester(client_id="client-1"),
            )

            assert payload == {"subscribed": False}

            await hub.publish(
                {
                    "type": "gateway_event",
                    "event": "sessions.changed",
                    "payload": {"sessionKey": "agent:main:main", "reason": "patch"},
                    "createdAt": utcnow(),
                }
            )

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(subscribed_queue.get(), timeout=0.05)


@pytest.mark.asyncio
async def test_sessions_unsubscribe_returns_stateless_ack_without_connection_context() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("sessions.unsubscribe", {})

    assert payload == {"subscribed": False}


@pytest.mark.asyncio
async def test_sessions_create_registers_metadata_session_and_sends_initial_message() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-create-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-create.db")
    await database.initialize()

    class _RecordingBroadcastHub(BroadcastHub):
        def __init__(self) -> None:
            super().__init__()
            self.published_events: list[dict[str, object]] = []

        async def publish(self, event: dict[str, object]) -> None:
            self.published_events.append(dict(event))
            await super().publish(event)

    hub = _RecordingBroadcastHub()
    observed_send: dict[str, object] = {}
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    created_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-created-1",
    ).session_key

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": "run-created-session-1", "status": "ok"}

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        hub=hub,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
    )

    with pytest.raises(ValueError, match="task must be a string"):
        await service.call("sessions.create", {"task": 1})

    with pytest.raises(
        ValueError,
        match="unknown parent session: launch:mode:workspace_affinity:thread:missing",
    ):
        await service.call(
            "sessions.create",
            {"parentSessionKey": "launch:mode:workspace_affinity:thread:missing"},
        )

    payload = await service.call(
        "sessions.create",
        {
            "key": created_session_key,
            "label": "Parity Session",
            "model": "gpt-5.4-mini",
            "parentSessionKey": main_session_key,
            "message": "Ship parity.",
        },
        now_ms=222,
    )

    assert observed_send["session_key"] == created_session_key
    assert observed_send["message"] == "Ship parity."
    assert observed_send["thinking"] is None
    assert observed_send["deliver"] is None
    assert observed_send["timeout_ms"] is None
    assert isinstance(observed_send["idempotency_key"], str)
    assert observed_send["idempotency_key"]

    assert payload["ok"] is True
    assert payload["key"] == created_session_key
    assert payload["sessionId"] == "thread-created-1"
    assert payload["runStarted"] is True
    assert payload["runId"] == "run-created-session-1"
    assert payload["status"] == "ok"
    assert payload["entry"]["key"] == created_session_key
    assert payload["entry"]["kind"] == "thread"
    assert payload["entry"]["displayName"] == "OpenZues Control Chat Thread"
    assert payload["entry"]["sessionId"] == "thread-created-1"
    assert payload["entry"]["modelProvider"] == "openai"
    assert payload["entry"]["model"] == "gpt-5.4-mini"
    assert payload["entry"]["label"] == "Parity Session"
    assert payload["entry"]["parentSessionKey"] == main_session_key
    assert isinstance(payload["entry"]["updatedAt"], int)
    assert payload["entry"]["updatedAt"] > 0

    metadata_row = await database.get_gateway_session_metadata(created_session_key)
    assert metadata_row is not None
    assert metadata_row["metadata"] == {
        "label": "Parity Session",
        "model": "gpt-5.4-mini",
        "parentSessionKey": main_session_key,
    }

    resolve_payload = await service.call("sessions.resolve", {"key": created_session_key})
    assert resolve_payload == {"ok": True, "key": created_session_key}

    sessions_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=333,
    )
    assert [session["key"] for session in sessions_payload["sessions"]] == [
        main_session_key,
        created_session_key,
    ]

    sessions_changed = [
        event
        for event in hub.published_events
        if event.get("type") == "gateway_event" and event.get("event") == "sessions.changed"
    ]
    assert [event["payload"]["reason"] for event in sessions_changed] == ["create", "send"]
    assert sessions_changed[0]["payload"]["sessionKey"] == created_session_key
    assert sessions_changed[1]["payload"]["sessionKey"] == created_session_key


@pytest.mark.asyncio
async def test_sessions_patch_persists_current_session_metadata_and_surfaces_it() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-patch-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-patch.db")
    await database.initialize()
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Patch the live control chat session.",
        session_key=current_session_key,
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="responseUsage must be one of: full, off, on, tokens"):
        await service.call(
            "sessions.patch",
            {
                "key": current_session_key,
                "responseUsage": "broken",
            },
        )

    payload = await service.call(
        "sessions.patch",
        {
            "key": current_session_key,
            "label": "Parity Session",
            "thinkingLevel": "low",
            "fastMode": True,
            "verboseLevel": "high",
            "traceLevel": "debug",
            "responseUsage": "tokens",
            "model": "gpt-5.4-mini",
        },
        now_ms=222,
    )

    assert payload["ok"] is True
    assert payload["path"] == str(database.path)
    assert payload["key"] == current_session_key
    assert payload["resolved"] == {"modelProvider": "openai", "model": "gpt-5.4-mini"}
    assert payload["entry"]["key"] == current_session_key
    assert payload["entry"]["label"] == "Parity Session"
    assert payload["entry"]["thinkingLevel"] == "low"
    assert payload["entry"]["fastMode"] is True
    assert payload["entry"]["verboseLevel"] == "high"
    assert payload["entry"]["traceLevel"] == "debug"
    assert payload["entry"]["responseUsage"] == "tokens"
    assert payload["entry"]["model"] == "gpt-5.4-mini"

    sessions_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=333,
    )
    assert sessions_payload["sessions"] == [
        {
            "key": current_session_key,
            "kind": "global",
            "displayName": "OpenZues Control Chat",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": sessions_payload["sessions"][0]["updatedAt"],
            "sessionId": None,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": "low",
            "fastMode": True,
            "verboseLevel": "high",
            "traceLevel": "debug",
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4-mini",
            "contextTokens": None,
            "label": "Parity Session",
            "responseUsage": "tokens",
        }
    ]

    history_payload = await service.call(
        "chat.history",
        {"sessionKey": current_session_key, "limit": 5},
    )
    assert history_payload["thinkingLevel"] == "low"
    assert history_payload["fastMode"] is True
    assert history_payload["verboseLevel"] == "high"
    assert history_payload["traceLevel"] == "debug"


@pytest.mark.asyncio
async def test_sessions_usage_returns_bounded_summary_from_latest_persisted_mission() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-usage-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    with pytest.raises(ValueError, match="mode must be one of: gateway, specific, utc"):
        await service.call("sessions.usage", {"mode": "broken"})

    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-usage-service",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"label": "Parity Usage Session"},
    )
    await database.append_control_chat_message(
        role="user",
        content="Please summarize the latest session usage.",
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The latest persisted mission totals are ready.",
        session_key=session_key,
    )
    mission_id = await database.create_mission(
        name="Usage parity summary",
        objective="Summarize the current usage seam.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-service",
        session_key=session_key,
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        mission_id,
        total_tokens=1200,
        output_tokens=220,
        reasoning_tokens=90,
    )

    payload = await service.call(
        "sessions.usage",
        {
            "key": session_key,
            "startDate": "2026-04-01",
            "endDate": "2026-04-18",
            "mode": "specific",
            "utcOffset": "UTC-5",
            "limit": 50,
            "includeContextWeight": False,
        },
    )

    assert payload["startDate"] == "2026-04-01"
    assert payload["endDate"] == "2026-04-18"
    assert payload["totals"]["totalTokens"] == 1200
    assert payload["aggregates"]["messages"] == {
        "total": 2,
        "user": 1,
        "assistant": 1,
        "toolCalls": 0,
        "toolResults": 0,
        "errors": 0,
    }
    assert payload["aggregates"]["tools"] == {
        "totalCalls": 0,
        "uniqueTools": 0,
        "tools": [],
    }
    assert len(payload["sessions"]) == 1
    session_payload = payload["sessions"][0]
    assert session_payload["key"] == session_key
    assert session_payload["label"] == "Parity Usage Session"
    assert session_payload["sessionId"] == "thread-usage-service"
    assert session_payload["modelProvider"] == "openai"
    assert session_payload["model"] == "gpt-5.4"
    assert session_payload["usage"]["totalTokens"] == 1200
    assert session_payload["usage"]["output"] == 220
    assert session_payload["usage"]["missingCostEntries"] == 1
    assert session_payload["usage"]["messageCounts"] == {
        "total": 2,
        "user": 1,
        "assistant": 1,
        "toolCalls": 0,
        "toolResults": 0,
        "errors": 0,
    }


@pytest.mark.asyncio
async def test_sessions_usage_timeseries_returns_bounded_mission_points_for_session() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-usage-timeseries-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.usage.timeseries", {})

    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-usage-timeseries-service",
    ).session_key

    first_mission_id = await database.create_mission(
        name="Usage timeseries first slice",
        objective="Record the first bounded usage point.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-timeseries-service",
        session_key=session_key,
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        first_mission_id,
        total_tokens=300,
        output_tokens=80,
    )

    second_mission_id = await database.create_mission(
        name="Usage timeseries second slice",
        objective="Record the second bounded usage point.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-timeseries-service",
        session_key=session_key,
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        second_mission_id,
        total_tokens=700,
        output_tokens=180,
    )

    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-usage-timeseries-other",
    ).session_key
    other_mission_id = await database.create_mission(
        name="Usage timeseries noise",
        objective="Stay out of the selected usage timeseries.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-timeseries-other",
        session_key=other_session_key,
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        other_mission_id,
        total_tokens=999,
        output_tokens=333,
    )

    payload = await service.call(
        "sessions.usage.timeseries",
        {"key": session_key},
    )

    assert payload["sessionId"] == "thread-usage-timeseries-service"
    assert len(payload["points"]) == 2
    assert payload["points"][0] == {
        "timestamp": payload["points"][0]["timestamp"],
        "input": 220,
        "output": 80,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 300,
        "cost": 0.0,
        "cumulativeTokens": 300,
        "cumulativeCost": 0.0,
    }
    assert payload["points"][1] == {
        "timestamp": payload["points"][1]["timestamp"],
        "input": 520,
        "output": 180,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 700,
        "cost": 0.0,
        "cumulativeTokens": 1000,
        "cumulativeCost": 0.0,
    }
    assert payload["points"][0]["timestamp"] <= payload["points"][1]["timestamp"]


@pytest.mark.asyncio
async def test_sessions_usage_logs_returns_bounded_transcript_entries_with_linked_usage() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-usage-logs-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    with pytest.raises(ValueError, match="limit must be between 1 and 1000"):
        await service.call("sessions.usage.logs", {"key": "openzues:thread:demo", "limit": 0})

    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-usage-logs-service",
    ).session_key

    await database.append_control_chat_message(
        role="user",
        content="Please show the bounded usage logs.",
        session_key=session_key,
    )

    mission_id = await database.create_mission(
        name="Usage log slice",
        objective="Link the assistant reply back to bounded mission usage.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-logs-service",
        session_key=session_key,
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        mission_id,
        total_tokens=640,
        output_tokens=160,
    )

    await database.append_control_chat_message(
        role="assistant",
        content="Here is the latest bounded usage log entry.",
        mission_id=mission_id,
        session_key=session_key,
    )

    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-usage-logs-other",
    ).session_key
    await database.append_control_chat_message(
        role="assistant",
        content="Noise from another session.",
        session_key=other_session_key,
    )

    payload = await service.call(
        "sessions.usage.logs",
        {"key": session_key, "limit": 10},
    )

    assert payload["sessionId"] == "thread-usage-logs-service"
    assert payload["entries"] == [
        {
            "timestamp": payload["entries"][0]["timestamp"],
            "role": "user",
            "content": "Please show the bounded usage logs.",
        },
        {
            "timestamp": payload["entries"][1]["timestamp"],
            "role": "assistant",
            "content": "Here is the latest bounded usage log entry.",
            "tokens": 640,
        },
    ]
    assert payload["entries"][0]["timestamp"] <= payload["entries"][1]["timestamp"]


@pytest.mark.asyncio
async def test_usage_cost_returns_bounded_daily_rollup_for_date_range() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-usage-cost-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    first_mission_id = await database.create_mission(
        name="Usage cost first slice",
        objective="Count the first bounded daily usage total.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-cost-1",
        session_key="openzues:thread:usage-cost-1",
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        first_mission_id,
        total_tokens=300,
        output_tokens=80,
    )

    second_mission_id = await database.create_mission(
        name="Usage cost second slice",
        objective="Count the second bounded daily usage total.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-cost-2",
        session_key="openzues:thread:usage-cost-2",
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        second_mission_id,
        total_tokens=700,
        output_tokens=180,
    )

    out_of_range_mission_id = await database.create_mission(
        name="Usage cost out-of-range slice",
        objective="Stay outside the bounded date window.",
        status="completed",
        instance_id=7,
        project_id=None,
        thread_id="thread-usage-cost-3",
        session_key="openzues:thread:usage-cost-3",
        conversation_target=None,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    await database.update_mission(
        out_of_range_mission_id,
        total_tokens=999,
        output_tokens=333,
    )

    with sqlite3.connect(database.path) as conn:
        conn.execute(
            "UPDATE missions SET created_at = ?, updated_at = ? WHERE id = ?",
            ("2026-04-15T12:00:00+00:00", "2026-04-15T12:00:00+00:00", first_mission_id),
        )
        conn.execute(
            "UPDATE missions SET created_at = ?, updated_at = ? WHERE id = ?",
            ("2026-04-16T18:30:00+00:00", "2026-04-16T18:30:00+00:00", second_mission_id),
        )
        conn.execute(
            "UPDATE missions SET created_at = ?, updated_at = ? WHERE id = ?",
            (
                "2026-04-18T08:00:00+00:00",
                "2026-04-18T08:00:00+00:00",
                out_of_range_mission_id,
            ),
        )
        conn.commit()

    payload = await service.call(
        "usage.cost",
        {
            "startDate": "2026-04-15",
            "endDate": "2026-04-16",
            "mode": "utc",
        },
    )

    assert payload["days"] == 2
    assert payload["daily"] == [
        {
            "date": "2026-04-15",
            "input": 220,
            "output": 80,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 300,
            "totalCost": 0.0,
            "inputCost": 0.0,
            "outputCost": 0.0,
            "cacheReadCost": 0.0,
            "cacheWriteCost": 0.0,
            "missingCostEntries": 1,
        },
        {
            "date": "2026-04-16",
            "input": 520,
            "output": 180,
            "cacheRead": 0,
            "cacheWrite": 0,
            "totalTokens": 700,
            "totalCost": 0.0,
            "inputCost": 0.0,
            "outputCost": 0.0,
            "cacheReadCost": 0.0,
            "cacheWriteCost": 0.0,
            "missingCostEntries": 1,
        },
    ]
    assert payload["totals"] == {
        "input": 740,
        "output": 260,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 1000,
        "totalCost": 0.0,
        "inputCost": 0.0,
        "outputCost": 0.0,
        "cacheReadCost": 0.0,
        "cacheWriteCost": 0.0,
        "missingCostEntries": 2,
    }


@pytest.mark.asyncio
async def test_usage_status_returns_truthful_provider_inventory_with_telemetry_gap() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("usage.status")

    assert payload == {
        "updatedAt": payload["updatedAt"],
        "providers": [
            {
                "provider": "openai",
                "displayName": "openai",
                "windows": [],
                "plan": None,
                "error": "Quota telemetry is not available in OpenZues yet.",
            }
        ],
    }


@pytest.mark.asyncio
async def test_chat_abort_fails_as_explicit_unavailable_until_runtime_is_wired() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="sessionKey must be a non-empty string"):
        await service.call("chat.abort", {})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "chat.abort",
            {"sessionKey": "openzues:thread:demo", "runId": "run-chat-send-1"},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "chat.abort is unavailable until control chat cancellation is wired"
    )


@pytest.mark.asyncio
async def test_agent_wait_waits_for_tracked_gateway_run_completion() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-wait-ok-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-wait-ok.db")
    await database.initialize()
    session_key = "openzues:thread:agent-wait-ok"
    mission_id = await database.create_mission(
        name="Gateway Agent Wait Loop",
        objective="Wait for the tracked gateway run to finish.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-wait-ok",
        session_key=session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Tracked gateway wait completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    send_payload = await service.call(
        "sessions.send",
        {
            "key": session_key,
            "message": "continue",
            "idempotencyKey": "run-agent-wait-ok-1",
        },
        now_ms=111,
    )
    assert send_payload == {"runId": "run-agent-wait-ok-1", "status": "ok"}

    payload = await service.call(
        "agent.wait",
        {
            "runId": "run-agent-wait-ok-1",
            "timeoutMs": 5,
        },
    )

    assert payload["runId"] == "run-agent-wait-ok-1"
    assert payload["status"] == "ok"
    assert payload["startedAt"] == 111
    assert isinstance(payload["endedAt"], int)
    assert payload["endedAt"] >= payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_wait_returns_failed_terminal_snapshot_for_tracked_run() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-wait-error-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-wait-error.db")
    await database.initialize()
    session_key = "openzues:thread:agent-wait-error"
    mission_id = await database.create_mission(
        name="Gateway Agent Wait Failure Loop",
        objective="Surface the tracked gateway failure snapshot.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-wait-error",
        session_key=session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        del session_key, message, thinking, deliver, timeout_ms
        return {"runId": idempotency_key, "status": "ok"}

    await database.update_mission(
        mission_id,
        status="failed",
        in_progress=0,
        phase="failed",
        last_error="Gateway parity run failed on verification.",
    )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        chat_send_service=fake_chat_send_service,
    )

    send_payload = await service.call(
        "sessions.send",
        {
            "key": session_key,
            "message": "continue",
            "idempotencyKey": "run-agent-wait-error-1",
        },
        now_ms=222,
    )
    assert send_payload == {"runId": "run-agent-wait-error-1", "status": "ok"}

    payload = await service.call(
        "agent.wait",
        {
            "runId": "run-agent-wait-error-1",
            "timeoutMs": 0,
        },
    )

    assert payload["runId"] == "run-agent-wait-error-1"
    assert payload["status"] == "error"
    assert payload["startedAt"] == 222
    assert isinstance(payload["endedAt"], int)
    assert payload["endedAt"] >= payload["startedAt"]
    assert payload["error"] == "Gateway parity run failed on verification."


@pytest.mark.asyncio
async def test_agent_launches_bounded_main_session_run_and_wait_completes() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-main-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-main.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Launch Loop",
        objective="Launch the next parity slice through the main control-chat session.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-main",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "idempotencyKey": "agent-run-1",
        },
        now_ms=321,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert launch_payload["acceptedAt"] >= 321

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 321
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launches_bounded_session_id_selected_run_and_wait_completes() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-session-id-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-session-id.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-agent-launch-session-id",
    ).session_key
    mission_id = await database.create_mission(
        name="Gateway Agent SessionId Launch Loop",
        objective="Launch parity through a sessionId-selected control-chat thread.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-session-id",
        session_key=thread_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent sessionId launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "sessionId": "thread-agent-launch-session-id",
            "idempotencyKey": "agent-run-session-id-1",
        },
        now_ms=654,
    )

    assert observed_send == {
        "session_key": thread_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-session-id-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-session-id-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert launch_payload["acceptedAt"] >= 654

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-session-id-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-session-id-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 654
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launches_bounded_main_session_run_and_persists_session_label() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-label-persist-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-label-persist.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Label Persist Loop",
        objective="Launch parity while persisting the requested session label.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-label-persist",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.upsert_gateway_session_metadata(
        session_key=main_session_key,
        metadata={"model": "gpt-5.4-mini"},
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent label persistence completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "label": "Parity Worker",
            "idempotencyKey": "agent-run-label-persist-1",
        },
        now_ms=987,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-label-persist-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-label-persist-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert launch_payload["acceptedAt"] >= 987
    metadata_row = await database.get_gateway_session_metadata(main_session_key)
    assert isinstance(metadata_row, dict)
    metadata = metadata_row.get("metadata")
    assert isinstance(metadata, dict)
    assert metadata["label"] == "Parity Worker"
    assert metadata["model"] == "gpt-5.4-mini"

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-label-persist-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-label-persist-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 987
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launches_bounded_main_session_run_with_explicit_non_delivery() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-deliver-false-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-deliver-false.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Deliver False Loop",
        objective="Launch parity while keeping delivery explicitly disabled.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-deliver-false",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent explicit non-delivery launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "deliver": False,
            "idempotencyKey": "agent-run-deliver-false-1",
        },
        now_ms=1597,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-deliver-false-1",
        "thinking": None,
        "deliver": False,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-deliver-false-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert launch_payload["acceptedAt"] >= 1597

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-deliver-false-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-deliver-false-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 1597
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launches_bounded_main_session_run_with_best_effort_deliver_false() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-best-effort-false-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-best-effort-false.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Best Effort False Loop",
        objective="Launch parity while keeping best-effort delivery explicitly disabled.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-best-effort-false",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent best-effort false launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "bestEffortDeliver": False,
            "idempotencyKey": "agent-run-best-effort-false-1",
        },
        now_ms=2337,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-best-effort-false-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-best-effort-false-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert launch_payload["acceptedAt"] >= 2337

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-best-effort-false-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-best-effort-false-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 2337
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_rejects_malformed_session_keys_before_session_lookup() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=Database(Path.cwd() / ".tmp-pytest-local" / "noop-agent-malformed.db"),
        sessions_service=None,
        chat_send_service=None,
    )

    with pytest.raises(
        ValueError,
        match='invalid agent params: malformed session key "agent::main"',
    ):
        await service.call(
            "agent",
            {
                "message": "Ship the next verified slice.",
                "agentId": "main",
                "sessionKey": "agent::main",
                "idempotencyKey": "agent-run-malformed-session-key-1",
                },
            )


@pytest.mark.asyncio
async def test_agent_rejects_agent_id_that_conflicts_with_session_key_agent() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=Database(Path.cwd() / ".tmp-pytest-local" / "noop-agent-mismatch.db"),
        sessions_service=None,
        chat_send_service=None,
    )

    with pytest.raises(
        ValueError,
        match='invalid agent params: agent "main" does not match session key agent "other-agent"',
    ):
        await service.call(
            "agent",
            {
                "message": "Ship the next verified slice.",
                "agentId": "main",
                "sessionKey": "agent:other-agent:main",
                "idempotencyKey": "agent-run-session-key-agent-mismatch-1",
                },
            )


@pytest.mark.asyncio
async def test_agent_launch_accepts_matching_session_key_and_session_id_selectors() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-matching-key-session-id"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-matching-key-session-id.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-agent-matching-key-session-id",
    ).session_key
    mission_id = await database.create_mission(
        name="Gateway Agent Matching Key SessionId Loop",
        objective="Launch parity through matching sessionKey and sessionId selectors.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-matching-key-session-id",
        session_key=thread_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent matching session selectors completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "sessionKey": thread_session_key,
            "sessionId": "thread-agent-matching-key-session-id",
            "idempotencyKey": "agent-run-matching-key-session-id-1",
        },
        now_ms=3189,
    )

    assert observed_send == {
        "session_key": thread_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-matching-key-session-id-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-matching-key-session-id-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-matching-key-session-id-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-matching-key-session-id-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 3189
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launch_ignores_blank_optional_unsupported_string_fields() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-optional-fields"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-optional-fields.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Blank Optional Fields Loop",
        objective="Launch parity while treating blank unsupported strings as omitted.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-blank-optional-fields",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent blank optional fields launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "provider": "   ",
            "replyTo": "   ",
            "channel": "   ",
            "threadId": "   ",
            "groupId": "   ",
            "lane": "   ",
            "extraSystemPrompt": "   ",
            "idempotencyKey": "agent-run-blank-optional-fields-1",
        },
        now_ms=3721,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-optional-fields-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-blank-optional-fields-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-blank-optional-fields-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-blank-optional-fields-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 3721
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launch_ignores_blank_session_selectors() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-session-selectors"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-session-selectors.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Blank Session Selectors Loop",
        objective="Launch parity while treating blank session selectors as omitted.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-blank-session-selectors",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent blank session selectors launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "sessionKey": "   ",
            "sessionId": "   ",
            "idempotencyKey": "agent-run-blank-session-selectors-1",
        },
        now_ms=4511,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-session-selectors-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-blank-session-selectors-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-blank-session-selectors-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-blank-session-selectors-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 4511
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launch_ignores_blank_agent_id() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-agent-id"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-agent-id.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Blank Agent Id Loop",
        objective="Launch parity while treating blank agent ids as omitted.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-blank-agent-id",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent blank agent id launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "   ",
            "idempotencyKey": "agent-run-blank-agent-id-1",
        },
        now_ms=4822,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-agent-id-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-blank-agent-id-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-blank-agent-id-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-blank-agent-id-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 4822
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launch_allows_blank_thinking_hint() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-thinking"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-thinking.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Blank Thinking Loop",
        objective="Launch parity while preserving blank thinking hints.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-blank-thinking",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent blank thinking launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "thinking": "",
            "idempotencyKey": "agent-run-blank-thinking-1",
        },
        now_ms=5091,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-thinking-1",
        "thinking": "",
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-blank-thinking-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-blank-thinking-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-blank-thinking-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 5091
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launch_ignores_blank_label_and_preserves_existing_metadata() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-blank-label"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-blank-label.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Blank Label Loop",
        objective="Launch parity while treating blank labels as omitted.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-blank-label",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.upsert_gateway_session_metadata(
        session_key=main_session_key,
        metadata={"label": "Pinned Worker", "model": "gpt-5.4"},
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent blank label launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "label": "",
            "idempotencyKey": "agent-run-blank-label-1",
        },
        now_ms=5274,
    )

    metadata_row = await database.get_gateway_session_metadata(main_session_key)

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-blank-label-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-blank-label-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)
    assert metadata_row is not None
    assert metadata_row["metadata"]["label"] == "Pinned Worker"
    assert metadata_row["metadata"]["model"] == "gpt-5.4"

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-blank-label-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-blank-label-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 5274
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_agent_launch_allows_empty_internal_events_array() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agent-launch-empty-internal-events"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agent-launch-empty-internal-events.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    mission_id = await database.create_mission(
        name="Gateway Agent Empty Internal Events Loop",
        objective="Launch parity while treating empty internal events as inert.",
        status="active",
        instance_id=7,
        project_id=None,
        thread_id="thread-agent-launch-empty-internal-events",
        session_key=main_session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )

    observed_send: dict[str, object] = {}

    async def fake_chat_send_service(
        *,
        session_key: str,
        message: str,
        idempotency_key: str,
        thinking: str | None,
        deliver: bool | None,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        observed_send.update(
            {
                "session_key": session_key,
                "message": message,
                "idempotency_key": idempotency_key,
                "thinking": thinking,
                "deliver": deliver,
                "timeout_ms": timeout_ms,
            }
        )
        return {"runId": idempotency_key, "status": "ok"}

    sleep_calls = 0

    async def fake_sleep(_seconds: float) -> None:
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 1:
            await database.update_mission(
                mission_id,
                status="completed",
                in_progress=0,
                phase="completed",
                last_checkpoint="Gateway agent empty internal events launch completed.",
            )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
        chat_send_service=fake_chat_send_service,
        sleep=fake_sleep,
    )

    launch_payload = await service.call(
        "agent",
        {
            "message": "Ship the next verified slice.",
            "agentId": "main",
            "internalEvents": [],
            "idempotencyKey": "agent-run-empty-internal-events-1",
        },
        now_ms=5417,
    )

    assert observed_send == {
        "session_key": main_session_key,
        "message": "Ship the next verified slice.",
        "idempotency_key": "agent-run-empty-internal-events-1",
        "thinking": None,
        "deliver": None,
        "timeout_ms": None,
    }
    assert launch_payload["runId"] == "agent-run-empty-internal-events-1"
    assert launch_payload["status"] == "accepted"
    assert isinstance(launch_payload["acceptedAt"], int)

    wait_payload = await service.call(
        "agent.wait",
        {
            "runId": "agent-run-empty-internal-events-1",
            "timeoutMs": 5,
        },
    )

    assert wait_payload["runId"] == "agent-run-empty-internal-events-1"
    assert wait_payload["status"] == "ok"
    assert wait_payload["startedAt"] == 5417
    assert isinstance(wait_payload["endedAt"], int)
    assert wait_payload["endedAt"] >= wait_payload["startedAt"]
    assert sleep_calls == 1


@pytest.mark.asyncio
async def test_cron_list_returns_paged_scheduled_task_inventory() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-list-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-list.db")
    await database.initialize()
    scheduled_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload("Ship the next verified slice."),
    )
    await database.update_task_blueprint_payload(
        scheduled_id,
        last_launched_at="2026-04-18T05:00:00Z",
        last_status="completed",
        last_result_summary="Completed the nightly ship lane.",
    )
    await database.create_task_blueprint(
        name="Archive Sweep",
        summary="Disabled schedule should not leak into enabled filter.",
        project_id=None,
        instance_id=None,
        cadence_minutes=30,
        enabled=False,
        payload=_task_blueprint_payload("Archive the old artifacts."),
    )
    await database.create_task_blueprint(
        name="Manual Repair",
        summary="Manual-only work should not appear in cron.list.",
        project_id=None,
        instance_id=None,
        cadence_minutes=None,
        enabled=True,
        payload=_task_blueprint_payload("Repair the queue drift."),
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "cron.list",
        {"enabled": "enabled", "limit": 10, "sortBy": "name", "sortDir": "asc"},
    )

    assert payload["total"] == 1
    assert payload["offset"] == 0
    assert payload["limit"] == 10
    assert payload["hasMore"] is False
    assert payload["nextOffset"] is None
    job = payload["jobs"][0]
    assert job["id"] == f"task-blueprint:{scheduled_id}"
    assert job["agentId"] == "openzues"
    assert job["name"] == "Nightly Ship"
    assert job["description"] == "Ship the next verified slice."
    assert job["enabled"] is True
    assert job["schedule"] == {"kind": "every", "everyMs": 3_600_000}
    assert job["sessionTarget"] == "main"
    assert job["wakeMode"] == "now"
    assert job["payload"] == {
        "kind": "agentTurn",
        "message": "Ship the next verified slice.",
        "model": "gpt-5.4",
    }
    assert job["delivery"] == {"mode": "none"}
    last_run_at_ms = int(datetime(2026, 4, 18, 5, 0, tzinfo=UTC).timestamp() * 1000)
    next_run_at_ms = int(datetime(2026, 4, 18, 6, 0, tzinfo=UTC).timestamp() * 1000)
    assert job["state"] == {
        "nextRunAtMs": next_run_at_ms,
        "lastRunAtMs": last_run_at_ms,
        "lastRunStatus": "ok",
        "lastStatus": "ok",
    }
    assert isinstance(job["createdAtMs"], int)
    assert isinstance(job["updatedAtMs"], int)
    assert job["createdAtMs"] > 0
    assert job["updatedAtMs"] >= job["createdAtMs"]


@pytest.mark.asyncio
async def test_cron_status_returns_bounded_scheduler_summary() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-status-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-status.db")
    await database.initialize()
    enabled_id = await database.create_task_blueprint(
        name="Status Ping",
        summary="Keep the scheduler warm.",
        project_id=None,
        instance_id=None,
        cadence_minutes=30,
        enabled=True,
        payload=_task_blueprint_payload("Keep the scheduler warm."),
    )
    await database.update_task_blueprint_payload(
        enabled_id,
        last_launched_at="2026-04-18T05:00:00Z",
        last_status="completed",
        last_result_summary="Scheduler status lane completed.",
    )
    await database.create_task_blueprint(
        name="Disabled Sweep",
        summary="Still counts as a stored cadence job.",
        project_id=None,
        instance_id=None,
        cadence_minutes=120,
        enabled=False,
        payload=_task_blueprint_payload("Sweep disabled backlog."),
    )
    await database.create_task_blueprint(
        name="Manual Repair",
        summary="Manual-only work should not count toward cron.status jobs.",
        project_id=None,
        instance_id=None,
        cadence_minutes=None,
        enabled=True,
        payload=_task_blueprint_payload("Repair queue drift."),
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call("cron.status", {})

    assert payload == {
        "enabled": True,
        "storePath": str(database.path),
        "jobs": 2,
        "nextWakeAtMs": int(datetime(2026, 4, 18, 5, 30, tzinfo=UTC).timestamp() * 1000),
    }


@pytest.mark.asyncio
async def test_cron_runs_returns_finished_scheduled_mission_history_page() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-runs-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-runs.db")
    await database.initialize()
    ship_task_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload("Ship the next verified slice."),
    )
    other_task_id = await database.create_task_blueprint(
        name="Archive Sweep",
        summary="Sweep the release lane.",
        project_id=None,
        instance_id=None,
        cadence_minutes=30,
        enabled=True,
        payload=_task_blueprint_payload("Sweep the release lane."),
    )
    await _create_scheduled_mission(
        database,
        name="Nightly Ship Run",
        objective="Ship the next verified slice.",
        status="completed",
        task_blueprint_id=ship_task_id,
        thread_id="thread-ship-ok",
        last_checkpoint="Nightly ship landed.",
    )
    await _create_scheduled_mission(
        database,
        name="Nightly Ship Retry",
        objective="Ship the next verified slice.",
        status="failed",
        task_blueprint_id=ship_task_id,
        thread_id="thread-ship-error",
        last_error="Archive webhook target was unavailable.",
    )
    await _create_scheduled_mission(
        database,
        name="Archive Sweep Run",
        objective="Sweep the release lane.",
        status="completed",
        task_blueprint_id=other_task_id,
        thread_id="thread-archive-ok",
        last_checkpoint="Archive sweep landed.",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call("cron.runs", {"id": f"task-blueprint:{ship_task_id}", "limit": 10})

    assert payload["total"] == 2
    assert payload["offset"] == 0
    assert payload["limit"] == 10
    assert payload["hasMore"] is False
    assert payload["nextOffset"] is None
    entries = payload["entries"]
    assert len(entries) == 2
    assert {entry["status"] for entry in entries} == {"ok", "error"}
    assert {entry["jobId"] for entry in entries} == {f"task-blueprint:{ship_task_id}"}
    assert {entry["action"] for entry in entries} == {"finished"}
    assert {entry["deliveryStatus"] for entry in entries} == {"not-requested"}
    assert {entry["summary"] for entry in entries} == {
        "Nightly ship landed.",
        "Archive webhook target was unavailable.",
    }
    ok_entry = next(entry for entry in entries if entry["status"] == "ok")
    assert ok_entry["sessionId"] == "thread-ship-ok"
    assert ok_entry["sessionKey"] == "launch:mode:workspace_affinity"
    assert isinstance(ok_entry["ts"], int)
    assert isinstance(ok_entry["runAtMs"], int)
    assert isinstance(ok_entry["durationMs"], int)
    error_entry = next(entry for entry in entries if entry["status"] == "error")
    assert error_entry["error"] == "Archive webhook target was unavailable."


@pytest.mark.asyncio
async def test_cron_run_launches_scheduled_task_via_runtime_bridge() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-run-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-run.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload("Ship the next verified slice."),
    )
    runner = FakeCronTaskRunner()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        run_task_blueprint_now=runner,
    )

    payload = await service.call("cron.run", {"id": f"task-blueprint:{task_id}", "mode": "force"})

    assert payload == {"ok": True, "enqueued": True, "runId": "mission:52"}
    assert runner.calls == [(task_id, "gateway-cron:force")]


@pytest.mark.asyncio
async def test_cron_run_due_returns_not_due_without_launching() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-run-due-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-run-due.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload("Ship the next verified slice."),
    )
    await database.update_task_blueprint(
        task_id,
        last_launched_at=datetime.now(UTC).isoformat(),
    )
    runner = FakeCronTaskRunner()
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        run_task_blueprint_now=runner,
    )

    payload = await service.call("cron.run", {"id": f"task-blueprint:{task_id}", "mode": "due"})

    assert payload == {"ok": True, "ran": False, "reason": "not-due"}
    assert runner.calls == []


@pytest.mark.asyncio
async def test_cron_remove_deletes_cadence_backed_task_blueprint() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-remove-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-remove.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload("Ship the next verified slice."),
    )

    async def delete_task(task_blueprint_id: int) -> None:
        await database.delete_task_blueprint(task_blueprint_id)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        delete_task_blueprint=delete_task,
    )

    payload = await service.call("cron.remove", {"id": f"task-blueprint:{task_id}"})

    assert payload == {"ok": True, "removed": True}
    assert await database.get_task_blueprint(task_id) is None


@pytest.mark.asyncio
async def test_cron_remove_returns_removed_false_for_manual_only_task() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-remove-manual-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-remove-manual.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Manual Sweep",
        summary="Manual only.",
        project_id=None,
        instance_id=None,
        cadence_minutes=None,
        enabled=True,
        payload=_task_blueprint_payload("Manual only."),
    )

    async def delete_task(task_blueprint_id: int) -> None:
        await database.delete_task_blueprint(task_blueprint_id)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        delete_task_blueprint=delete_task,
    )

    payload = await service.call("cron.remove", {"id": f"task-blueprint:{task_id}"})

    assert payload == {"ok": True, "removed": False}
    assert await database.get_task_blueprint(task_id) is not None


@pytest.mark.asyncio
async def test_cron_add_creates_every_schedule_agent_turn_job() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-add.db")
    await database.initialize()
    created_payloads: list[TaskBlueprintCreate] = []

    async def create_task(payload: TaskBlueprintCreate) -> object:
        created_payloads.append(payload)
        task_id = await database.create_task_blueprint(
            name=payload.name,
            summary=payload.summary,
            project_id=payload.project_id,
            instance_id=payload.instance_id,
            cadence_minutes=payload.cadence_minutes,
            enabled=payload.enabled,
            payload={
                "objective_template": payload.objective_template,
                "conversation_target": payload.conversation_target,
                "run_until_complete": payload.run_until_complete,
                "continuation_cooldown_minutes": payload.continuation_cooldown_minutes,
                "completion_marker": payload.completion_marker,
                "cwd": payload.cwd,
                "model": payload.model,
                "reasoning_effort": payload.reasoning_effort,
                "collaboration_mode": payload.collaboration_mode,
                "max_turns": payload.max_turns,
                "use_builtin_agents": payload.use_builtin_agents,
                "run_verification": payload.run_verification,
                "auto_commit": payload.auto_commit,
                "pause_on_approval": payload.pause_on_approval,
                "allow_auto_reflexes": payload.allow_auto_reflexes,
                "auto_recover": payload.auto_recover,
                "auto_recover_limit": payload.auto_recover_limit,
                "reflex_cooldown_seconds": payload.reflex_cooldown_seconds,
                "allow_failover": payload.allow_failover,
                "toolsets": payload.toolsets,
            },
        )
        return type("CreatedTask", (), {"id": task_id})()

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        create_task_blueprint=create_task,
    )

    payload = await service.call(
        "cron.add",
        {
            "name": "Nightly Ship",
            "description": "Ship the next verified slice.",
            "enabled": True,
            "schedule": {"kind": "every", "everyMs": 3_600_000},
            "sessionTarget": "main",
            "wakeMode": "now",
            "payload": {
                "kind": "agentTurn",
                "message": "Ship the next verified slice.",
                "model": "gpt-5.4",
            },
        },
    )

    assert len(created_payloads) == 1
    created = created_payloads[0]
    assert created.name == "Nightly Ship"
    assert created.summary == "Ship the next verified slice."
    assert created.cadence_minutes == 60
    assert created.objective_template == "Ship the next verified slice."
    assert created.model == "gpt-5.4"
    assert payload["name"] == "Nightly Ship"
    assert payload["description"] == "Ship the next verified slice."
    assert payload["schedule"] == {"kind": "every", "everyMs": 3_600_000}
    assert payload["sessionTarget"] == "main"
    assert payload["wakeMode"] == "now"
    assert payload["payload"] == {
        "kind": "agentTurn",
        "message": "Ship the next verified slice.",
        "model": "gpt-5.4",
    }
    assert payload["delivery"] == {"mode": "none"}
    assert payload["enabled"] is True
    assert str(payload["id"]).startswith("task-blueprint:")


@pytest.mark.asyncio
async def test_cron_add_accepts_every_schedule_anchor_ms() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-add-anchor-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-add-anchor.db")
    await database.initialize()
    created_payloads: list[TaskBlueprintCreate] = []

    async def create_task(payload: TaskBlueprintCreate) -> object:
        created_payloads.append(payload)
        task_id = await database.create_task_blueprint(
            name=payload.name,
            summary=payload.summary,
            project_id=payload.project_id,
            instance_id=payload.instance_id,
            cadence_minutes=payload.cadence_minutes,
            enabled=payload.enabled,
            payload={
                "objective_template": payload.objective_template,
                "conversation_target": payload.conversation_target,
                "run_until_complete": payload.run_until_complete,
                "continuation_cooldown_minutes": payload.continuation_cooldown_minutes,
                "completion_marker": payload.completion_marker,
                "cwd": payload.cwd,
                "model": payload.model,
                "reasoning_effort": payload.reasoning_effort,
                "collaboration_mode": payload.collaboration_mode,
                "max_turns": payload.max_turns,
                "use_builtin_agents": payload.use_builtin_agents,
                "run_verification": payload.run_verification,
                "auto_commit": payload.auto_commit,
                "pause_on_approval": payload.pause_on_approval,
                "allow_auto_reflexes": payload.allow_auto_reflexes,
                "auto_recover": payload.auto_recover,
                "auto_recover_limit": payload.auto_recover_limit,
                "reflex_cooldown_seconds": payload.reflex_cooldown_seconds,
                "allow_failover": payload.allow_failover,
                "toolsets": payload.toolsets,
                "schedule_anchor_ms": payload.schedule_anchor_ms,
            },
        )
        return type("CreatedTask", (), {"id": task_id})()

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        create_task_blueprint=create_task,
    )

    payload = await service.call(
        "cron.add",
        {
            "name": "Anchored Ship",
            "description": "Ship on the anchored minute boundary.",
            "enabled": True,
            "schedule": {"kind": "every", "everyMs": 3_600_000, "anchorMs": 123},
            "sessionTarget": "main",
            "wakeMode": "now",
            "payload": {
                "kind": "agentTurn",
                "message": "Ship on the anchored minute boundary.",
                "model": "gpt-5.4",
            },
        },
    )

    assert len(created_payloads) == 1
    assert created_payloads[0].schedule_anchor_ms == 123
    assert payload["schedule"] == {"kind": "every", "everyMs": 3_600_000, "anchorMs": 123}


@pytest.mark.asyncio
async def test_cron_add_rejects_unsupported_schedule_kind() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        create_task_blueprint=lambda payload: payload,
    )

    with pytest.raises(
        ValueError,
        match="invalid cron.add params: OpenZues currently supports only schedule.kind='every'",
    ):
        await service.call(
            "cron.add",
            {
                "name": "One Shot",
                "schedule": {"kind": "at", "at": "2026-04-18T12:00:00Z"},
                "sessionTarget": "main",
                "wakeMode": "now",
                "payload": {"kind": "agentTurn", "message": "Do the thing."},
            },
        )


@pytest.mark.asyncio
async def test_cron_update_patches_supported_every_agent_turn_fields() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-update.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload(
            "Ship the next verified slice.",
            model="gpt-5.4",
        ),
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "cron.update",
        {
            "id": f"task-blueprint:{task_id}",
            "patch": {
                "name": "Nightly Repair",
                "description": "Repair the next verified slice.",
                "enabled": False,
                "schedule": {"kind": "every", "everyMs": 7_200_000},
                "payload": {
                    "message": "Repair the next verified slice.",
                    "model": "gpt-5.4-mini",
                },
            },
        },
    )
    updated_task = await database.get_task_blueprint(task_id)
    updated_record = next(
        record
        for record in await database.list_task_blueprint_records()
        if record["id"] == task_id
    )

    assert payload["id"] == f"task-blueprint:{task_id}"
    assert payload["name"] == "Nightly Repair"
    assert payload["description"] == "Repair the next verified slice."
    assert payload["enabled"] is False
    assert payload["schedule"] == {"kind": "every", "everyMs": 7_200_000}
    assert payload["payload"] == {
        "kind": "agentTurn",
        "message": "Repair the next verified slice.",
        "model": "gpt-5.4-mini",
    }
    assert updated_task is not None
    assert updated_task["name"] == "Nightly Repair"
    assert updated_task["summary"] == "Repair the next verified slice."
    assert updated_task["cadence_minutes"] == 120
    assert not bool(updated_record["enabled"])
    assert updated_task["objective_template"] == "Repair the next verified slice."
    assert updated_task["model"] == "gpt-5.4-mini"


@pytest.mark.asyncio
async def test_cron_update_accepts_every_schedule_anchor_ms() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-anchor-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-update-anchor.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Anchored Ship",
        summary="Ship on the anchored minute boundary.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload={
            **_task_blueprint_payload(
                "Ship on the anchored minute boundary.",
                model="gpt-5.4",
            ),
            "schedule_anchor_ms": 123,
        },
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "cron.update",
        {
            "id": f"task-blueprint:{task_id}",
            "patch": {
                "schedule": {"kind": "every", "everyMs": 7_200_000, "anchorMs": 456},
            },
        },
    )
    updated_task = await database.get_task_blueprint(task_id)

    assert payload["schedule"] == {"kind": "every", "everyMs": 7_200_000, "anchorMs": 456}
    assert updated_task is not None
    assert updated_task["schedule_anchor_ms"] == 456


@pytest.mark.asyncio
async def test_cron_update_rejects_unsupported_schedule_kind() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-cron-update-reject-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-cron-update-reject.db")
    await database.initialize()
    task_id = await database.create_task_blueprint(
        name="Nightly Ship",
        summary="Ship the next verified slice.",
        project_id=None,
        instance_id=None,
        cadence_minutes=60,
        enabled=True,
        payload=_task_blueprint_payload("Ship the next verified slice."),
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    with pytest.raises(
        ValueError,
        match=(
            "invalid cron.update params: "
            "OpenZues currently supports only patch.schedule.kind='every'"
        ),
    ):
        await service.call(
            "cron.update",
            {
                "id": f"task-blueprint:{task_id}",
                "patch": {"schedule": {"kind": "cron", "expr": "0 * * * *"}},
            },
        )


@pytest.mark.asyncio
async def test_wake_requires_openclaw_shape_then_dispatches_or_queues_when_runtime_wired(
    tmp_path,
) -> None:
    database = Database(tmp_path / "gateway-wake.db")
    await database.initialize()
    dispatched: list[str] = []

    async def fake_dispatch_now(text: str) -> None:
        dispatched.append(text)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        wake_service=GatewayWakeService(database, dispatch_now=fake_dispatch_now),
    )

    with pytest.raises(ValueError, match="mode is required"):
        await service.call("wake", {"text": "Resume parity from the latest checkpoint."})

    with pytest.raises(
        ValueError,
        match="mode must be one of: next-heartbeat, now",
    ):
        await service.call(
            "wake",
            {"mode": "later", "text": "Resume parity from the latest checkpoint."},
        )

    now_payload = await service.call(
        "wake",
        {"mode": "now", "text": "  Resume parity from the latest checkpoint.  "},
    )
    queued_payload = await service.call(
        "wake",
        {
            "mode": "next-heartbeat",
            "text": "  Check the queued parity nudge on the next heartbeat.  ",
        },
    )
    wake_requests = await database.list_gateway_wake_requests()

    assert now_payload == {"ok": True}
    assert queued_payload == {"ok": True}
    assert dispatched == ["Resume parity from the latest checkpoint."]
    assert len(wake_requests) == 1
    assert wake_requests[0]["mode"] == "next-heartbeat"
    assert wake_requests[0]["text"] == "Check the queued parity nudge on the next heartbeat."
    assert wake_requests[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_agents_files_list_returns_bounded_workspace_instruction_inventory() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agents-files-list-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    workspace_root = tmp_path / "workspace"
    (workspace_root / ".codex").mkdir(parents=True, exist_ok=True)
    (workspace_root / "AGENTS.md").write_text("Top-level instructions.\n", encoding="utf-8")
    (workspace_root / ".codex" / "AGENTS.md").write_text(
        "Codex instructions.\n",
        encoding="utf-8",
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        agent_files_service=GatewayAgentFilesService(workspace_dir=workspace_root),
    )

    payload = await service.call("agents.files.list", {"agentId": "main"})

    assert payload["agentId"] == "main"
    assert payload["workspace"] == str(workspace_root)
    files_by_name = {entry["name"]: entry for entry in payload["files"]}
    assert files_by_name["AGENTS.md"]["missing"] is False
    assert files_by_name["AGENTS.md"]["path"] == str(workspace_root / "AGENTS.md")
    assert files_by_name["AGENTS.md"]["size"] == (workspace_root / "AGENTS.md").stat().st_size
    assert isinstance(files_by_name["AGENTS.md"]["updatedAtMs"], int)
    assert files_by_name[".codex/AGENTS.md"]["missing"] is False
    assert files_by_name[".codex/AGENTS.md"]["path"] == str(workspace_root / ".codex" / "AGENTS.md")


@pytest.mark.asyncio
async def test_agents_files_get_returns_workspace_instruction_file_content() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agents-files-get-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    file_content = "Top-level instructions.\n"
    (workspace_root / "AGENTS.md").write_text(file_content, encoding="utf-8")
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        agent_files_service=GatewayAgentFilesService(workspace_dir=workspace_root),
    )

    payload = await service.call(
        "agents.files.get",
        {"agentId": "main", "name": "AGENTS.md"},
    )

    assert payload["agentId"] == "main"
    assert payload["workspace"] == str(workspace_root)
    assert payload["file"]["name"] == "AGENTS.md"
    assert payload["file"]["path"] == str(workspace_root / "AGENTS.md")
    assert payload["file"]["missing"] is False
    assert payload["file"]["size"] == (workspace_root / "AGENTS.md").stat().st_size
    assert isinstance(payload["file"]["updatedAtMs"], int)
    assert payload["file"]["content"] == file_content


@pytest.mark.asyncio
async def test_agents_files_set_writes_workspace_instruction_file_content() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agents-files-set-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    file_content = "Codex instructions.\n"
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        agent_files_service=GatewayAgentFilesService(workspace_dir=workspace_root),
    )

    payload = await service.call(
        "agents.files.set",
        {
            "agentId": "main",
            "name": ".codex/AGENTS.md",
            "content": file_content,
        },
    )

    written_path = workspace_root / ".codex" / "AGENTS.md"
    assert payload["ok"] is True
    assert payload["agentId"] == "main"
    assert payload["workspace"] == str(workspace_root)
    assert payload["file"]["name"] == ".codex/AGENTS.md"
    assert payload["file"]["path"] == str(written_path)
    assert payload["file"]["missing"] is False
    assert payload["file"]["size"] == written_path.stat().st_size
    assert isinstance(payload["file"]["updatedAtMs"], int)
    assert payload["file"]["content"] == file_content
    assert written_path.read_text(encoding="utf-8") == file_content


@pytest.mark.asyncio
async def test_agents_list_returns_bounded_singleton_agent_inventory() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-agents-list-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-agents-list.db")
    await database.initialize()
    project_id = await database.create_project(path=str(workspace_root), label="Parity Workspace")
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=None,
        preferred_project_id=project_id,
        team_id=None,
        operator_id=None,
        task_blueprint_id=None,
        default_cwd=None,
        bootstrap_roles=[],
        bootstrap_scopes=[],
        model="gpt-5.4-mini",
        max_turns=None,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call("agents.list", {})

    assert payload == {
        "defaultId": "main",
        "mainKey": "main",
        "scope": "global",
        "agents": [
            {
                "id": "main",
                "name": "OpenZues",
                "identity": {
                    "name": "OpenZues",
                    "avatar": "/static/favicon.svg",
                    "avatarUrl": "/static/favicon.svg",
                    "emoji": None,
                },
                "workspace": str(workspace_root),
                "model": {"primary": "gpt-5.4-mini"},
            }
        ],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "message"),
    [
        (
            "agents.create",
            {
                "name": "Builder",
                "workspace": "/tmp/workspace",
                "model": "gpt-5.4",
                "emoji": "robot",
                "avatar": "/static/agent.png",
            },
            "agents.create is unavailable until multi-agent registry mutation is wired",
        ),
        (
            "agents.update",
            {
                "agentId": "main",
                "name": "Builder",
                "workspace": "/tmp/workspace",
                "model": "gpt-5.4",
                "emoji": "robot",
                "avatar": "/static/agent.png",
            },
            "agents.update is unavailable until multi-agent registry mutation is wired",
        ),
        (
            "agents.delete",
            {
                "agentId": "main",
                "deleteFiles": True,
            },
            "agents.delete is unavailable until multi-agent registry mutation is wired",
        ),
    ],
)
async def test_agents_mutate_methods_return_explicit_unavailable_contract(
    method: str,
    params: dict[str, object],
    message: str,
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == message


@pytest.mark.asyncio
async def test_doctor_memory_status_returns_explicit_unavailable_contract() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call("doctor.memory.status", {})

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == (
        "doctor.memory.status is unavailable until gateway memory doctor runtime is wired"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "message"),
    [
        (
            "doctor.memory.dreamDiary",
            "doctor.memory.dreamDiary is unavailable until gateway dreaming runtime is wired",
        ),
        (
            "doctor.memory.backfillDreamDiary",
            "doctor.memory.backfillDreamDiary is unavailable until gateway dreaming "
            "runtime is wired",
        ),
        (
            "doctor.memory.resetDreamDiary",
            "doctor.memory.resetDreamDiary is unavailable until gateway dreaming runtime is wired",
        ),
        (
            "doctor.memory.resetGroundedShortTerm",
            "doctor.memory.resetGroundedShortTerm is unavailable until gateway dreaming "
            "runtime is wired",
        ),
        (
            "doctor.memory.repairDreamingArtifacts",
            "doctor.memory.repairDreamingArtifacts is unavailable until gateway dreaming "
            "runtime is wired",
        ),
        (
            "doctor.memory.dedupeDreamDiary",
            "doctor.memory.dedupeDreamDiary is unavailable until gateway dreaming runtime is wired",
        ),
    ],
)
async def test_doctor_memory_family_returns_explicit_unavailable_contract(
    method: str,
    message: str,
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, {})

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert str(exc_info.value) == message


@pytest.mark.asyncio
async def test_agent_identity_get_returns_singleton_identity_and_rejects_malformed_session_keys(
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("agent.identity.get", {"agentId": "main"})

    assert payload == {
        "agentId": "main",
        "name": "OpenZues",
        "avatar": "/static/favicon.svg",
        "emoji": None,
    }

    with pytest.raises(
        ValueError,
        match='invalid agent.identity.get params: malformed session key "agent:main"',
    ):
        await service.call("agent.identity.get", {"sessionKey": "agent:main"})


@pytest.mark.asyncio
async def test_agent_identity_get_rejects_agent_id_that_conflicts_with_session_key_agent() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        ValueError,
        match=(
            'invalid agent.identity.get params: agent "main" does not match session key agent '
            '"other-agent"'
        ),
    ):
        await service.call(
            "agent.identity.get",
            {"agentId": "main", "sessionKey": "agent:other-agent:main"},
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params",),
    [
        ({"agentId": "   "},),
        ({"sessionKey": "   "},),
    ],
)
async def test_agent_identity_get_allows_blank_optional_selectors(
    params: dict[str, str],
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("agent.identity.get", params)

    assert payload == {
        "agentId": "main",
        "name": "OpenZues",
        "avatar": "/static/favicon.svg",
        "emoji": None,
    }


@pytest.mark.asyncio
async def test_sessions_list_returns_bounded_singleton_control_chat_inventory() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list.db")
    await database.initialize()
    await database.upsert_gateway_bootstrap(
        setup_mode="local",
        setup_flow="quickstart",
        route_binding_mode="saved_lane",
        preferred_instance_id=9,
        preferred_project_id=3,
        team_id=None,
        operator_id=4,
        task_blueprint_id=7,
        default_cwd=str(tmp_path),
        bootstrap_roles=[],
        bootstrap_scopes=[],
        model="gpt-5.4",
        max_turns=4,
        use_builtin_agents=True,
        run_verification=True,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        toolsets=[],
    )
    main_session_key = build_launch_session_key(
        mode="saved_lane",
        preferred_instance_id=None,
        task_id=7,
        project_id=3,
        operator_id=4,
    )
    resolved_session_keys = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-demo",
    )
    await database.create_mission(
        name="Control Chat Thread",
        objective="Keep the operator control chat lane warm.",
        status="active",
        instance_id=9,
        project_id=3,
        task_blueprint_id=7,
        thread_id="thread-demo",
        session_key=resolved_session_keys.session_key,
        cwd=str(tmp_path),
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The singleton session inventory is staged.",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 50},
        now_ms=1_234,
    )

    assert payload["ts"] == 1_234
    assert payload["path"] == "/api/control-chat"
    assert payload["count"] == 1
    assert payload["defaults"] == {
        "model": "gpt-5.4",
        "contextTokens": None,
        "mainSessionKey": main_session_key,
    }
    assert payload["sessions"] == [
        {
            "key": resolved_session_keys.session_key,
            "kind": "thread",
            "displayName": "OpenZues Control Chat Thread",
            "surface": "control-chat",
            "subject": "Keep the operator control chat lane warm.",
            "room": None,
            "space": None,
            "updatedAt": payload["sessions"][0]["updatedAt"],
            "sessionId": "thread-demo",
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4",
            "contextTokens": None,
        }
    ]
    assert isinstance(payload["sessions"][0]["updatedAt"], int)
    assert payload["sessions"][0]["updatedAt"] > 0


@pytest.mark.asyncio
async def test_sessions_list_includes_metadata_known_non_current_sessions() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-metadata-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-metadata.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-parity",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=thread_session_key,
        metadata={
            "label": "Parity Worker",
            "spawnedBy": "parity-conductor",
            "model": "gpt-5.4-mini",
        },
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=456,
    )

    assert payload["count"] == 2
    assert payload["sessions"] == [
        {
            "key": main_session_key,
            "kind": "global",
            "displayName": "OpenZues Control Chat",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": payload["sessions"][0]["updatedAt"],
            "sessionId": None,
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4",
            "contextTokens": None,
        },
        {
            "key": thread_session_key,
            "kind": "thread",
            "displayName": "OpenZues Control Chat Thread",
            "surface": "control-chat",
            "subject": "Operator control chat",
            "room": None,
            "space": None,
            "updatedAt": payload["sessions"][1]["updatedAt"],
            "sessionId": "thread-parity",
            "systemSent": None,
            "abortedLastRun": None,
            "thinkingLevel": None,
            "verboseLevel": None,
            "traceLevel": None,
            "inputTokens": None,
            "outputTokens": None,
            "totalTokens": None,
            "modelProvider": "openai",
            "model": "gpt-5.4-mini",
            "contextTokens": None,
            "label": "Parity Worker",
            "spawnedBy": "parity-conductor",
        },
    ]
    assert isinstance(payload["sessions"][1]["updatedAt"], int)
    assert payload["sessions"][1]["updatedAt"] > 0


@pytest.mark.asyncio
async def test_sessions_list_surfaces_compaction_checkpoint_metadata() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-compaction-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-compaction.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-compaction-list",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=session_key,
        metadata={"label": "Checkpoint Worker"},
    )
    await database.append_control_chat_message(
        role="user",
        content="Alpha line 1\nAlpha line 2",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Bravo line 1",
        mission_id=None,
        session_key=session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Charlie line 1\nCharlie line 2",
        mission_id=None,
        session_key=session_key,
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    compacted = await service.call(
        "sessions.compact",
        {"key": session_key, "maxLines": 2},
        now_ms=1_700_000_000_123,
    )
    payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=1_700_000_000_456,
    )
    session_payload = next(
        session for session in payload["sessions"] if session["key"] == session_key
    )

    assert session_payload["compactionCheckpointCount"] == 1
    assert session_payload["latestCompactionCheckpoint"] == {
        "checkpointId": compacted["checkpointId"],
        "sessionKey": session_key,
        "sessionId": session_key,
        "createdAt": 1_700_000_000_123,
        "reason": "manual",
        "summary": "Alpha line 1 Alpha line 2 Bravo line 1",
        "firstKeptEntryId": session_payload["latestCompactionCheckpoint"]["firstKeptEntryId"],
        "preCompaction": {
            "sessionId": session_key,
            "entryId": session_payload["latestCompactionCheckpoint"]["preCompaction"]["entryId"],
        },
        "postCompaction": {
            "sessionId": session_key,
            "entryId": session_payload["latestCompactionCheckpoint"]["postCompaction"]["entryId"],
        },
    }


@pytest.mark.asyncio
async def test_sessions_list_hides_unknown_session_unless_explicitly_requested() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-unknown-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-unknown.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.upsert_gateway_session_metadata(
        session_key="unknown",
        metadata={"label": "Unknown Session"},
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    hidden_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10},
        now_ms=789,
    )
    visible_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": True, "limit": 10},
        now_ms=790,
    )

    assert [session["key"] for session in hidden_payload["sessions"]] == [main_session_key]
    assert [session["key"] for session in visible_payload["sessions"]] == [
        main_session_key,
        "unknown",
    ]


@pytest.mark.asyncio
async def test_sessions_list_supports_label_and_spawned_by_filters() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-filters-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-filters.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    parity_worker_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-parity-worker",
    ).session_key
    other_worker_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-other-worker",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=parity_worker_key,
        metadata={
            "label": "Parity Worker",
            "spawnedBy": "parity-conductor",
        },
    )
    await database.upsert_gateway_session_metadata(
        session_key=other_worker_key,
        metadata={
            "label": "Other Worker",
            "spawnedBy": "other-conductor",
        },
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    label_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": True,
            "includeUnknown": False,
            "limit": 10,
            "label": "Parity Worker",
        },
        now_ms=791,
    )
    spawned_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": True,
            "includeUnknown": True,
            "limit": 10,
            "spawnedBy": "parity-conductor",
        },
        now_ms=792,
    )

    assert [session["key"] for session in label_payload["sessions"]] == [parity_worker_key]
    assert [session["key"] for session in spawned_payload["sessions"]] == [parity_worker_key]


@pytest.mark.asyncio
async def test_sessions_list_supports_agent_id_filter() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-agent-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-agent.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-agent-filter",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=thread_session_key,
        metadata={"label": "Agent Filter Worker"},
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": True,
            "includeUnknown": False,
            "limit": 10,
            "agentId": "main",
        },
        now_ms=793,
    )

    assert [session["key"] for session in payload["sessions"]] == [
        main_session_key,
        thread_session_key,
    ]

    with pytest.raises(ValueError, match='unknown agent id "other-agent"'):
        await service.call(
            "sessions.list",
            {"includeGlobal": True, "includeUnknown": False, "agentId": "other-agent"},
            now_ms=794,
        )


@pytest.mark.asyncio
async def test_sessions_list_supports_active_minutes_filter() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-active-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-active.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    stale_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-stale-active-filter",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=stale_session_key,
        metadata={"label": "Stale Worker"},
    )
    reference_time = datetime.now(UTC)
    stale_updated_at = (reference_time - timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    with sqlite3.connect(database.path) as db:
        db.execute(
            "UPDATE gateway_session_metadata SET updated_at = ? WHERE session_key = ?",
            (stale_updated_at, stale_session_key),
        )
        db.commit()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    tight_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10, "activeMinutes": 5},
        now_ms=int(reference_time.timestamp() * 1000),
    )
    wide_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10, "activeMinutes": 30},
        now_ms=int(reference_time.timestamp() * 1000),
    )

    assert [session["key"] for session in tight_payload["sessions"]] == [main_session_key]
    assert [session["key"] for session in wide_payload["sessions"]] == [
        main_session_key,
        stale_session_key,
    ]


@pytest.mark.asyncio
async def test_sessions_list_supports_search_filter() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-search-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-search.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    target_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-search-target",
    ).session_key
    other_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-search-other",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=target_session_key,
        metadata={"label": "Parity Search Worker"},
    )
    await database.upsert_gateway_session_metadata(
        session_key=other_session_key,
        metadata={"label": "Background Worker"},
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    label_payload = await service.call(
        "sessions.list",
        {"includeGlobal": True, "includeUnknown": False, "limit": 10, "search": "parity"},
        now_ms=795,
    )
    key_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": True,
            "includeUnknown": False,
            "limit": 10,
            "search": "thread-search-other",
        },
        now_ms=796,
    )

    assert [session["key"] for session in label_payload["sessions"]] == [target_session_key]
    assert [session["key"] for session in key_payload["sessions"]] == [other_session_key]


@pytest.mark.asyncio
async def test_sessions_list_supports_include_last_message_preview() -> None:
    tmp_path = (
        Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-last-message-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-last-message.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    preview_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-last-message-preview",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=preview_session_key,
        metadata={"label": "Preview Worker"},
    )
    await database.append_control_chat_message(
        role="user",
        content="First preview message.",
        session_key=preview_session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Latest preview message.",
        session_key=preview_session_key,
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    hidden_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": False,
            "includeUnknown": False,
            "includeLastMessage": False,
            "label": "Preview Worker",
            "limit": 10,
        },
        now_ms=797,
    )
    visible_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": False,
            "includeUnknown": False,
            "includeLastMessage": True,
            "label": "Preview Worker",
            "limit": 10,
        },
        now_ms=798,
    )

    assert [session["key"] for session in hidden_payload["sessions"]] == [preview_session_key]
    assert "lastMessagePreview" not in hidden_payload["sessions"][0]
    assert [session["key"] for session in visible_payload["sessions"]] == [preview_session_key]
    assert visible_payload["sessions"][0]["lastMessagePreview"] == "Latest preview message."


@pytest.mark.asyncio
async def test_sessions_list_supports_include_derived_titles() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-list-derived-title-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-list-derived-title.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    preview_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-derived-title",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=preview_session_key,
        metadata={"label": "Preview Worker"},
    )
    await database.append_control_chat_message(
        role="user",
        content="First derived title message.",
        session_key=preview_session_key,
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Latest preview message.",
        session_key=preview_session_key,
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    hidden_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": False,
            "includeUnknown": False,
            "includeDerivedTitles": False,
            "label": "Preview Worker",
            "limit": 10,
        },
        now_ms=799,
    )
    visible_payload = await service.call(
        "sessions.list",
        {
            "includeGlobal": False,
            "includeUnknown": False,
            "includeDerivedTitles": True,
            "label": "Preview Worker",
            "limit": 10,
        },
        now_ms=800,
    )

    assert [session["key"] for session in hidden_payload["sessions"]] == [preview_session_key]
    assert "derivedTitle" not in hidden_payload["sessions"][0]
    assert [session["key"] for session in visible_payload["sessions"]] == [preview_session_key]
    assert visible_payload["sessions"][0]["derivedTitle"] == "First derived title message."


@pytest.mark.asyncio
async def test_sessions_get_returns_openclaw_shaped_control_chat_messages() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-get-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-get.db")
    await database.initialize()
    await database.append_control_chat_message(
        role="user",
        content="Need the control-chat transcript.",
        session_key="openzues:thread:demo",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The bounded session transcript is ready.",
        session_key="openzues:thread:demo",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "sessions.get",
        {"key": "openzues:thread:demo", "limit": 2},
    )

    assert payload == {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Need the control-chat transcript."}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "The bounded session transcript is ready."}],
            },
        ]
    }


@pytest.mark.asyncio
async def test_sessions_get_filters_control_chat_messages_by_session_key() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-get-filtered-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-get-filtered.db")
    await database.initialize()
    await database.append_control_chat_message(
        role="user",
        content="Need the thread transcript.",
        session_key="openzues:thread:demo",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="The thread transcript is ready.",
        session_key="openzues:thread:demo",
    )
    await database.append_control_chat_message(
        role="assistant",
        content="Noise from another session.",
        session_key="openzues:thread:other",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call(
        "sessions.get",
        {"key": "openzues:thread:demo", "limit": 5},
    )

    assert payload == {
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Need the thread transcript."}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "The thread transcript is ready."}],
            },
        ]
    }


@pytest.mark.asyncio
async def test_sessions_resolve_returns_bounded_current_control_chat_key() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve.db")
    await database.initialize()
    service = GatewayNodeMethodService(GatewayNodeRegistry(), database=database)

    payload = await service.call("sessions.resolve", {"agentId": "main"})

    assert payload == {"ok": True, "key": "launch:mode:workspace_affinity"}


@pytest.mark.asyncio
async def test_sessions_resolve_supports_current_session_label_lookup() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-label-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-label.db")
    await database.initialize()
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.upsert_gateway_session_metadata(
        session_key=current_session_key,
        metadata={"label": "Parity Session"},
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"label": "Parity Session"})

    assert payload == {"ok": True, "key": current_session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_hides_current_session_label_when_global_is_excluded() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-label-excludes-global-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-label-excludes-global.db")
    await database.initialize()
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.upsert_gateway_session_metadata(
        session_key=current_session_key,
        metadata={"label": "Parity Session"},
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="unknown session label"):
        await service.call(
            "sessions.resolve",
            {"label": "Parity Session", "includeGlobal": False},
        )


@pytest.mark.asyncio
async def test_sessions_resolve_supports_current_session_spawned_by_lookup() -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "gateway-sessions-resolve-spawned-by-service"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-spawned-by.db")
    await database.initialize()
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.upsert_gateway_session_metadata(
        session_key=current_session_key,
        metadata={"spawnedBy": "parity-conductor"},
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"spawnedBy": "parity-conductor"})

    assert payload == {"ok": True, "key": current_session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_supports_metadata_known_session_spawned_by_lookup() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-metadata-spawned-by-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-metadata-spawned-by.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-parity",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=thread_session_key,
        metadata={"spawnedBy": "parity-conductor"},
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"spawnedBy": "parity-conductor"})

    assert payload == {"ok": True, "key": thread_session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_supports_metadata_known_session_id_lookup() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-metadata-session-id-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-metadata-session-id.db")
    await database.initialize()
    main_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    thread_session_key = resolve_thread_session_keys(
        base_session_key=main_session_key,
        thread_id="thread-session-id-parity",
    ).session_key
    await database.upsert_gateway_session_metadata(
        session_key=thread_session_key,
        metadata={"label": "Session Id Parity"},
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"sessionId": "thread-session-id-parity"})

    assert payload == {"ok": True, "key": thread_session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_hides_global_session_id_when_global_is_excluded() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-session-id-excludes-global-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-session-id-excludes-global.db")
    await database.initialize()
    current_session_key = build_launch_session_key(
        mode="workspace_affinity",
        preferred_instance_id=None,
        task_id=None,
        project_id=None,
        operator_id=None,
    )
    await database.create_mission(
        name="Global Session Id",
        objective="Prove global sessionId visibility filtering.",
        status="completed",
        instance_id=9,
        project_id=None,
        thread_id="global-session-id-parity",
        session_key=current_session_key,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        task_blueprint_id=None,
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="unknown sessionId"):
        await service.call(
            "sessions.resolve",
            {"sessionId": "global-session-id-parity", "includeGlobal": False},
        )


@pytest.mark.asyncio
async def test_sessions_resolve_supports_mission_backed_session_id_lookup() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-mission-session-id-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-mission-session-id.db")
    await database.initialize()
    mission_session_key = resolve_thread_session_keys(
        base_session_key="agent:main:main",
        thread_id="thread-mission-session-id",
    ).session_key
    await database.create_mission(
        name="Mission-backed Session",
        objective="Prove mission-backed session id resolution.",
        status="completed",
        instance_id=9,
        project_id=None,
        thread_id="thread-mission-session-id",
        session_key=mission_session_key,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        task_blueprint_id=None,
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"sessionId": "thread-mission-session-id"})

    assert payload == {"ok": True, "key": mission_session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_prefers_freshest_mission_for_duplicate_session_id() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-duplicate-session-id-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-duplicate-session-id.db")
    await database.initialize()
    older_session_key = resolve_thread_session_keys(
        base_session_key="agent:main:main",
        thread_id="thread-duplicate-session-id",
    ).session_key
    newer_session_key = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity",
        thread_id="thread-duplicate-session-id",
    ).session_key
    await database.create_mission(
        name="Older duplicate session",
        objective="Older duplicate sessionId record.",
        status="completed",
        instance_id=9,
        project_id=None,
        thread_id="thread-duplicate-session-id",
        session_key=older_session_key,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        task_blueprint_id=None,
    )
    await database.create_mission(
        name="Newer duplicate session",
        objective="Newer duplicate sessionId record.",
        status="completed",
        instance_id=9,
        project_id=None,
        thread_id="thread-duplicate-session-id",
        session_key=newer_session_key,
        cwd="C:/workspace",
        model="gpt-5.4",
        reasoning_effort=None,
        collaboration_mode=None,
        max_turns=None,
        use_builtin_agents=False,
        run_verification=False,
        auto_commit=False,
        pause_on_approval=True,
        allow_auto_reflexes=True,
        auto_recover=True,
        auto_recover_limit=2,
        reflex_cooldown_seconds=900,
        allow_failover=True,
        task_blueprint_id=None,
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"sessionId": "thread-duplicate-session-id"})

    assert payload == {"ok": True, "key": newer_session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_supports_transcript_only_session_id_lookup() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-transcript-session-id-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-transcript-session-id.db")
    await database.initialize()
    session_key = resolve_thread_session_keys(
        base_session_key="launch:mode:workspace_affinity",
        thread_id="thread-transcript-session-id",
    ).session_key
    await database.append_control_chat_message(
        role="assistant",
        content="Transcript-only session evidence.",
        session_key=session_key,
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    payload = await service.call("sessions.resolve", {"sessionId": "thread-transcript-session-id"})

    assert payload == {"ok": True, "key": session_key}


@pytest.mark.asyncio
async def test_sessions_resolve_by_key_respects_spawned_by_filter() -> None:
    tmp_path = (
        Path.cwd()
        / ".tmp-pytest-local"
        / "gateway-sessions-resolve-key-spawned-by-filter-service"
    )
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = Database(tmp_path / "gateway-sessions-resolve-key-spawned-by-filter.db")
    await database.initialize()
    visible_parent_key = "agent:main:subagent:visible-parent"
    hidden_parent_key = "agent:main:subagent:hidden-parent"
    child_key = "agent:main:subagent:shared-child-key-filter"
    await database.upsert_gateway_session_metadata(
        session_key=visible_parent_key,
        metadata={"spawnedBy": "agent:main:main"},
    )
    await database.upsert_gateway_session_metadata(
        session_key=hidden_parent_key,
        metadata={"spawnedBy": "agent:main:main"},
    )
    await database.upsert_gateway_session_metadata(
        session_key=child_key,
        metadata={"spawnedBy": hidden_parent_key},
    )
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        database=database,
        sessions_service=GatewaySessionsService(database),
    )

    with pytest.raises(ValueError, match="unknown session key"):
        await service.call(
            "sessions.resolve",
            {"key": child_key, "spawnedBy": visible_parent_key},
        )


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
async def test_status_returns_injected_operator_status_snapshot() -> None:
    expected = {
        "headline": "Systems nominal",
        "summary": "One active mission and one connected lane.",
        "queue_plan": {"reply": "No bounded move."},
    }

    async def fake_status_service() -> dict[str, object]:
        return expected

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        status_service=fake_status_service,
    )

    payload = await service.call("status", {})

    assert payload == expected


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
async def test_config_open_file_fails_as_explicit_unavailable_without_file_owner() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        config_service=GatewayConfigService(
            assistant_name="OpenZues",
            assistant_avatar="/static/favicon.svg",
            assistant_agent_id="assistant-control-ui",
            server_version="9.9.9",
        ),
    )

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call("config.openFile", {})

    assert exc_info.value.code == "UNAVAILABLE"
    assert (
        exc_info.value.message
        == "config.openFile is unavailable until operator config file ownership is wired"
    )
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_config_open_file_returns_snapshot_path_when_owner_is_wired(tmp_path) -> None:
    opened_paths: list[Path] = []

    def fake_open_path(path: Path) -> None:
        opened_paths.append(path)

    expected_path = tmp_path / "settings" / "control-ui-config.json"
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        config_service=GatewayConfigService(
            assistant_name="OpenZues",
            assistant_avatar="/static/favicon.svg",
            assistant_agent_id="assistant-control-ui",
            server_version="9.9.9",
            data_dir=tmp_path,
            open_path=fake_open_path,
        ),
    )

    payload = await service.call("config.openFile", {})

    assert payload == {"ok": True, "path": str(expected_path)}
    assert opened_paths == [expected_path]
    assert json.loads(expected_path.read_text(encoding="utf-8")) == {
        "allowExternalEmbedUrls": False,
        "assistantAgentId": "assistant-control-ui",
        "assistantAvatar": "/static/favicon.svg",
        "assistantName": "OpenZues",
        "basePath": "",
        "embedSandbox": "scripts",
        "localMediaPreviewRoots": [],
        "serverVersion": "9.9.9",
    }


@pytest.mark.asyncio
async def test_config_open_file_returns_generic_error_when_opener_fails(tmp_path) -> None:
    def fake_open_path(_path: Path) -> None:
        raise OSError("no opener available")

    expected_path = tmp_path / "settings" / "control-ui-config.json"
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        config_service=GatewayConfigService(
            assistant_name="OpenZues",
            assistant_avatar="/static/favicon.svg",
            assistant_agent_id="assistant-control-ui",
            server_version="9.9.9",
            data_dir=tmp_path,
            open_path=fake_open_path,
        ),
    )

    payload = await service.call("config.openFile", {})

    assert payload == {
        "ok": False,
        "path": str(expected_path),
        "error": "failed to open config file",
    }
    assert expected_path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "params", "expected_message"),
    [
        (
            "config.set",
            {
                "raw": "{\"assistantName\":\"Parity Builder\"}",
                "baseHash": "sha256:abc123",
            },
            "config.set is unavailable until writable gateway config ownership is wired",
        ),
        (
            "config.patch",
            {
                "raw": "{\"assistantName\":\"Parity Builder\"}",
                "baseHash": "sha256:def456",
                "sessionKey": "agent:main:thread:demo",
                "deliveryContext": {
                    "channel": "slack",
                    "to": "user:U123",
                    "accountId": "default",
                    "threadId": 1771242986529939,
                },
                "note": "Patch the bounded config seam.",
                "restartDelayMs": 0,
            },
            "config.patch is unavailable until writable gateway config patching is wired",
        ),
        (
            "config.apply",
            {
                "raw": "{\"assistantName\":\"Parity Builder\"}",
                "baseHash": "sha256:ghi789",
                "sessionKey": "agent:main:thread:demo",
                "deliveryContext": {
                    "channel": "slack",
                    "to": "user:U123",
                    "accountId": "default",
                    "threadId": 1771242986529939,
                },
                "note": "Apply the bounded config seam.",
                "restartDelayMs": 0,
            },
            "config.apply is unavailable until writable gateway config apply runtime is wired",
        ),
    ],
)
async def test_config_write_methods_return_explicit_unavailable_contract(
    method: str,
    params: dict[str, object],
    expected_message: str,
) -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        config_service=GatewayConfigService(
            assistant_name="OpenZues",
            assistant_avatar="/static/favicon.svg",
            assistant_agent_id="assistant-control-ui",
            server_version="9.9.9",
        ),
    )

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(method, params)

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.message == expected_message
    assert exc_info.value.status_code == 503


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
    assert channels["channelOrder"] == ["discord", "slack", "telegram", "whatsapp"]
    assert channels["channelLabels"]["slack"] == "Slack"
    assert channels["channelDetailLabels"]["slack"] == "Slack"
    assert channels["channelMeta"][1] == {
        "id": "slack",
        "label": "Slack",
        "detailLabel": "Slack",
    }
    assert channels["channels"]["slack"] == {
        "routeCount": 1,
        "enabledRouteCount": 1,
        "conversationTargetCount": 1,
        "accountCount": 1,
    }
    assert channels["channelAccounts"]["slack"] == [
        {
            "accountId": "workspace-bot",
            "routeCount": 1,
            "enabledRouteCount": 1,
            "conversationTargetCount": 1,
        }
    ]
    assert channels["channelDefaultAccountId"]["slack"] == "workspace-bot"
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
async def test_skills_update_persists_local_entry_config_and_status_reflects_enabled_override(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = codex_home / "skills" / "local-update-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: local-update-test
description: local skill update
platforms:
  - windows
metadata:
  skillKey: local-update
---
Body
""",
        encoding="utf-8",
    )
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    updated = await service.call(
        "skills.update",
        {
            "skillKey": "local-update",
            "enabled": False,
            "apiKey": "abc\r\ndef",
            "env": {
                " OPENZUES_TOKEN ": "  ready  ",
                "REMOVE_ME": "   ",
            },
        },
    )
    status = await service.call("skills.status", {})

    assert updated == {
        "ok": True,
        "skillKey": "local-update",
        "config": {
            "enabled": False,
            "apiKey": "abcdef",
            "env": {"OPENZUES_TOKEN": "ready"},
        },
    }
    assert status["skills"] == [
        {
            "name": "local-update-test",
            "description": "local skill update",
            "source": "codex-home",
            "bundled": True,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": "local-update",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": True,
            "blockedByAllowlist": False,
            "eligible": False,
            "requirements": {
                "bins": [],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [],
        }
    ]


@pytest.mark.asyncio
async def test_skills_install_runs_declared_gateway_installer_and_updates_skill_status(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    skill_path = codex_home / "skills" / "local-install-test" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: local-install-test
description: local skill install
platforms:
  - windows
metadata:
  skillKey: local-install
  requires:
    bins:
      - missing-bin
  install:
    - id: node
      kind: node
      label: Install local-install-test
      package: demo-skill
      bins:
        - missing-bin
---
Body
""",
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    async def fake_command_runner(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_ms: int | None,
    ) -> tuple[int, str, str]:
        observed["argv"] = argv
        observed["cwd"] = str(cwd)
        observed["timeout_ms"] = timeout_ms
        shim_path = bin_dir / "missing-bin.cmd"
        shim_path.write_text("@echo off\r\necho installed\r\n", encoding="utf-8")
        return (0, "installed", "")

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_install_service=GatewaySkillInstallService(command_runner=fake_command_runner),
    )

    installed = await service.call(
        "skills.install",
        {"name": "local-install-test", "installId": "node", "timeoutMs": 45_000},
    )
    status = await service.call("skills.status", {})

    assert installed == {
        "ok": True,
        "name": "local-install-test",
        "skillKey": "local-install",
        "installId": "node",
        "kind": "node",
        "label": "Install local-install-test",
        "bins": ["missing-bin"],
        "command": ["npm", "install", "-g", "demo-skill"],
        "cwd": str(skill_path.parent),
    }
    assert observed == {
        "argv": ("npm", "install", "-g", "demo-skill"),
        "cwd": str(skill_path.parent),
        "timeout_ms": 45_000,
    }
    assert status["skills"] == [
        {
            "name": "local-install-test",
            "description": "local skill install",
            "source": "codex-home",
            "bundled": True,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": "local-install",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": False,
            "blockedByAllowlist": False,
            "eligible": True,
            "requirements": {
                "bins": ["missing-bin"],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [
                {
                    "id": "node",
                    "kind": "node",
                    "label": "Install local-install-test",
                    "bins": ["missing-bin"],
                }
            ],
        }
    ]


@pytest.mark.asyncio
async def test_skills_install_clawhub_mode_runs_cli_and_refreshes_workspace_inventory(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    observed: dict[str, object] = {}

    async def fake_command_runner(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_ms: int | None,
    ) -> tuple[int, str, str]:
        observed["argv"] = argv
        observed["cwd"] = str(cwd)
        observed["timeout_ms"] = timeout_ms
        skill_path = tmp_path / "skills" / "demo-skill" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(
            """---
name: demo-skill
description: installed from clawhub
platforms:
  - windows
metadata:
  skillKey: demo-skill
---
Body
""",
            encoding="utf-8",
        )
        return (0, "installed", "")

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_clawhub_service=GatewaySkillClawHubService(
            launcher=("clawhub",),
            command_runner=fake_command_runner,
        ),
    )

    installed = await service.call(
        "skills.install",
        {
            "source": "clawhub",
            "slug": "demo-skill",
            "version": "1.2.3",
            "force": True,
        },
    )
    status = await service.call("skills.status", {})

    assert installed == {
        "ok": True,
        "source": "clawhub",
        "action": "install",
        "slug": "demo-skill",
        "version": "1.2.3",
        "force": True,
        "command": [
            "clawhub",
            "install",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.3",
            "--force",
        ],
        "workspaceDir": str(tmp_path),
        "skillsDir": str(tmp_path / "skills"),
    }
    assert observed == {
        "argv": (
            "clawhub",
            "install",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.3",
            "--force",
        ),
        "cwd": str(tmp_path),
        "timeout_ms": None,
    }
    assert status["skills"] == [
        {
            "name": "demo-skill",
            "description": "installed from clawhub",
            "source": "workspace",
            "bundled": False,
            "filePath": str(tmp_path / "skills" / "demo-skill" / "SKILL.md"),
            "baseDir": str(tmp_path / "skills" / "demo-skill"),
            "skillKey": "demo-skill",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": False,
            "blockedByAllowlist": False,
            "eligible": True,
            "requirements": {
                "bins": [],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [],
        }
    ]


@pytest.mark.asyncio
async def test_skills_update_clawhub_mode_runs_cli_and_refreshes_workspace_inventory(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.chdir(tmp_path)
    skill_path = tmp_path / "skills" / "demo-skill" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(
        """---
name: demo-skill
description: before update
platforms:
  - windows
metadata:
  skillKey: demo-skill
---
Body
""",
        encoding="utf-8",
    )
    observed: dict[str, object] = {}

    async def fake_command_runner(
        argv: tuple[str, ...],
        *,
        cwd: Path,
        timeout_ms: int | None,
    ) -> tuple[int, str, str]:
        observed["argv"] = argv
        observed["cwd"] = str(cwd)
        observed["timeout_ms"] = timeout_ms
        skill_path.write_text(
            """---
name: demo-skill
description: updated from clawhub
platforms:
  - windows
metadata:
  skillKey: demo-skill
---
Body
""",
            encoding="utf-8",
        )
        return (0, "updated", "")

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_clawhub_service=GatewaySkillClawHubService(
            launcher=("clawhub",),
            command_runner=fake_command_runner,
        ),
    )

    updated = await service.call(
        "skills.update",
        {
            "source": "clawhub",
            "slug": "demo-skill",
            "version": "1.2.4",
            "force": True,
        },
    )
    status = await service.call("skills.status", {})

    assert updated == {
        "ok": True,
        "source": "clawhub",
        "action": "update",
        "slug": "demo-skill",
        "version": "1.2.4",
        "force": True,
        "all": False,
        "command": [
            "clawhub",
            "update",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.4",
            "--force",
        ],
        "workspaceDir": str(tmp_path),
        "skillsDir": str(tmp_path / "skills"),
    }
    assert observed == {
        "argv": (
            "clawhub",
            "update",
            "demo-skill",
            "--workdir",
            str(tmp_path),
            "--dir",
            "skills",
            "--no-input",
            "--version",
            "1.2.4",
            "--force",
        ),
        "cwd": str(tmp_path),
        "timeout_ms": None,
    }
    assert status["skills"] == [
        {
            "name": "demo-skill",
            "description": "updated from clawhub",
            "source": "workspace",
            "bundled": False,
            "filePath": str(skill_path),
            "baseDir": str(skill_path.parent),
            "skillKey": "demo-skill",
            "primaryEnv": None,
            "emoji": None,
            "homepage": None,
            "always": False,
            "disabled": False,
            "blockedByAllowlist": False,
            "eligible": True,
            "requirements": {
                "bins": [],
                "env": [],
                "config": [],
                "os": ["windows"],
            },
            "missing": {
                "bins": [],
                "env": [],
                "config": [],
                "os": [],
            },
            "configChecks": [],
            "install": [],
        }
    ]


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
async def test_tts_convert_runs_bounded_runtime_when_wired(tmp_path) -> None:
    synthesized_path = tmp_path / "speech.wav"
    synthesized_path.write_bytes(b"RIFFtest-wave",)
    observed: dict[str, object] = {}

    def fake_convert(
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        observed.update(
            {
                "text": text,
                "channel": channel,
                "provider": provider,
                "model_id": model_id,
                "voice_id": voice_id,
            }
        )
        return GatewayTtsSynthesisResult(
            audio_path=str(synthesized_path),
            provider="microsoft",
            output_format="wav",
            voice_compatible=True,
        )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_runtime_service=GatewayTtsRuntimeService(
            data_dir=tmp_path,
            convert_runner=fake_convert,
        ),
    )

    payload = await service.call(
        "tts.convert",
        {
            "text": "Hello from Zues",
            "channel": "assistant",
            "provider": "edge",
            "modelId": "ignored-local-model",
            "voiceId": "Microsoft Zira Desktop",
        },
    )

    assert payload == {
        "audioPath": str(synthesized_path),
        "provider": "microsoft",
        "outputFormat": "wav",
        "voiceCompatible": True,
    }
    assert observed == {
        "text": "Hello from Zues",
        "channel": "assistant",
        "provider": "microsoft",
        "model_id": "ignored-local-model",
        "voice_id": "Microsoft Zira Desktop",
    }


@pytest.mark.asyncio
async def test_tts_convert_normalizes_blank_optional_selectors(tmp_path) -> None:
    synthesized_path = tmp_path / "speech.wav"
    synthesized_path.write_bytes(b"RIFFtest-wave")
    observed: dict[str, object] = {}

    def fake_convert(
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        observed.update(
            {
                "text": text,
                "channel": channel,
                "provider": provider,
                "model_id": model_id,
                "voice_id": voice_id,
            }
        )
        return GatewayTtsSynthesisResult(
            audio_path=str(synthesized_path),
            provider="microsoft",
            output_format="wav",
            voice_compatible=True,
        )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_runtime_service=GatewayTtsRuntimeService(
            data_dir=tmp_path,
            convert_runner=fake_convert,
        ),
    )

    payload = await service.call(
        "tts.convert",
        {
            "text": "Hello from Zues",
            "channel": "   ",
            "provider": "   ",
            "modelId": "   ",
            "voiceId": "   ",
        },
    )

    assert payload == {
        "audioPath": str(synthesized_path),
        "provider": "microsoft",
        "outputFormat": "wav",
        "voiceCompatible": True,
    }
    assert observed == {
        "text": "Hello from Zues",
        "channel": None,
        "provider": "microsoft",
        "model_id": None,
        "voice_id": None,
    }


@pytest.mark.asyncio
async def test_tts_convert_fails_closed_when_runtime_is_disabled() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_runtime_service=GatewayTtsRuntimeService(enabled=False),
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match="TTS conversion runtime not wired in OpenZues yet",
    ) as exc_info:
        await service.call("tts.convert", {"text": "Hello from Zues"})

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_talk_speak_returns_inline_audio_when_runtime_is_wired(tmp_path) -> None:
    synthesized_path = tmp_path / "spoken.wav"
    synthesized_bytes = b"RIFFtalk-wave"
    synthesized_path.write_bytes(synthesized_bytes)
    observed: dict[str, object] = {}

    def fake_convert(
        *,
        text: str,
        channel: str | None,
        provider: str | None,
        model_id: str | None,
        voice_id: str | None,
    ) -> GatewayTtsSynthesisResult:
        observed.update(
            {
                "text": text,
                "channel": channel,
                "provider": provider,
                "model_id": model_id,
                "voice_id": voice_id,
            }
        )
        return GatewayTtsSynthesisResult(
            audio_path=str(synthesized_path),
            provider="microsoft",
            output_format="wav",
            voice_compatible=True,
        )

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_runtime_service=GatewayTtsRuntimeService(
            data_dir=tmp_path,
            convert_runner=fake_convert,
        ),
    )

    payload = await service.call(
        "talk.speak",
        {
            "text": "Hello from talk mode.",
            "provider": "edge",
            "voiceId": "Microsoft Zira Desktop",
            "outputFormat": "wav",
            "rateWpm": 180,
        },
    )

    assert payload == {
        "audioBase64": base64.b64encode(synthesized_bytes).decode("ascii"),
        "provider": "microsoft",
        "outputFormat": "wav",
        "voiceCompatible": True,
        "mimeType": "audio/wav",
        "fileExtension": ".wav",
    }
    assert observed == {
        "text": "Hello from talk mode.",
        "channel": None,
        "provider": "microsoft",
        "model_id": None,
        "voice_id": "Microsoft Zira Desktop",
    }


@pytest.mark.asyncio
async def test_talk_speak_rejects_rate_wpm_that_resolves_outside_upstream_window(
    tmp_path,
) -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        tts_runtime_service=GatewayTtsRuntimeService(
            data_dir=tmp_path,
            convert_runner=lambda **_: (_ for _ in ()).throw(
                AssertionError("convert_runner should not be reached for invalid talk.speak")
            ),
        ),
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match="invalid talk.speak params: rateWpm must resolve to speed between 0.5 and 2.0",
    ) as exc_info:
        await service.call(
            "talk.speak",
            {
                "text": "Hello from talk mode.",
                "rateWpm": 350,
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_skills_install_clawhub_mode_fails_closed_when_gateway_host_lacks_cli() -> None:
    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        skill_clawhub_service=GatewaySkillClawHubService(resolve_launcher=False),
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match="ClawHub CLI is not available on the gateway host.",
    ) as exc_info:
        await service.call(
            "skills.install",
            {"source": "clawhub", "slug": "openclaw/example"},
        )

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
async def test_system_event_records_event_and_broadcasts_presence_snapshot(tmp_path) -> None:
    database = Database(tmp_path / "system-event.db")
    await database.initialize()
    registry = GatewayNodeRegistry()
    _register_ios_node(registry)
    hub = BroadcastHub()
    service = GatewayNodeMethodService(
        registry,
        database=database,
        hub=hub,
        gateway_identity_service=GatewayIdentityService(tmp_path),
    )

    async with hub.subscribe() as queue:
        response = await service.call(
            "system-event",
            {
                "text": "note from test",
                "deviceId": "device-1",
                "instanceId": "instance-1",
                "roles": ["operator", "operator", "  "],
                "tags": ["gateway", "test"],
            },
            now_ms=1_700_000_000_000,
        )
        broadcast = await asyncio.wait_for(queue.get(), timeout=1.0)

    events = await database.list_events()

    assert response == {"ok": True}
    assert len(events) == 1
    assert events[0]["instance_id"] is None
    assert events[0]["thread_id"] is None
    assert events[0]["method"] == "system-event"
    assert events[0]["payload"] == {
        "text": "note from test",
        "deviceId": "device-1",
        "instanceId": "instance-1",
        "roles": ["operator"],
        "tags": ["gateway", "test"],
    }

    assert broadcast["type"] == "gateway_event"
    assert broadcast["event"] == "presence"
    assert isinstance(broadcast["createdAt"], str)
    assert "presence" in broadcast["payload"]
    assert isinstance(broadcast["payload"]["presence"], list)
    node_entry = next(
        entry for entry in broadcast["payload"]["presence"] if entry.get("deviceId") == "node-1"
    )
    assert node_entry["host"] == "Builder Phone"
    self_entry = next(
        entry
        for entry in broadcast["payload"]["presence"]
        if entry.get("reason") == "self"
    )
    assert self_entry["deviceId"].startswith("gateway-")


@pytest.mark.asyncio
async def test_secrets_reload_counts_enabled_broken_secret_refs() -> None:
    now = datetime.now(UTC)
    probed_secret_ids: list[int] = []

    async def fake_list_integration_views() -> list[IntegrationView]:
        return [
            IntegrationView(
                id=1,
                name="Healthy GitHub",
                kind="github",
                base_url="https://api.github.com",
                auth_scheme="token",
                vault_secret_id=1,
                vault_secret_label="GITHUB_TOKEN",
                has_secret=True,
                secret_preview="****1234",
                auth_status="satisfied",
                auth_detail="Vault secret 'GITHUB_TOKEN' is attached.",
                enabled=True,
                created_at=now,
                updated_at=now,
            ),
            IntegrationView(
                id=2,
                name="Broken GitHub",
                kind="github",
                base_url="https://api.github.com",
                auth_scheme="token",
                vault_secret_id=9,
                vault_secret_label=None,
                has_secret=False,
                secret_preview=None,
                auth_status="degraded",
                auth_detail="Referenced vault secret is missing.",
                enabled=True,
                created_at=now,
                updated_at=now,
            ),
            IntegrationView(
                id=3,
                name="Missing Credential",
                kind="github",
                base_url="https://api.github.com",
                auth_scheme="token",
                vault_secret_id=None,
                vault_secret_label=None,
                has_secret=False,
                secret_preview=None,
                auth_status="missing",
                auth_detail="Attach a vault secret before using this integration.",
                enabled=True,
                created_at=now,
                updated_at=now,
            ),
            IntegrationView(
                id=4,
                name="Disabled Broken GitHub",
                kind="github",
                base_url="https://api.github.com",
                auth_scheme="token",
                vault_secret_id=10,
                vault_secret_label=None,
                has_secret=False,
                secret_preview=None,
                auth_status="degraded",
                auth_detail="Referenced vault secret is missing.",
                enabled=False,
                created_at=now,
                updated_at=now,
            ),
        ]

    async def fake_list_notification_route_views() -> list[NotificationRouteView]:
        return [
            NotificationRouteView(
                id=7,
                name="Healthy Webhook",
                kind="webhook",
                target="https://example.invalid/healthy",
                events=["mission/completed"],
                enabled=True,
                vault_secret_id=1,
                vault_secret_label="Webhook secret",
                has_secret=True,
                secret_preview="****1234",
                created_at=now,
                updated_at=now,
            ),
            NotificationRouteView(
                id=8,
                name="Broken Webhook",
                kind="webhook",
                target="https://example.invalid/broken",
                events=["mission/completed"],
                enabled=True,
                vault_secret_id=11,
                vault_secret_label=None,
                has_secret=False,
                secret_preview=None,
                created_at=now,
                updated_at=now,
            ),
            NotificationRouteView(
                id=9,
                name="No Secret Webhook",
                kind="webhook",
                target="https://example.invalid/no-secret",
                events=["mission/completed"],
                enabled=True,
                vault_secret_id=None,
                vault_secret_label=None,
                has_secret=False,
                secret_preview=None,
                created_at=now,
                updated_at=now,
            ),
            NotificationRouteView(
                id=10,
                name="Disabled Broken Webhook",
                kind="webhook",
                target="https://example.invalid/disabled-broken",
                events=["mission/completed"],
                enabled=False,
                vault_secret_id=12,
                vault_secret_label=None,
                has_secret=False,
                secret_preview=None,
                created_at=now,
                updated_at=now,
            ),
        ]

    async def fake_probe_secret(secret_id: int) -> str | None:
        probed_secret_ids.append(secret_id)
        return {
            1: None,
            11: "Referenced vault secret is missing.",
            12: "Referenced vault secret is missing.",
        }.get(secret_id)

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        list_integration_views=fake_list_integration_views,
        list_notification_route_views=fake_list_notification_route_views,
        probe_secret=fake_probe_secret,
    )

    payload = await service.call("secrets.reload", {})

    assert payload == {"ok": True, "warningCount": 2}
    assert probed_secret_ids == [1, 11]


@pytest.mark.asyncio
async def test_secrets_resolve_returns_validated_unavailable_contract() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=(
            "secrets.resolve is unavailable until command-target secret resolution is wired"
        ),
    ) as exc_info:
        await service.call(
            "secrets.resolve",
            {
                "commandName": "memory status",
                "targetIds": ["talk.providers.*.apiKey"],
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_message_action_reports_unsupported_action_for_known_channel() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=r"Channel whatsapp does not support action react\.",
    ) as exc_info:
        await service.call(
            "message.action",
            {
                "channel": "whatsapp",
                "action": "react",
                "params": {
                    "chatJid": "+15551234567",
                    "messageId": "wamid.1",
                    "emoji": "✅",
                },
                "accountId": "default",
                "requesterSenderId": "trusted-user",
                "senderIsOwner": True,
                "sessionKey": "agent:main:whatsapp:+15551234567",
                "sessionId": "session-123",
                "agentId": "main",
                "toolContext": {
                    "currentChannelId": "channel:team:general",
                    "currentGraphChannelId": "graph:team/general",
                    "currentChannelProvider": "whatsapp",
                    "currentThreadTs": "1710000000.9999",
                    "currentMessageId": "wamid.1",
                    "replyToMode": "first",
                    "hasRepliedRef": {"value": True},
                    "skipCrossContextDecoration": True,
                },
                "idempotencyKey": "idem-message-action",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_message_action_rejects_internal_webchat_channel() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=(
            "unsupported channel: webchat \\(internal-only\\)\\. Use `chat.send` for "
            "WebChat UI messages or choose a deliverable channel\\."
        ),
    ) as exc_info:
        await service.call(
            "message.action",
            {
                "channel": "webchat",
                "action": "react",
                "params": {
                    "messageId": "webchat.1",
                    "emoji": "ok",
                },
                "idempotencyKey": "idem-message-action-webchat",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_message_action_auto_picks_single_notification_route_channel_when_omitted() -> None:
    now = datetime.now(UTC)

    async def fake_list_notification_route_views() -> list[NotificationRouteView]:
        return [
            NotificationRouteView(
                id=1,
                name="Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission/completed"],
                conversation_target=ConversationTargetView(
                    channel="slack",
                    account_id="workspace-bot",
                    peer_kind="channel",
                    peer_id="deploy-room",
                ),
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        ]

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        list_notification_route_views=fake_list_notification_route_views,
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match=r"Channel slack does not support action react\.",
    ) as exc_info:
        await service.call(
            "message.action",
            {
                "action": "react",
                "params": {
                    "messageId": "slack.1",
                    "emoji": "ok",
                },
                "idempotencyKey": "idem-message-action-autopick",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "extra_params"),
    [
        (
            "accountId",
            {"accountId": "   "},
        ),
        (
            "requesterSenderId",
            {"requesterSenderId": "   "},
        ),
        (
            "sessionKey",
            {"sessionKey": "   "},
        ),
        (
            "sessionId",
            {"sessionId": "   "},
        ),
        (
            "agentId",
            {"agentId": "   "},
        ),
    ],
)
async def test_message_action_allows_blank_optional_routing_identifiers(
    field: str,
    extra_params: dict[str, str],
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=r"Channel slack does not support action react\.",
    ) as exc_info:
        await service.call(
            "message.action",
            {
                "channel": "slack",
                "action": "react",
                "params": {
                    "messageId": "slack.1",
                    "emoji": "ok",
                },
                "idempotencyKey": f"idem-message-action-blank-{field}",
                **extra_params,
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_send_returns_validated_unavailable_contract() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="send is unavailable until channel-target outbound delivery is wired",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": "channel:C123",
                "message": "Ship parity.",
                "channel": "slack",
                "accountId": "default",
                "agentId": "main",
                "threadId": "1710000000.9999",
                "sessionKey": "agent:main:slack:channel:C123",
                "idempotencyKey": "idem-send",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_send_accepts_valid_whatsapp_target_shape_before_delivery_placeholder() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="send is unavailable until channel-target outbound delivery is wired",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": " (555) 123-4567 ",
                "message": "Ship parity.",
                "channel": "whatsapp",
                "idempotencyKey": "idem-send-whatsapp-valid",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_send_rejects_invalid_whatsapp_target_shape() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="WhatsApp target is required",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": "wat",
                "message": "Ship parity.",
                "channel": "whatsapp",
                "idempotencyKey": "idem-send-whatsapp-invalid",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_send_accepts_valid_telegram_topic_target_shape_before_delivery_placeholder() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="send is unavailable until channel-target outbound delivery is wired",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": " telegram:-100123:topic:77 ",
                "message": "Ship parity.",
                "channel": "telegram",
                "idempotencyKey": "idem-send-telegram-topic",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_send_rejects_blank_telegram_target_shape() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="Telegram target is required",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": "   ",
                "message": "Ship parity.",
                "channel": "telegram",
                "idempotencyKey": "idem-send-telegram-blank",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "extra_params"),
    [
        (
            "accountId",
            {"accountId": "   "},
        ),
        (
            "agentId",
            {"agentId": "   "},
        ),
        (
            "threadId",
            {"threadId": "   "},
        ),
        (
            "sessionKey",
            {"sessionKey": "   "},
        ),
    ],
)
async def test_send_allows_blank_optional_routing_identifiers(
    field: str,
    extra_params: dict[str, str],
) -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="send is unavailable until channel-target outbound delivery is wired",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": "channel:C123",
                "message": "Ship parity.",
                "channel": "slack",
                "idempotencyKey": f"idem-send-blank-{field}",
                **extra_params,
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_send_rejects_internal_webchat_channel() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=(
            "unsupported channel: webchat \\(internal-only\\)\\. Use `chat.send` for "
            "WebChat UI messages or choose a deliverable channel\\."
        ),
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": "channel:C123",
                "message": "Ship parity.",
                "channel": "webchat",
                "idempotencyKey": "idem-send-webchat",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_send_rejects_missing_channel_when_multiple_route_channels_configured() -> None:
    now = datetime.now(UTC)

    async def fake_list_notification_route_views() -> list[NotificationRouteView]:
        return [
            NotificationRouteView(
                id=1,
                name="Slack Route",
                kind="webhook",
                target="https://example.invalid/slack",
                events=["mission/completed"],
                conversation_target=ConversationTargetView(
                    channel="slack",
                    account_id="workspace-bot",
                    peer_kind="channel",
                    peer_id="deploy-room",
                ),
                enabled=True,
                created_at=now,
                updated_at=now,
            ),
            NotificationRouteView(
                id=2,
                name="Telegram Route",
                kind="webhook",
                target="https://example.invalid/telegram",
                events=["mission/completed"],
                conversation_target=ConversationTargetView(
                    channel="telegram",
                    account_id="default",
                    peer_kind="group",
                    peer_id="12345",
                ),
                enabled=True,
                created_at=now,
                updated_at=now,
            ),
        ]

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        list_notification_route_views=fake_list_notification_route_views,
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match="Channel is required when multiple channels are configured: slack, telegram",
    ) as exc_info:
        await service.call(
            "send",
            {
                "to": "channel:C123",
                "message": "Ship parity.",
                "idempotencyKey": "idem-send-no-channel",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_poll_returns_validated_unavailable_contract() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="poll is unavailable until channel-target poll delivery is wired",
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "channel:C123",
                "question": "Ship it?",
                "options": ["Yes", "No"],
                "maxSelections": 1,
                "durationSeconds": 3600,
                "channel": "slack",
                "accountId": "default",
                "idempotencyKey": "idem-poll",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_poll_allows_thread_id_before_delivery_placeholder() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="poll is unavailable until channel-target poll delivery is wired",
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "channel:C123",
                "question": "Ship it?",
                "options": ["Yes", "No"],
                "maxSelections": 1,
                "durationSeconds": 3600,
                "channel": "slack",
                "accountId": "default",
                "threadId": "1710000000.9999",
                "idempotencyKey": "idem-poll-thread",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_poll_rejects_invalid_whatsapp_target_shape() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="WhatsApp target is required",
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "wat",
                "question": "Where next?",
                "options": ["Now", "Later"],
                "channel": "whatsapp",
                "idempotencyKey": "idem-poll-whatsapp-invalid",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_poll_rejects_blank_telegram_target_shape() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="Telegram target is required",
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "   ",
                "question": "Where next?",
                "options": ["Now", "Later"],
                "channel": "telegram",
                "idempotencyKey": "idem-poll-telegram-blank",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_poll_allows_blank_account_id() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match="poll is unavailable until channel-target poll delivery is wired",
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "channel:C123",
                "question": "Where next?",
                "options": ["Now", "Later"],
                "channel": "slack",
                "accountId": "   ",
                "idempotencyKey": "idem-poll-blank-account",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_poll_rejects_internal_webchat_channel() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(
        GatewayNodeMethodError,
        match=(
            "unsupported channel: webchat \\(internal-only\\)\\. Use `chat.send` for "
            "WebChat UI messages or choose a deliverable channel\\."
        ),
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "channel:C123",
                "question": "Where next?",
                "options": ["Now", "Later"],
                "channel": "webchat",
                "idempotencyKey": "idem-poll-webchat",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_poll_rejects_missing_channel_when_no_route_channels_configured() -> None:
    async def fake_list_notification_route_views() -> list[NotificationRouteView]:
        return []

    service = GatewayNodeMethodService(
        GatewayNodeRegistry(),
        list_notification_route_views=fake_list_notification_route_views,
    )

    with pytest.raises(
        GatewayNodeMethodError,
        match=r"Channel is required \(no configured channels detected\)\.",
    ) as exc_info:
        await service.call(
            "poll",
            {
                "to": "channel:C123",
                "question": "Where next?",
                "options": ["Now", "Later"],
                "idempotencyKey": "idem-poll-no-channel",
            },
        )

    assert exc_info.value.code == "INVALID_REQUEST"
    assert exc_info.value.status_code == 400


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
