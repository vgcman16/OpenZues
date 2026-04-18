from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from openzues.database import Database
from openzues.schemas import ConversationTargetView, NotificationRouteView, TaskBlueprintCreate
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
from openzues.services.gateway_voicewake import GatewayVoiceWakeService
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
        "updatedAt": 111,
        "sessionId": None,
        "kind": "global",
        "subject": "Operator control chat",
        "displayName": "OpenZues Control Chat",
        "systemSent": None,
        "abortedLastRun": None,
        "thinkingLevel": None,
        "verboseLevel": None,
        "inputTokens": None,
        "outputTokens": None,
        "totalTokens": None,
        "contextTokens": None,
        "modelProvider": "openai",
        "model": "gpt-5.4",
        "space": None,
    }
    assert isinstance(sessions_changed[0]["createdAt"], str)


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
        now_ms=666,
    )

    assert payload == {
        "ok": True,
        "key": session_key,
        "deleted": True,
        "archived": [],
    }
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
async def test_sessions_compact_fails_explicitly_until_compaction_runtime_is_wired() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compact", {})

    with pytest.raises(ValueError, match="maxLines must be between 1 and 1000000"):
        await service.call(
            "sessions.compact",
            {"key": "openzues:thread:demo", "maxLines": 0},
        )

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.compact",
            {"key": "openzues:thread:demo", "maxLines": 200},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.compact is unavailable until control chat compaction is wired"
    )


@pytest.mark.asyncio
async def test_sessions_compaction_restore_fails_explicitly_until_restore_runtime_is_wired() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.restore", {})

    with pytest.raises(ValueError, match="checkpointId must be a non-empty string"):
        await service.call(
            "sessions.compaction.restore",
            {"key": "openzues:thread:demo"},
        )

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.compaction.restore",
            {
                "key": "openzues:thread:demo",
                "checkpointId": "checkpoint-001",
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.compaction.restore is unavailable until control chat compaction restore is wired"
    )


@pytest.mark.asyncio
async def test_sessions_compaction_list_fails_explicitly_until_checkpoint_inventory_is_wired() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.list", {})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.compaction.list",
            {"key": "openzues:thread:demo"},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.compaction.list is unavailable until control chat compaction "
        "checkpoints are wired"
    )


@pytest.mark.asyncio
async def test_sessions_compaction_get_fails_explicitly_until_checkpoint_inventory_is_wired() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.get", {})

    with pytest.raises(ValueError, match="checkpointId must be a non-empty string"):
        await service.call(
            "sessions.compaction.get",
            {"key": "openzues:thread:demo"},
        )

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.compaction.get",
            {"key": "openzues:thread:demo", "checkpointId": "checkpoint-001"},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.compaction.get is unavailable until control chat compaction checkpoints are wired"
    )


@pytest.mark.asyncio
async def test_sessions_compaction_branch_fails_explicitly_until_branch_runtime_is_wired() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.compaction.branch", {})

    with pytest.raises(ValueError, match="checkpointId must be a non-empty string"):
        await service.call(
            "sessions.compaction.branch",
            {"key": "openzues:thread:demo"},
        )

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.compaction.branch",
            {"key": "openzues:thread:demo", "checkpointId": "checkpoint-001"},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.compaction.branch is unavailable until control chat compaction branching is wired"
    )


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
async def test_sessions_subscribe_returns_stateless_ack_without_connection_context() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    payload = await service.call("sessions.subscribe", {})

    assert payload == {"subscribed": False}


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


@pytest.mark.asyncio
async def test_sessions_usage_fails_explicitly_until_analytics_runtime_is_wired() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="mode must be one of: gateway, specific, utc"):
        await service.call("sessions.usage", {"mode": "broken"})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.usage",
            {
                "key": "openzues:thread:demo",
                "startDate": "2026-04-01",
                "endDate": "2026-04-18",
                "mode": "specific",
                "utcOffset": "UTC-5",
                "limit": 50,
                "includeContextWeight": False,
            },
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.usage is unavailable until session usage analytics are wired"
    )


@pytest.mark.asyncio
async def test_sessions_usage_timeseries_fails_explicitly_until_analytics_runtime_is_wired() -> (
    None
):
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="key must be a non-empty string"):
        await service.call("sessions.usage.timeseries", {})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.usage.timeseries",
            {"key": "openzues:thread:demo"},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.usage.timeseries is unavailable until session usage analytics are wired"
    )


@pytest.mark.asyncio
async def test_sessions_usage_logs_fails_explicitly_until_analytics_runtime_is_wired() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

    with pytest.raises(ValueError, match="limit must be between 1 and 1000"):
        await service.call("sessions.usage.logs", {"key": "openzues:thread:demo", "limit": 0})

    with pytest.raises(GatewayNodeMethodError) as exc_info:
        await service.call(
            "sessions.usage.logs",
            {"key": "openzues:thread:demo", "limit": 200},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503
    assert exc_info.value.message == (
        "sessions.usage.logs is unavailable until session usage analytics are wired"
    )


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
async def test_wake_requires_openclaw_shape_then_fails_as_explicit_unavailable() -> None:
    service = GatewayNodeMethodService(GatewayNodeRegistry())

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

    with pytest.raises(
        GatewayNodeMethodError,
        match="wake is unavailable until control-plane wake queue is wired",
    ) as exc_info:
        await service.call(
            "wake",
            {"mode": "now", "text": "Resume parity from the latest checkpoint."},
        )

    assert exc_info.value.code == "UNAVAILABLE"
    assert exc_info.value.status_code == 503


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

    with pytest.raises(ValueError, match="sessionKey is malformed"):
        await service.call("agent.identity.get", {"sessionKey": "agent:main"})


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
