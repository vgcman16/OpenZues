import asyncio
import codecs
import json
import os
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from typer.testing import CliRunner

import openzues.app as app_module
import openzues.cli as cli_module
from openzues.app import create_app
from openzues.cli import (
    _append_watch_log,
    _close_services,
    _emit_attention_queue_action,
    _emit_continue_action,
    _emit_gateway_bootstrap,
    _emit_gateway_capability,
    _emit_status,
    _summarize_browser_snapshot,
    _watch_browser_verify,
    app,
)
from openzues.database import Database
from openzues.schemas import (
    ControlChatMessageView,
    ControlChatResponse,
    GatewayCapabilityView,
    MissionDraftView,
)
from openzues.services.control_chat import ControlChatPlan
from openzues.services.device_bootstrap_profile import BOOTSTRAP_HANDOFF_OPERATOR_SCOPES
from openzues.services.gateway_config import GatewayConfigService
from openzues.services.gateway_method_policy import list_known_gateway_methods
from openzues.services.ops_mesh import OUTBOUND_DELIVERY_MAX_RETRIES
from openzues.settings import Settings

runner = CliRunner()


def _bootstrap_cli_workspace(tmp_path, monkeypatch, *, task_name: str = "CLI Gateway Loop") -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(data_dir))
    bootstrap = runner.invoke(
        app,
        [
            "setup",
            "bootstrap",
            "--project-path",
            str(tmp_path),
            "--operator-name",
            "CLI Builder",
            "--task-name",
            task_name,
            "--objective-template",
            "Ship the next verified gateway slice.",
            "--json",
        ],
    )
    assert bootstrap.exit_code == 0, bootstrap.stdout


def test_close_services_shuts_down_background_service_loops() -> None:
    events: list[str] = []

    class _AsyncRecorder:
        def __init__(self, name: str) -> None:
            self.name = name

        async def close(self) -> None:
            events.append(self.name)

    class _ControlChatRecorder:
        async def close_attention_queue(self) -> None:
            events.append("control_chat")

    services = SimpleNamespace(
        control_chat=_ControlChatRecorder(),
        runtime_updates=_AsyncRecorder("runtime_updates"),
        hermes_platform=_AsyncRecorder("hermes_platform"),
        ops_mesh=_AsyncRecorder("ops_mesh"),
        mission_service=_AsyncRecorder("mission_service"),
        manager=_AsyncRecorder("manager"),
    )

    asyncio.run(_close_services(services))

    assert events == [
        "control_chat",
        "runtime_updates",
        "hermes_platform",
        "ops_mesh",
        "mission_service",
        "manager",
    ]


def _watch_dashboard_payload(*, mission_status: str = "paused") -> dict[str, object]:
    return {
        "brief": {
            "headline": "Control plane is connected and ready",
            "summary": "Launch a mission, start a thread manually, or prepare the workspace.",
            "focus_mission_id": 35,
        },
        "control_chat": {
            "headline": "Tell Zues what to do next",
            "summary": "Chat is active in the leader window.",
            "messages": [],
        },
        "attention_queue": {
            "enabled": True,
            "headline": "Attention queue is standing by",
            "summary": "Recoveries and checkpoint hardeners can auto-launch.",
            "actions": [],
        },
        "instances": [
            {
                "id": 2,
                "name": "Local Codex Desktop",
                "connected": True,
            }
        ],
        "missions": [
            {
                "id": 35,
                "name": "OpenClaw Total Parity Program",
                "status": mission_status,
                "phase": "paused" if mission_status == "paused" else "ready",
                "task_blueprint_id": 2,
                "toolsets": ["delegation", "browser", "debugging"],
                "current_command": "python -m pytest tests/test_cli.py -q",
                "last_commentary": "Watching the parity lane and verifying the next relay.",
                "last_checkpoint": "Checkpoint ready for the next parity slice.",
                "last_error": None,
                "in_progress": mission_status == "active",
                "live_telemetry": {
                    "streaming": mission_status == "active",
                    "summary": (
                        "Streaming now with 3 thread events in the last 30s."
                        if mission_status == "active"
                        else "Mission is queued for the next live relay."
                    ),
                },
                "delegation_brief": {
                    "summary": "Built-in agents are armed for the parity run.",
                },
            }
        ],
        "gateway_capability": {
            "level": "ready",
            "headline": "Gateway capability is aligned",
            "summary": "The saved launch posture is clear and lane health is stable.",
        },
    }


def _watch_handoff_payload() -> dict[str, object]:
    return {
        "status": "ready",
        "headline": "Saved launch handoff is ready",
        "summary": "The saved lane, remote operator, and recurring task are aligned.",
        "recommended_action": "load_draft",
        "action_label": "Load launch draft",
        "warnings": [],
        "next_entrypoint": "Load the saved launch draft, then run the next verified mission cycle.",
        "instance": {"id": 2, "label": "Local Codex Desktop", "connected": True},
        "task_blueprint": {"id": 2, "label": "OpenClaw Total Parity Program"},
        "mission_draft": {
            "name": "OpenClaw Total Parity Program",
            "objective": "Continue the verified parity program.",
            "instance_id": 2,
            "project_id": 1,
            "task_blueprint_id": 2,
            "cwd": "C:\\Users\\skull\\OneDrive\\Documents\\OpenZues",
            "model": "gpt-5.4",
            "reasoning_effort": "high",
            "max_turns": 8,
            "use_builtin_agents": True,
            "run_verification": True,
            "auto_commit": False,
            "pause_on_approval": True,
            "allow_auto_reflexes": True,
            "auto_recover": True,
            "auto_recover_limit": 2,
            "reflex_cooldown_seconds": 900,
            "allow_failover": True,
            "toolsets": ["delegation", "browser", "debugging"],
            "start_immediately": True,
        },
    }


def test_emit_continue_action_human_output(capsys) -> None:
    _emit_continue_action(
        {
            "mode": "plan",
            "executed": False,
            "action_kind": "launch_opportunity",
            "reply": (
                "I launched `Stabilize gateway posture` because Gateway Doctor says "
                "Connected lanes need repair before launch."
            ),
            "target_label": "Stabilize gateway posture",
            "opportunity_id": "gateway-repair",
            "mission_id": 17,
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "I launched `Stabilize gateway posture`" in output
    assert "mode: plan" in output
    assert "action: launch_opportunity" in output
    assert "target: Stabilize gateway posture" in output
    assert "opportunity: gateway-repair" in output
    assert "mission: 17" in output


def test_emit_attention_queue_action_human_output(capsys) -> None:
    _emit_attention_queue_action(
        {
            "mode": "plan",
            "executed": False,
            "action_kind": "launch_opportunity",
            "status": "executed",
            "reply": (
                "I launched `Stabilize gateway posture` from the attention queue because "
                "Gateway Doctor says connected lanes need repair before launch."
            ),
            "signal_id": "gateway-health-burn",
            "target_label": "Stabilize gateway posture",
            "opportunity_id": "gateway-repair",
            "mission_id": 17,
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "I launched `Stabilize gateway posture` from the attention queue" in output
    assert "mode: plan" in output
    assert "executed: False" in output
    assert "action: launch_opportunity" in output
    assert "status: executed" in output
    assert "signal: gateway-health-burn" in output
    assert "target: Stabilize gateway posture" in output
    assert "opportunity: gateway-repair" in output
    assert "mission: 17" in output


def test_gateway_doctor_json_includes_gateway_capability_summary(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["gateway", "doctor", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        api_payload = client.get("/api/gateway/capability").json()

    cli_payload = {key: value for key, value in payload.items() if key != "checked_at"}
    api_payload = {key: value for key, value in api_payload.items() if key != "checked_at"}
    if "diagnostics" in cli_payload and "diagnostics" in api_payload:
        for key in ("ok_count", "warn_count", "fail_count"):
            cli_payload["diagnostics"].pop(key, None)
            api_payload["diagnostics"].pop(key, None)

    assert payload["headline"]
    assert "connected_lane_health" in payload
    assert "inventory" in payload
    assert "memory_summary" in payload["inventory"]
    assert "approval_posture" in payload
    assert "launch_policy" in payload
    assert payload["launch_policy"]["setup_mode"] == "local"
    assert cli_payload == api_payload


def test_gateway_doctor_prefers_live_gateway_view_when_available(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        gateway_payload = client.get("/api/gateway/capability").json()

    gateway_payload["headline"] = "Live gateway headline"
    gateway_payload["summary"] = "Live gateway summary"

    async def fake_live_gateway(_settings: Settings) -> GatewayCapabilityView:
        return GatewayCapabilityView.model_validate(gateway_payload)

    monkeypatch.setattr(cli_module, "_try_live_gateway_capability_view", fake_live_gateway)

    result = runner.invoke(app, ["gateway", "doctor", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["headline"] == "Live gateway headline"
    assert payload["summary"] == "Live gateway summary"


def test_agents_list_json_includes_saved_workspace_inventory(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Agents Loop")

    result = runner.invoke(app, ["agents", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["defaultId"] == "main"
    assert payload["mainKey"] == "main"
    assert payload["scope"] == "global"
    assert payload["agents"] == [
        {
            "id": "main",
            "name": "OpenZues",
            "identity": {
                "name": "OpenZues",
                "avatar": "/static/favicon.svg",
                "avatarUrl": "/static/favicon.svg",
                "emoji": None,
            },
            "workspace": str(tmp_path),
            "model": {"primary": "gpt-5.4"},
        }
    ]


def test_channels_status_json_includes_saved_notification_routes(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Channels Loop")

    database = Database(data_dir / "openzues.db")
    asyncio.run(database.initialize())
    asyncio.run(
        database.create_notification_route(
            name="CLI Slack Route",
            kind="webhook",
            target="https://example.invalid/slack",
            events=["mission/completed"],
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
                "summary": "slack workspace-bot channel deploy-room",
            },
            enabled=True,
            secret_header_name=None,
            secret_token=None,
            vault_secret_id=None,
        )
    )

    result = runner.invoke(app, ["channels", "status", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["routeCount"] == 1
    assert payload["enabledCount"] == 1
    assert payload["conversationTargetCount"] == 1
    assert payload["channelOrder"] == ["discord", "slack", "telegram", "whatsapp"]
    assert payload["channelLabels"]["slack"] == "Slack"
    assert payload["channelDetailLabels"]["slack"] == "Slack"
    assert payload["channels"]["slack"] == {
        "routeCount": 1,
        "enabledRouteCount": 1,
        "conversationTargetCount": 1,
        "accountCount": 1,
    }
    assert payload["channelAccounts"]["slack"] == [
        {
            "accountId": "workspace-bot",
            "routeCount": 1,
            "enabledRouteCount": 1,
            "conversationTargetCount": 1,
        }
    ]
    assert payload["channelDefaultAccountId"]["slack"] == "workspace-bot"


def test_sandbox_list_json_returns_openclaw_shaped_inventory(monkeypatch) -> None:
    class FakeDatabase:
        async def list_gateway_session_metadata_rows(self) -> list[dict[str, object]]:
            return []

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(database=FakeDatabase()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["sandbox", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout) == {"containers": [], "browsers": []}


def test_sandbox_list_json_surfaces_saved_sandbox_runtime_metadata(monkeypatch) -> None:
    class FakeDatabase:
        async def list_gateway_session_metadata_rows(self) -> list[dict[str, object]]:
            return [
                {
                    "session_key": "agent:main:subagent:sandbox-worker",
                    "updated_at": "2026-04-29T12:00:00Z",
                    "metadata": {
                        "runtime": "codex-app-server",
                        "runtimeId": 7,
                        "runtimeThreadId": "thread-7",
                        "runtimeSessionId": "thread-7",
                        "sandboxed": True,
                        "sandboxMode": "workspace-write",
                        "sandboxPolicy": {"type": "workspaceWrite"},
                    },
                },
                {
                    "session_key": "agent:main:subagent:plain-worker",
                    "metadata": {"label": "Plain worker"},
                },
            ]

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(database=FakeDatabase()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["sandbox", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["browsers"] == []
    assert payload["containers"] == [
        {
            "sessionKey": "agent:main:subagent:sandbox-worker",
            "runtime": "codex-app-server",
            "runtimeId": 7,
            "runtimeThreadId": "thread-7",
            "runtimeSessionId": "thread-7",
            "sandboxMode": "workspace-write",
            "sandboxPolicy": {"type": "workspaceWrite"},
            "status": "known",
            "source": "session_metadata",
            "updatedAt": "2026-04-29T12:00:00Z",
        }
    ]


def test_sandbox_list_human_output_includes_total_summary(monkeypatch) -> None:
    class FakeDatabase:
        async def list_gateway_session_metadata_rows(self) -> list[dict[str, object]]:
            return [
                {
                    "session_key": "agent:main:subagent:sandbox-worker",
                    "metadata": {
                        "runtime": "codex-app-server",
                        "sandboxed": True,
                        "sandboxMode": "workspace-write",
                    },
                }
            ]

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(database=FakeDatabase()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["sandbox", "list"])

    assert result.exit_code == 0, result.stdout
    assert "[container] agent:main:subagent:sandbox-worker (known)" in result.stdout
    assert "Total: 1 (0 running)" in result.stdout


def test_sandbox_list_human_output_warns_on_config_mismatch(monkeypatch) -> None:
    class FakeDatabase:
        async def list_gateway_session_metadata_rows(self) -> list[dict[str, object]]:
            return [
                {
                    "session_key": "agent:main:subagent:sandbox-worker",
                    "metadata": {
                        "runtime": "codex-app-server",
                        "sandboxed": True,
                        "sandboxMode": "workspace-write",
                        "imageMatch": False,
                    },
                }
            ]

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(database=FakeDatabase()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["sandbox", "list"])

    assert result.exit_code == 0, result.stdout
    assert "1 runtime(s) with config mismatch detected." in result.stdout
    assert "sandbox recreate --all" in result.stdout


def test_acp_bridge_command_reports_native_runtime_unavailable() -> None:
    result = runner.invoke(
        app,
        [
            "acp",
            "--url",
            "ws://gateway.invalid/openzues",
            "--session",
            "agent:main:main",
            "--provenance",
            "meta",
        ],
    )

    assert result.exit_code == 1
    assert "ACP Gateway bridge is not available" in result.stderr
    assert "sessions spawn --runtime acp" in result.stderr


def test_acp_client_command_reports_native_runtime_unavailable() -> None:
    result = runner.invoke(
        app,
        [
            "acp",
            "client",
            "--cwd",
            r"C:\work\OpenZues",
            "--server",
            "openzues",
            "--verbose",
        ],
    )

    assert result.exit_code == 1
    assert "ACP client bridge is not available" in result.stderr
    assert r"C:\work\OpenZues" in result.stderr


def test_sandbox_recreate_session_force_json_forgets_saved_sandbox_metadata(monkeypatch) -> None:
    deleted: list[str] = []

    class FakeDatabase:
        async def list_gateway_session_metadata_rows(self) -> list[dict[str, object]]:
            return [
                {
                    "session_key": "agent:main:subagent:sandbox-worker",
                    "metadata": {
                        "runtime": "codex-app-server",
                        "runtimeId": 7,
                        "runtimeThreadId": "thread-7",
                        "runtimeSessionId": "thread-7",
                        "sandboxed": True,
                        "sandboxMode": "workspace-write",
                        "sandboxPolicy": {"type": "workspaceWrite"},
                    },
                },
                {
                    "session_key": "agent:main:subagent:plain-worker",
                    "metadata": {"label": "Plain worker"},
                },
            ]

        async def delete_gateway_session_metadata(self, session_key: str) -> None:
            deleted.append(session_key)

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(database=FakeDatabase()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(
        app,
        [
            "sandbox",
            "recreate",
            "--session",
            "agent:main:subagent:sandbox-worker",
            "--force",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["successCount"] == 1
    assert payload["failCount"] == 0
    assert payload["removed"] == ["agent:main:subagent:sandbox-worker"]
    assert payload["failed"] == []
    assert deleted == ["agent:main:subagent:sandbox-worker"]


def test_sandbox_recreate_rejects_multiple_targets() -> None:
    result = runner.invoke(
        app,
        [
            "sandbox",
            "recreate",
            "--all",
            "--session",
            "agent:main:subagent:sandbox-worker",
            "--json",
        ],
    )

    assert result.exit_code == 1
    assert "Please specify only one of: --all, --session, --agent" in result.stderr


def test_sandbox_explain_json_uses_saved_sandbox_metadata(monkeypatch) -> None:
    class FakeDatabase:
        async def list_gateway_session_metadata_rows(self) -> list[dict[str, object]]:
            return [
                {
                    "session_key": "agent:main:subagent:sandbox-worker",
                    "metadata": {
                        "runtime": "codex-app-server",
                        "runtimeId": 7,
                        "runtimeThreadId": "thread-7",
                        "runtimeSessionId": "thread-7",
                        "sandboxed": True,
                        "sandboxMode": "workspace-write",
                        "sandboxPolicy": {"type": "workspaceWrite"},
                        "spawnedWorkspaceDir": r"C:\work\OpenZues",
                    },
                }
            ]

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(database=FakeDatabase()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(
        app,
        [
            "sandbox",
            "explain",
            "--session",
            "agent:main:subagent:sandbox-worker",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["docsUrl"] == "https://docs.openclaw.ai/sandbox"
    assert payload["agentId"] == "main"
    assert payload["sessionKey"] == "agent:main:subagent:sandbox-worker"
    assert payload["mainSessionKey"] == "agent:main:main"
    assert payload["sandbox"]["sessionIsSandboxed"] is True
    assert payload["sandbox"]["mode"] == "workspace-write"
    assert payload["sandbox"]["scope"] == "session"
    assert payload["sandbox"]["workspaceRoot"] == r"C:\work\OpenZues"
    assert payload["sandbox"]["runtime"] == "codex-app-server"
    assert payload["sandbox"]["runtimeId"] == 7
    assert payload["sandbox"]["policy"] == {"type": "workspaceWrite"}
    assert "agents.defaults.sandbox.mode" in payload["fixIt"]


def test_sessions_spawn_json_calls_gateway_method_owner(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeGatewayNodeMethods:
        async def call(
            self,
            method: str,
            params: dict[str, object],
        ) -> dict[str, object]:
            calls.append((method, params))
            return {
                "status": "accepted",
                "runId": "run-42",
                "childSessionKey": "agent:main:acp:thread-42",
                "mode": "run",
                "cleanup": "keep",
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(gateway_node_methods=FakeGatewayNodeMethods()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(
        app,
        [
            "sessions",
            "spawn",
            "--task",
            "Audit parity.",
            "--label",
            "Parity Scout",
            "--runtime",
            "acp",
            "--agent-id",
            "worker",
            "--cwd",
            r"C:\work\OpenZues",
            "--resume-session-id",
            "thread-existing",
            "--stream-to",
            "parent",
            "--mode",
            "run",
            "--thread",
            "--sandbox",
            "inherit",
            "--run-timeout-seconds",
            "45",
            "--cleanup",
            "keep",
            "--expects-completion-message",
            "--requester-session-key",
            "agent:main:main",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "accepted"
    assert payload["runId"] == "run-42"
    assert calls == [
        (
            "sessions.spawn",
            {
                "task": "Audit parity.",
                "label": "Parity Scout",
                "runtime": "acp",
                "agentId": "worker",
                "cwd": r"C:\work\OpenZues",
                "resumeSessionId": "thread-existing",
                "streamTo": "parent",
                "mode": "run",
                "thread": True,
                "sandbox": "inherit",
                "runTimeoutSeconds": 45,
                "cleanup": "keep",
                "expectsCompletionMessage": True,
                "requesterSessionKey": "agent:main:main",
            },
        )
    ]


def test_sessions_wait_human_output_calls_agent_wait(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeGatewayNodeMethods:
        async def call(
            self,
            method: str,
            params: dict[str, object],
        ) -> dict[str, object]:
            calls.append((method, params))
            return {
                "runId": "run-42",
                "status": "ok",
                "startedAt": 1_800_000_000_000,
                "endedAt": 1_800_000_004_000,
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(gateway_node_methods=FakeGatewayNodeMethods()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(
        app,
        [
            "sessions",
            "wait",
            "run-42",
            "--timeout-ms",
            "250",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status: ok" in result.stdout
    assert "run: run-42" in result.stdout
    assert calls == [("agent.wait", {"runId": "run-42", "timeoutMs": 250})]


def test_plugins_list_json_projects_hermes_plugin_inventory(monkeypatch) -> None:
    class FakeHermesPlatform:
        async def get_doctor_view(self) -> dict[str, object]:
            return {
                "profile": {"hermes_source_path": r"C:\Hermes"},
                "warnings": ["Plugin discovery is using source inventory only."],
                "plugins": {
                    "headline": "Plugin and app architecture is mapped",
                    "summary": "OpenZues inventories live Codex plugins and Hermes plugins.",
                    "items": [
                        {
                            "key": "codex_plugins",
                            "label": "Live Codex Plugins",
                            "status": "ready",
                            "summary": "Connected lanes currently expose 2 plugin surface(s).",
                            "capabilities": ["plugin inventory"],
                        },
                        {
                            "key": "hermes_plugin:slack",
                            "label": "Hermes Plugin: Slack",
                            "status": "advisory",
                            "summary": "Hermes source tree includes this plugin family.",
                            "capabilities": ["plugin discovery"],
                        },
                    ],
                },
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(hermes_platform=FakeHermesPlatform()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["plugins", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["workspaceDir"] == r"C:\Hermes"
    assert payload["diagnostics"] == [
        {"level": "warn", "message": "Plugin discovery is using source inventory only."}
    ]
    assert payload["plugins"] == [
        {
            "id": "codex_plugins",
            "name": "Live Codex Plugins",
            "status": "loaded",
            "format": "openzues",
            "source": "live_codex",
            "origin": "runtime",
            "description": "Connected lanes currently expose 2 plugin surface(s).",
            "capabilities": ["plugin inventory"],
            "parityStatus": "ready",
        },
        {
            "id": "hermes_plugin:slack",
            "name": "Hermes Plugin: Slack",
            "status": "disabled",
            "format": "hermes",
            "source": r"C:\Hermes\plugins\slack",
            "origin": "hermes_source",
            "description": "Hermes source tree includes this plugin family.",
            "capabilities": ["plugin discovery"],
            "parityStatus": "advisory",
        },
    ]


def test_plugins_list_enabled_filters_loaded_plugins(monkeypatch) -> None:
    class FakeHermesPlatform:
        async def get_doctor_view(self) -> dict[str, object]:
            return {
                "profile": {"hermes_source_path": None},
                "warnings": [],
                "plugins": {
                    "items": [
                        {
                            "key": "codex_plugins",
                            "label": "Live Codex Plugins",
                            "status": "ready",
                            "summary": "Connected lanes expose plugins.",
                        },
                        {
                            "key": "hermes_plugin:slack",
                            "label": "Hermes Plugin: Slack",
                            "status": "advisory",
                            "summary": "Source-only plugin family.",
                        },
                    ],
                },
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(hermes_platform=FakeHermesPlatform()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["plugins", "list", "--enabled", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [plugin["id"] for plugin in payload["plugins"]] == ["codex_plugins"]


def test_plugins_doctor_human_reports_no_plugin_issues(monkeypatch) -> None:
    class FakeHermesPlatform:
        async def get_doctor_view(self) -> dict[str, object]:
            return {
                "profile": {"hermes_source_path": None},
                "warnings": ["Source-only inventory is advisory."],
                "plugins": {
                    "items": [
                        {
                            "key": "codex_plugins",
                            "label": "Live Codex Plugins",
                            "status": "ready",
                            "summary": "Connected lanes expose plugins.",
                        }
                    ],
                },
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(hermes_platform=FakeHermesPlatform()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["plugins", "doctor"])

    assert result.exit_code == 0, result.stdout
    assert "No plugin issues detected." in result.stdout


def test_plugins_doctor_human_reports_error_plugins(monkeypatch) -> None:
    class FakeHermesPlatform:
        async def get_doctor_view(self) -> dict[str, object]:
            return {
                "profile": {"hermes_source_path": None},
                "warnings": [],
                "plugins": {
                    "items": [
                        {
                            "key": "broken_plugin",
                            "label": "Broken Plugin",
                            "status": "error",
                            "summary": "failed to load plugin: boom",
                        }
                    ],
                },
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(hermes_platform=FakeHermesPlatform()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["plugins", "doctor"])

    assert result.exit_code == 0, result.stdout
    assert "Plugin errors:" in result.stdout
    assert "- broken_plugin: failed to load plugin: boom (openzues)" in result.stdout


def test_plugins_inspect_json_returns_plugin_detail(monkeypatch) -> None:
    class FakeHermesPlatform:
        async def get_doctor_view(self) -> dict[str, object]:
            return {
                "profile": {"hermes_source_path": r"C:\Hermes"},
                "warnings": [],
                "plugins": {
                    "items": [
                        {
                            "key": "hermes_plugin:slack",
                            "label": "Hermes Plugin: Slack",
                            "status": "advisory",
                            "summary": "Hermes source tree includes this plugin family.",
                            "capabilities": ["plugin discovery", "future activation/config"],
                        }
                    ],
                },
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(hermes_platform=FakeHermesPlatform()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["plugins", "inspect", "hermes_plugin:slack", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["plugin"]["id"] == "hermes_plugin:slack"
    assert payload["plugin"]["status"] == "disabled"
    assert payload["shape"] == "hermes-inventory"
    assert payload["capabilityMode"] == "inventory"
    assert payload["capabilities"] == [
        {"kind": "inventory", "ids": ["plugin discovery", "future activation/config"]}
    ]


def test_plugins_info_alias_json_uses_inspect_payload(monkeypatch) -> None:
    class FakeHermesPlatform:
        async def get_doctor_view(self) -> dict[str, object]:
            return {
                "profile": {"hermes_source_path": None},
                "warnings": [],
                "plugins": {
                    "items": [
                        {
                            "key": "codex_plugins",
                            "label": "Live Codex Plugins",
                            "status": "ready",
                            "summary": "Connected lanes expose plugins.",
                        }
                    ],
                },
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(hermes_platform=FakeHermesPlatform()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["plugins", "info", "codex_plugins", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["plugin"]["id"] == "codex_plugins"
    assert payload["shape"] == "openzues-runtime-inventory"


def test_plugins_marketplace_list_json_reads_local_manifest(tmp_path) -> None:
    marketplace_dir = tmp_path / "marketplace"
    manifest_dir = marketplace_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True)
    manifest_path = manifest_dir / "marketplace.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": "Local Marketplace",
                "version": "1.0.0",
                "plugins": [
                    {
                        "name": "frontend-design",
                        "version": "0.2.0",
                        "description": "Design helper.",
                        "source": {"type": "path", "path": "plugins/frontend-design"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["plugins", "marketplace", "list", str(marketplace_dir), "--json"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload == {
        "source": str(manifest_path),
        "name": "Local Marketplace",
        "version": "1.0.0",
        "plugins": [
            {
                "name": "frontend-design",
                "version": "0.2.0",
                "description": "Design helper.",
                "source": {"type": "path", "path": "plugins/frontend-design"},
            }
        ],
    }


def test_plugins_enable_disable_json_persists_openclaw_config(
    tmp_path,
    monkeypatch,
) -> None:
    gateway_config = GatewayConfigService(
        assistant_name="OpenZues",
        assistant_avatar="/static/favicon.svg",
        assistant_agent_id="openzues",
        server_version="9.9.9",
        data_dir=tmp_path,
    )
    gateway_config.set_raw(
        json.dumps(
            {
                "basePath": "",
                "assistantName": "OpenZues",
                "assistantAvatar": "/static/favicon.svg",
                "assistantAgentId": "openzues",
                "serverVersion": "9.9.9",
                "localMediaPreviewRoots": [],
                "embedSandbox": "scripts",
                "allowExternalEmbedUrls": False,
                "plugins": {
                    "allow": ["existing-plugin"],
                    "entries": {
                        "demo-plugin": {
                            "config": {"mode": "test"},
                        }
                    },
                },
                "channels": {
                    "slack": {
                        "botToken": "xoxb-redacted",
                    }
                },
            }
        )
    )

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(gateway_config=gateway_config))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    enable_result = runner.invoke(app, ["plugins", "enable", "demo-plugin", "--json"])

    assert enable_result.exit_code == 0, enable_result.stdout
    enable_payload = json.loads(enable_result.stdout)
    assert enable_payload["ok"] is True
    assert enable_payload["action"] == "enable"
    assert enable_payload["pluginId"] == "demo-plugin"
    assert enable_payload["resolvedPluginId"] == "demo-plugin"
    assert enable_payload["enabled"] is True

    disable_result = runner.invoke(app, ["plugins", "disable", "slack", "--json"])

    assert disable_result.exit_code == 0, disable_result.stdout
    disable_payload = json.loads(disable_result.stdout)
    assert disable_payload["ok"] is True
    assert disable_payload["action"] == "disable"
    assert disable_payload["pluginId"] == "slack"
    assert disable_payload["resolvedPluginId"] == "slack"
    assert disable_payload["enabled"] is False

    stored = json.loads(
        (tmp_path / "settings" / "control-ui-config.json").read_text(encoding="utf-8")
    )
    assert stored["plugins"]["allow"] == ["existing-plugin", "demo-plugin"]
    assert stored["plugins"]["entries"]["demo-plugin"] == {
        "config": {"mode": "test"},
        "enabled": True,
    }
    assert stored["plugins"]["entries"]["slack"]["enabled"] is False
    assert stored["channels"]["slack"] == {
        "botToken": "xoxb-redacted",
        "enabled": False,
    }


def test_models_list_json_calls_gateway_method_owner(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeGatewayNodeMethods:
        async def call(
            self,
            method: str,
            params: dict[str, object],
        ) -> dict[str, object]:
            calls.append((method, params))
            return {
                "models": [
                    {
                        "id": "gpt-5.4",
                        "name": "gpt-5.4",
                        "provider": "openai",
                        "isDefault": True,
                    }
                ]
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(gateway_node_methods=FakeGatewayNodeMethods()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["models", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout) == {
        "models": [
            {
                "id": "gpt-5.4",
                "name": "gpt-5.4",
                "provider": "openai",
                "isDefault": True,
            }
        ]
    }
    assert calls == [("models.list", {})]


def test_models_status_json_projects_default_catalog_state(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeGatewayNodeMethods:
        async def call(
            self,
            method: str,
            params: dict[str, object],
        ) -> dict[str, object]:
            calls.append((method, params))
            return {
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

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(gateway_node_methods=FakeGatewayNodeMethods()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["models", "status", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["defaultModel"] == "gpt-5.4"
    assert payload["resolvedDefault"] == "openai/gpt-5.4"
    assert payload["allowed"] == ["openai/gpt-5.4", "openai/gpt-5.4-mini"]
    assert payload["fallbacks"] == []
    assert payload["auth"]["status"] == "unavailable"
    assert payload["auth"]["probes"] is None
    assert calls == [("models.list", {})]


def test_control_plane_base_url_prefers_lease_metadata(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "control-plane.lock.meta.json").write_text(
        json.dumps({"pid": 42, "host": "127.0.0.1", "port": 8884}),
        encoding="utf-8",
    )
    cli_settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db", port=8765)
    monkeypatch.setattr(
        cli_module,
        "_control_plane_metadata_endpoint_is_reachable",
        lambda host, port: True,
    )

    assert cli_module._control_plane_base_url(cli_settings) == "http://127.0.0.1:8884"


def test_control_plane_base_url_ignores_stale_local_lease_metadata(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "control-plane.lock.meta.json").write_text(
        json.dumps({"pid": 42, "host": "127.0.0.1", "port": 8884}),
        encoding="utf-8",
    )
    cli_settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db", port=8765)
    monkeypatch.setattr(
        cli_module,
        "_control_plane_metadata_endpoint_is_reachable",
        lambda host, port: False,
    )

    assert cli_module._control_plane_base_url(cli_settings) == "http://127.0.0.1:8765"


def test_serve_sets_openzues_host_and_port_env(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(app_target: str, **kwargs: object) -> None:
        captured["app_target"] = app_target
        captured["kwargs"] = kwargs

    monkeypatch.delenv("OPENZUES_HOST", raising=False)
    monkeypatch.delenv("OPENZUES_PORT", raising=False)
    monkeypatch.setattr(cli_module.uvicorn, "run", fake_run)

    cli_module.serve(host="0.0.0.0", port=9999, reload=False)

    assert os.environ["OPENZUES_HOST"] == "0.0.0.0"
    assert os.environ["OPENZUES_PORT"] == "9999"
    assert cli_module.settings.host == "0.0.0.0"
    assert cli_module.settings.port == 9999
    assert app_module.settings.host == "0.0.0.0"
    assert app_module.settings.port == 9999
    assert captured["app_target"] == "openzues.app:create_app"
    assert captured["kwargs"] == {
        "host": "0.0.0.0",
        "port": 9999,
        "reload": False,
        "factory": True,
    }


def test_emit_gateway_capability_surfaces_conversation_reuse_summary(capsys) -> None:
    _emit_gateway_capability(
        {
            "headline": "Gateway capability is operator-ready",
            "summary": "Control plane is aligned.",
            "connected_lane_health": {"summary": "1/1 lane(s) connected."},
            "inventory": {"summary": "Tracked inventory is healthy.", "memory_summary": "Idle."},
            "approval_posture": {"summary": "No approvals waiting."},
            "launch_policy": {
                "summary": "Verification on. Next launch will reuse thread thread_saved.",
                "launch_route": {
                    "conversation_target": {
                        "summary": "slack · account workspace-bot · channel deploy-room"
                    },
                    "conversation_reuse": {
                        "summary": (
                            "Next launch will reuse thread thread_saved from mission "
                            "'Parity'."
                        )
                    }
                },
            },
            "diagnostics": {"summary": "Diagnostics are clean."},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "conversation target: slack" in output
    assert "conversation reuse: Next launch will reuse thread thread_saved" in output


def test_emit_gateway_capability_surfaces_callable_method_inventory(capsys) -> None:
    _emit_gateway_capability(
        {
            "headline": "Gateway capability is operator-ready",
            "summary": "Control plane is aligned.",
            "connected_lane_health": {"summary": "1/1 lane(s) connected."},
            "inventory": {
                "summary": "Tracked inventory is healthy.",
                "memory_summary": "Idle.",
                "method_catalog": {
                    "summary": (
                        "3 callable method(s) are visible across 1 MCP server catalog(s) on "
                        "1 connected lane(s)."
                    ),
                    "tool_count": 3,
                    "server_count": 1,
                    "lane_count": 1,
                    "tools": [
                        "github_create_pull_request",
                        "github_search",
                        "github_search_prs",
                    ],
                    "servers": ["GitHub MCP Server"],
                },
            },
            "approval_posture": {"summary": "No approvals waiting."},
            "launch_policy": {"summary": "Saved local launch policy."},
            "diagnostics": {"summary": "Diagnostics are clean."},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "method catalog: 3 callable method(s) are visible" in output
    assert "method tools: github_create_pull_request, github_search, github_search_prs" in output


def test_emit_gateway_capability_surfaces_reserved_admin_methods(capsys) -> None:
    _emit_gateway_capability(
        {
            "headline": "Gateway capability is operator-ready",
            "summary": "Control plane is aligned.",
            "connected_lane_health": {"summary": "1/1 lane(s) connected."},
            "inventory": {
                "summary": "Tracked inventory is healthy.",
                "memory_summary": "Idle.",
                "method_catalog": {
                    "summary": (
                        "10 callable method(s) are visible across 1 MCP server catalog(s) on "
                        "1 connected lane(s). Scope coverage: operator.admin 3, "
                        "operator.read 1, operator.write 1, operator.approvals 1, "
                        "operator.pairing 1, node.role 2. 2 reserved admin method(s) require "
                        "operator.admin."
                    ),
                    "tool_count": 10,
                    "server_count": 1,
                    "lane_count": 1,
                    "classified_method_count": 9,
                    "reserved_admin_method_count": 2,
                    "reserved_admin_scope": "operator.admin",
                    "tools": [
                        "connect",
                        "config.reload",
                        "exec.approval.list",
                        "github_search",
                        "node.pending.drain",
                        "node.pair.request",
                        "send",
                        "skills.bins",
                        "status",
                        "wizard.bootstrap",
                    ],
                    "servers": ["Control Plane MCP"],
                    "reserved_admin_methods": [
                        "config.reload",
                        "wizard.bootstrap",
                    ],
                    "scopes": [
                        {
                            "scope": "operator.admin",
                            "method_count": 3,
                            "methods": ["config.reload", "connect", "wizard.bootstrap"],
                        },
                        {
                            "scope": "operator.read",
                            "method_count": 1,
                            "methods": ["status"],
                        },
                        {
                            "scope": "operator.write",
                            "method_count": 1,
                            "methods": ["send"],
                        },
                        {
                            "scope": "operator.approvals",
                            "method_count": 1,
                            "methods": ["exec.approval.list"],
                        },
                        {
                            "scope": "operator.pairing",
                            "method_count": 1,
                            "methods": ["node.pair.request"],
                        },
                        {
                            "scope": "node.role",
                            "method_count": 2,
                            "methods": ["node.pending.drain", "skills.bins"],
                        },
                    ],
                },
            },
            "approval_posture": {"summary": "No approvals waiting."},
            "launch_policy": {"summary": "Saved local launch policy."},
            "diagnostics": {"summary": "Diagnostics are clean."},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "reserved admin methods: config.reload, wizard.bootstrap" in output
    assert (
        "method scopes: operator.admin (3), operator.read (1), operator.write (1), "
        "operator.approvals (1), operator.pairing (1), node.role (2)"
    ) in output


def test_emit_gateway_capability_surfaces_staged_local_method_registry_summary(capsys) -> None:
    registry_methods = list(list_known_gateway_methods())

    _emit_gateway_capability(
        {
            "headline": "Gateway method registry is staged",
            "summary": "Built-in registry is staged locally.",
            "connected_lane_health": {"summary": "0/0 lane(s) connected."},
            "inventory": {
                "summary": "Tracked inventory is healthy.",
                "memory_summary": "Idle.",
                "method_catalog": {
                    "summary": (
                        "217 built-in gateway method(s) are registered locally while "
                        "lane-published MCP catalogs are offline. Scope coverage: "
                        "operator.admin 39, operator.read 75, operator.write 75, "
                        "operator.approvals 9, operator.pairing 12, node.role 7. "
                        "14 reserved admin method(s) require operator.admin."
                    ),
                    "tool_count": len(registry_methods),
                    "server_count": 0,
                    "lane_count": 0,
                    "classified_method_count": len(registry_methods),
                    "reserved_admin_method_count": 14,
                    "reserved_admin_scope": "operator.admin",
                    "tools": registry_methods,
                    "servers": [],
                    "reserved_admin_methods": [
                        "config.apply",
                        "config.openFile",
                        "config.patch",
                        "config.schema",
                        "config.set",
                        "exec.approvals.get",
                        "exec.approvals.node.get",
                        "exec.approvals.node.set",
                        "exec.approvals.set",
                        "update.run",
                        "wizard.cancel",
                        "wizard.next",
                        "wizard.start",
                        "wizard.status",
                    ],
                    "scopes": [
                        {"scope": "operator.admin", "method_count": 39},
                        {"scope": "operator.read", "method_count": 75},
                        {"scope": "operator.write", "method_count": 75},
                        {"scope": "operator.approvals", "method_count": 9},
                        {"scope": "operator.pairing", "method_count": 12},
                        {"scope": "node.role", "method_count": 7},
                    ],
                },
            },
            "approval_posture": {"summary": "No approvals waiting."},
            "launch_policy": {"summary": "Saved local launch policy."},
            "diagnostics": {"summary": "Diagnostics are clean."},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert (
        "method catalog: 217 built-in gateway method(s) are registered locally while "
        "lane-published MCP catalogs are offline."
    ) in output
    assert (
        "method tools: agent, agent.identity.get, agent.wait, agents.create, "
        "agents.delete, agents.files.get"
    ) in output
    assert (
        "reserved admin methods: config.apply, config.openFile, config.patch, "
        "config.schema, config.set, exec.approvals.get"
    ) in output
    assert (
        "method scopes: operator.admin (39), operator.read (75), operator.write (75), "
        "operator.approvals (9), operator.pairing (12), node.role (7)"
    ) in output


def test_emit_gateway_capability_surfaces_browser_runtime_contract(capsys) -> None:
    _emit_gateway_capability(
        {
            "headline": "Gateway capability is operator-ready",
            "summary": "Control plane is aligned.",
            "connected_lane_health": {"summary": "1/1 lane(s) connected."},
            "inventory": {
                "summary": "Tracked inventory is healthy.",
                "memory_summary": "Idle.",
                "browser_runtime": {
                    "summary": (
                        "1 connected lane(s) publish 1 browser method(s) and 1 browser "
                        "service(s). Plugin signals: browser. MCP servers: browser-runtime."
                    ),
                    "status": "ready",
                    "lane_count": 1,
                    "connected_lane_count": 1,
                    "ready_lane_count": 1,
                    "method_count": 1,
                    "service_count": 1,
                    "methods": ["browser.request"],
                    "services": ["browser-control"],
                    "recommended_action": (
                        "Use the live browser lane when parity work needs browser-led "
                        "verification or browser-control execution."
                    ),
                },
            },
            "approval_posture": {"summary": "No approvals waiting."},
            "launch_policy": {"summary": "Saved local launch policy."},
            "diagnostics": {"summary": "Diagnostics are clean."},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "browser runtime: 1 connected lane(s) publish 1 browser method(s)" in output
    assert "browser methods: browser.request" in output
    assert "browser services: browser-control" in output
    assert "browser action: Use the live browser lane" in output


def test_emit_gateway_bootstrap_surfaces_runtime_browser_contract(capsys) -> None:
    _emit_gateway_bootstrap(
        {
            "headline": "Gateway bootstrap is launch-ready",
            "summary": "Saved launch lane is aligned.",
            "launch_defaults_summary": "Verification on, built-in agents on, approvals paused.",
            "launch_route": {"summary": "Saved lane will be reused."},
            "runtime_inventory": {
                "summary": "1 plugin, 1 service, and 1 browser method are visible on the lane.",
                "browser_runtime": {
                    "summary": (
                        "Browser Lane publishes 1 browser method(s) and 1 browser service(s) "
                        "for the saved launch lane."
                    ),
                    "methods": ["browser.request"],
                    "services": ["browser-control"],
                    "recommended_action": (
                        "Use this saved launch lane for browser-led verification and "
                        "browser-control work."
                    ),
                },
                "method_catalog": {
                    "summary": "1 plugin-published gateway method is resolved on the lane."
                },
            },
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "launch defaults: Verification on, built-in agents on, approvals paused." in output
    assert "launch route: Saved lane will be reused." in output
    assert "runtime inventory: 1 plugin, 1 service, and 1 browser method are visible" in output
    assert "browser runtime: Browser Lane publishes 1 browser method(s)" in output
    assert "browser methods: browser.request" in output
    assert "browser services: browser-control" in output
    assert "browser action: Use this saved launch lane" in output
    assert "method catalog: 1 plugin-published gateway method is resolved on the lane." in output


def test_browser_status_json_surfaces_saved_launch_and_local_browser(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Browser Loop")
    monkeypatch.setattr(
        "openzues.services.browser_posture.find_agent_browser_command",
        lambda: "agent-browser.cmd",
    )

    result = runner.invoke(app, ["browser", "status", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["control_plane_url"].startswith("http://")
    assert payload["local_agent_browser"]["available"] is True
    assert payload["local_agent_browser"]["command"] == "agent-browser.cmd"
    assert payload["saved_launch_browser_runtime"] is not None
    assert payload["saved_launch"]["status"] in {"ready", "warn", "info", "staged"}


def test_browser_doctor_json_surfaces_posture_without_verify(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Browser Doctor")
    monkeypatch.setattr(
        "openzues.services.browser_posture.find_agent_browser_command",
        lambda: "agent-browser.cmd",
    )

    result = runner.invoke(app, ["browser", "doctor", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] in {"ready", "warn", "info"}
    assert payload["control_plane_url"].startswith("http://")
    assert payload["local_agent_browser"]["available"] is True
    assert payload.get("verification") is None


def test_browser_doctor_verify_json_embeds_verification_result(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(
        "openzues.cli._control_plane_base_url",
        lambda _settings: "http://watch.test",
    )

    async def fake_build_browser_status_payload(_services) -> dict[str, object]:
        return {
            "status": "ready",
            "headline": "Browser control is operator-ready",
            "summary": "Local agent-browser and the lane browser runtime are aligned.",
            "control_plane_url": "http://watch.test",
            "local_agent_browser": {
                "available": True,
                "command": "agent-browser.cmd",
                "summary": "agent-browser is available at agent-browser.cmd.",
            },
            "recommended_action": "Use the connected browser lane for live verification.",
        }

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "openzues-browser"
        return {
            "ok": True,
            "status": "ready",
            "summary": "url http://watch.test, content visible, no overlay, 0 page error(s).",
            "url": browser_url,
            "title": "OpenZues",
        }

    monkeypatch.setattr(
        "openzues.cli._build_browser_status_payload",
        fake_build_browser_status_payload,
    )
    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(app, ["browser", "doctor", "--verify", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["verification"]["ok"] is True
    assert payload["verification"]["status"] == "ready"
    assert payload["verification"]["url"] == "http://watch.test"
    assert payload["verification"]["session"] == "openzues-browser"


def test_browser_doctor_verify_exits_nonzero_when_verify_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(
        "openzues.cli._control_plane_base_url",
        lambda _settings: "http://watch.test",
    )

    async def fake_build_browser_status_payload(_services) -> dict[str, object]:
        return {
            "status": "ready",
            "headline": "Browser control is operator-ready",
            "summary": "Local agent-browser and the lane browser runtime are aligned.",
            "control_plane_url": "http://watch.test",
            "local_agent_browser": {
                "available": True,
                "command": "agent-browser.cmd",
                "summary": "agent-browser is available at agent-browser.cmd.",
            },
            "recommended_action": "Use the connected browser lane for live verification.",
        }

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "openzues-browser"
        raise RuntimeError("browser verification timed out after 45s.")

    monkeypatch.setattr(
        "openzues.cli._build_browser_status_payload",
        fake_build_browser_status_payload,
    )
    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(app, ["browser", "doctor", "--verify", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "warn"
    assert payload["verification"]["ok"] is False
    assert payload["verification"]["summary"] == "browser verification timed out after 45s."
    assert payload["verification"]["url"] == "http://watch.test"


def test_browser_verify_json_defaults_to_control_plane_url(monkeypatch) -> None:
    monkeypatch.setattr(
        "openzues.cli._control_plane_base_url",
        lambda _settings: "http://watch.test",
    )

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "openzues-browser"
        return {
            "ok": True,
            "status": "ready",
            "summary": "url http://watch.test, content visible, no overlay, 0 page error(s).",
            "url": browser_url,
            "title": "OpenZues",
        }

    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(app, ["browser", "verify", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["ok"] is True
    assert payload["session"] == "openzues-browser"
    assert payload["url"] == "http://watch.test"


def test_browser_verify_exits_nonzero_when_guarded_verify_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        "openzues.cli._control_plane_base_url",
        lambda _settings: "http://watch.test",
    )

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "openzues-browser"
        raise RuntimeError("browser verification timed out after 45s.")

    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(app, ["browser", "verify", "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "warn"
    assert payload["ok"] is False
    assert payload["summary"] == "browser verification timed out after 45s."
    assert payload["url"] == "http://watch.test"


def test_browser_open_json_uses_agent_browser_session_and_target(monkeypatch) -> None:
    calls: list[tuple[list[str], str, float, bool]] = []

    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        calls.append((args, session_name, timeout_seconds, allow_failure))
        return ""

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    result = runner.invoke(app, ["browser", "open", "https://example.com", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["url"] == "https://example.com"
    assert payload["session"] == "openzues-browser"
    assert calls == [(["open", "https://example.com"], "openzues-browser", 15.0, False)]


def test_browser_snapshot_json_summarizes_snapshot_output(monkeypatch) -> None:
    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        assert args == ["snapshot", "-i"]
        assert session_name == "openzues-browser"
        assert timeout_seconds == 6.0
        assert allow_failure is False
        return "\n".join(
            [
                '[document] "OpenZues"',
                '- heading "Parity Control"',
                '- button "Continue parity work"',
            ]
        )

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    result = runner.invoke(app, ["browser", "snapshot", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["session"] == "openzues-browser"
    assert "Parity Control" in payload["snapshot_summary"]


def test_browser_console_json_returns_lines(monkeypatch) -> None:
    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        assert args == ["console"]
        assert session_name == "openzues-browser"
        assert timeout_seconds == 5.0
        assert allow_failure is False
        return "\n".join(["console: ready", "console: parity pulse"])

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    result = runner.invoke(app, ["browser", "console", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["line_count"] == 2
    assert payload["lines"] == ["console: ready", "console: parity pulse"]


def test_browser_errors_json_returns_lines(monkeypatch) -> None:
    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        assert args == ["errors"]
        assert session_name == "openzues-browser"
        assert timeout_seconds == 5.0
        assert allow_failure is False
        return "TypeError: parity probe failed"

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    result = runner.invoke(app, ["browser", "errors", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ready"
    assert payload["line_count"] == 1
    assert payload["lines"] == ["TypeError: parity probe failed"]


def test_continue_plan_uses_gateway_aware_repair_first_posture(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["continue", "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "plan"
    assert payload["action_kind"] == "observe"
    assert payload["executed"] is False
    assert "Gateway Doctor says" in payload["reply"]


def test_queue_plan_uses_attention_queue_planner(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Queue Loop")

    result = runner.invoke(app, ["queue", "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "plan"
    assert payload["executed"] is False
    assert payload["action_kind"] == "observe"
    assert payload["status"] == "escalated"
    assert payload["signal_id"] is not None
    assert "Gateway Doctor says" in payload["reply"]
    assert payload["mission_payload"] is None


def test_queue_plan_can_target_selected_signal_id(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Queue Loop")

    baseline = runner.invoke(app, ["queue", "--plan", "--json"])
    assert baseline.exit_code == 0, baseline.stdout
    signal_id = json.loads(baseline.stdout)["signal_id"]

    result = runner.invoke(app, ["queue", "--signal-id", signal_id, "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "plan"
    assert payload["executed"] is False
    assert payload["signal_id"] == signal_id
    assert "Gateway Doctor says" in payload["reply"]


def test_queue_execute_runs_one_bounded_attention_move(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Queue Loop")

    result = runner.invoke(app, ["queue", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "executed"
    assert payload["executed"] is True
    assert payload["action_kind"] == "observe"
    assert payload["status"] == "escalated"
    assert payload["signal_id"] is not None
    assert "Gateway Doctor says" in payload["reply"]


def test_queue_execute_can_target_selected_signal_id(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Queue Loop")

    baseline = runner.invoke(app, ["queue", "--plan", "--json"])
    assert baseline.exit_code == 0, baseline.stdout
    signal_id = json.loads(baseline.stdout)["signal_id"]

    result = runner.invoke(app, ["queue", "--signal-id", signal_id, "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "executed"
    assert payload["executed"] is True
    assert payload["signal_id"] == signal_id
    assert "Gateway Doctor says" in payload["reply"]


def test_queue_rejects_unknown_signal_id(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Queue Loop")

    result = runner.invoke(app, ["queue", "--signal-id", "missing-signal", "--plan"])

    assert result.exit_code == 1
    assert "Attention-queue signal 'missing-signal' is not available right now." in result.stderr
    assert "Available ids:" in result.stderr


def test_gateway_doctor_human_output_summarizes_sections(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    result = runner.invoke(app, ["gateway", "doctor"])

    assert result.exit_code == 0, result.stdout
    assert "lane health:" in result.stdout
    assert "inventory:" in result.stdout
    assert "memory:" in result.stdout
    assert "approvals:" in result.stdout
    assert "launch policy:" in result.stdout
    assert "diagnostics:" in result.stdout


def test_health_json_surfaces_gateway_readiness_snapshot(monkeypatch) -> None:
    calls: list[tuple[str, str, float]] = []

    monkeypatch.setattr(
        cli_module,
        "_control_plane_base_url",
        lambda _settings: "http://gateway.test",
    )

    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        timeout_seconds: float,
        **_kwargs: object,
    ) -> dict[str, object]:
        calls.append((base_url, path, timeout_seconds))
        if path == "/api/health":
            return {
                "status": "ok",
                "control_plane": "leader",
                "owner_pid": 1234,
                "lock_path": r"C:\OpenZues\control-plane.lock",
                "runtime_update": {"status": "idle"},
            }
        if path == "/readyz":
            return {"ready": True, "failing": [], "uptimeMs": 123}
        raise AssertionError(path)

    monkeypatch.setattr(cli_module, "_watch_api_json", fake_watch_api_json)

    result = runner.invoke(app, ["health", "--json", "--timeout-ms", "2500"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "status": "ok",
        "controlPlane": "leader",
        "ownerPid": 1234,
        "lockPath": r"C:\OpenZues\control-plane.lock",
        "runtimeUpdate": {"status": "idle"},
        "readiness": {"ready": True, "failing": [], "uptimeMs": 123},
    }
    assert calls == [
        ("http://gateway.test", "/api/health", 2.5),
        ("http://gateway.test", "/readyz", 2.5),
    ]


def test_status_json_reuses_gateway_contract_and_surfaces_queue_plan(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "openzues.services.browser_posture.find_agent_browser_command",
        lambda: "agent-browser.cmd",
    )

    result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        api_payload = client.get("/api/gateway/capability").json()

    cli_gateway = {
        key: value for key, value in payload["gateway_capability"].items() if key != "checked_at"
    }
    api_payload = {key: value for key, value in api_payload.items() if key != "checked_at"}
    if "diagnostics" in cli_gateway and "diagnostics" in api_payload:
        for key in ("ok_count", "warn_count", "fail_count"):
            cli_gateway["diagnostics"].pop(key, None)
            api_payload["diagnostics"].pop(key, None)

    assert payload["headline"]
    assert payload["status_plan"]["action_kind"] == "observe"
    assert payload["browser_posture"]["local_agent_browser"]["available"] is True
    assert payload["browser_posture"]["saved_launch_browser_runtime"] is not None
    assert payload["queue_plan"] is not None
    assert payload["queue_plan"]["signal_id"] is not None
    assert "Gateway Doctor says" in payload["queue_plan"]["reply"]
    assert cli_gateway == api_payload


def test_status_json_prefers_live_status_payload_when_available(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        status_payload = client.get("/api/status").json()

    status_payload["brief"]["headline"] = "Live dashboard headline"
    status_payload["summary"] = "Live dashboard summary"
    status_payload["instance_summary"]["connected_count"] = 1

    async def fake_live_status(_settings: Settings) -> dict[str, object]:
        return status_payload

    monkeypatch.setattr(cli_module, "_try_live_status_payload", fake_live_status)

    result = runner.invoke(app, ["status", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["brief"]["headline"] == "Live dashboard headline"
    assert payload["summary"] == "Live dashboard summary"
    assert payload["instance_summary"]["connected_count"] == 1


def test_status_json_breadth_flags_add_runtime_sections_with_timeout(
    tmp_path, monkeypatch
) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    health_calls: list[int] = []

    async def fake_live_status(_settings: Settings) -> dict[str, object]:
        return {"headline": "Live dashboard headline", "summary": "Live dashboard summary"}

    async def fake_live_health(
        _settings: Settings,
        *,
        timeout_ms: int,
    ) -> dict[str, object]:
        health_calls.append(timeout_ms)
        return {
            "ok": True,
            "status": "ok",
            "controlPlane": "leader",
            "readiness": {"ready": True, "failing": []},
        }

    monkeypatch.setattr(cli_module, "_try_live_status_payload", fake_live_status)
    monkeypatch.setattr(cli_module, "_build_live_health_payload", fake_live_health)

    result = runner.invoke(
        app,
        [
            "status",
            "--json",
            "--deep",
            "--usage",
            "--all",
            "--timeout",
            "5000",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert health_calls == [5000]
    assert payload["headline"] == "Live dashboard headline"
    assert payload["health"]["status"] == "ok"
    assert payload["lastHeartbeat"] is None
    assert payload["usage"]["status"] == "unavailable"
    assert payload["usage"]["timeoutMs"] == 5000
    assert payload["securityAudit"]["status"] == "unavailable"


def test_status_all_human_output_renders_pasteable_diagnosis(
    tmp_path, monkeypatch
) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    async def fake_live_status(_settings: Settings) -> dict[str, object]:
        return {
            "headline": "Live dashboard headline",
            "summary": "Live dashboard summary",
            "mission_summary": {"active_count": 1, "blocked_count": 0},
            "instance_summary": {"connected_count": 1, "total_count": 2},
            "gateway_capability": {"summary": "Gateway route is configured."},
        }

    monkeypatch.setattr(cli_module, "_try_live_status_payload", fake_live_status)

    result = runner.invoke(app, ["status", "--all", "--timeout", "5000"])

    assert result.exit_code == 0, result.stdout
    assert "OpenClaw status --all" in result.stdout
    assert "Overview" in result.stdout
    assert "Channels" in result.stdout
    assert "Agents" in result.stdout
    assert "Diagnosis (read-only)" in result.stdout
    assert "Live dashboard headline" in result.stdout
    assert "timeout: 5000 ms" in result.stdout


def test_routes_list_json_surfaces_saved_notification_routes(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/completed"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )

    assert response.status_code == 200, response.text

    result = runner.invoke(app, ["routes", "list", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["name"] == "Deploy Room"
    assert payload[0]["events"] == ["mission/completed"]
    assert payload[0]["conversation_target"]["channel"] == "slack"
    assert payload[0]["conversation_target"]["peer_id"] == "deploy-room"


def test_routes_create_command_productizes_native_provider_routes(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "routes",
            "create",
            "--name",
            "WhatsApp Native Gateway",
            "--kind",
            "whatsapp",
            "--target",
            "https://graph.facebook.com/v20.0/123456789",
            "--conversation-channel",
            "whatsapp",
            "--conversation-account",
            "wa-business",
            "--conversation-peer-kind",
            "direct",
            "--conversation-peer-id",
            "direct:+15551234567",
            "--secret-token",
            "wa-access-token",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["name"] == "WhatsApp Native Gateway"
    assert payload["kind"] == "whatsapp"
    assert payload["target"] == "https://graph.facebook.com/v20.0/123456789"
    assert payload["events"] == ["gateway/send", "gateway/poll"]
    conversation_target = payload["conversation_target"]
    assert conversation_target["channel"] == "whatsapp"
    assert conversation_target["account_id"] == "wa-business"
    assert conversation_target["peer_kind"] == "direct"
    assert conversation_target["peer_id"] == "direct:+15551234567"
    assert "direct:+15551234567" in conversation_target["summary"]
    assert payload["has_secret"] is True
    assert payload["secret_preview"] == "****oken"

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    database = Database(settings.db_path)
    asyncio.run(database.initialize())
    routes = asyncio.run(database.list_notification_routes())
    assert len(routes) == 1
    assert routes[0]["kind"] == "whatsapp"
    assert routes[0]["events"] == ["gateway/send", "gateway/poll"]


def test_routes_send_json_calls_native_direct_send_runtime(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeOpsMesh:
        async def send_direct_channel_message(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {
                "ok": True,
                "sessionKey": "agent:main:channel:slack:account:workspace:peer:channel:C123",
                "deliveryId": 41,
                "messageId": "slack-41",
                "channel": "slack",
                "transport": {"transport": "slack", "messageId": "slack-41"},
                "provider": "slack",
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(ops_mesh=FakeOpsMesh()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(
        app,
        [
            "routes",
            "send",
            "--channel",
            "slack",
            "--to",
            "channel:C123",
            "--message",
            "Deploy is green.",
            "--account",
            "workspace",
            "--thread",
            "1700.2",
            "--reply-to",
            "1699.1",
            "--media-url",
            "https://example.invalid/report.png",
            "--gif-playback",
            "--silent",
            "--force-document",
            "--agent-id",
            "main",
            "--session-key",
            "agent:main:main",
            "--idempotency-key",
            "cli-send-1",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["deliveryId"] == 41
    assert payload["messageId"] == "slack-41"
    assert payload["transport"]["transport"] == "slack"
    assert calls == [
        {
            "channel": "slack",
            "to": "channel:C123",
            "message": "Deploy is green.",
            "media_urls": ["https://example.invalid/report.png"],
            "gif_playback": True,
            "reply_to_id": "1699.1",
            "silent": True,
            "force_document": True,
            "account_id": "workspace",
            "agent_id": "main",
            "thread_id": "1700.2",
            "session_key": "agent:main:main",
            "idempotency_key": "cli-send-1",
        }
    ]


def test_routes_poll_human_output_calls_native_direct_poll_runtime(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeOpsMesh:
        async def send_direct_channel_poll(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {
                "ok": True,
                "sessionKey": "agent:main:channel:telegram:account:ops:peer:channel:deploy",
                "deliveryId": 42,
                "messageId": "telegram-poll-42",
                "pollId": "poll-42",
                "channel": "telegram",
                "transport": {"transport": "telegram", "messageId": "telegram-poll-42"},
            }

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(ops_mesh=FakeOpsMesh()))

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(
        app,
        [
            "routes",
            "poll",
            "--channel",
            "telegram",
            "--to",
            "channel:deploy",
            "--question",
            "Ship the release?",
            "--option",
            "yes",
            "--option",
            "no",
            "--max-selections",
            "1",
            "--duration-seconds",
            "3600",
            "--silent",
            "--anonymous",
            "--account",
            "ops",
            "--thread",
            "123",
            "--idempotency-key",
            "cli-poll-1",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "ok: True" in result.stdout
    assert "delivery: 42" in result.stdout
    assert "message: telegram-poll-42" in result.stdout
    assert "poll: poll-42" in result.stdout
    assert calls == [
        {
            "channel": "telegram",
            "to": "channel:deploy",
            "question": "Ship the release?",
            "options": ["yes", "no"],
            "max_selections": 1,
            "duration_seconds": 3600,
            "duration_hours": None,
            "silent": True,
            "is_anonymous": True,
            "account_id": "ops",
            "thread_id": "123",
            "idempotency_key": "cli-poll-1",
        }
    ]


def test_routes_deliveries_json_surfaces_saved_outbound_deliveries(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, event_type, event, secret_token

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["ops/inbox/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]
        test_response = client.post(f"/api/notification-routes/{route_id}/test")

    assert test_response.status_code == 200, test_response.text

    result = runner.invoke(app, ["routes", "deliveries", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["route_name"] == "Deploy Room"
    assert payload[0]["delivery_state"] == "delivered"
    assert payload[0]["event_type"] == "ops/inbox/test"
    assert payload[0]["conversation_target"]["channel"] == "slack"
    assert payload[0]["conversation_target"]["peer_id"] == "deploy-room"
    assert payload[0]["route_scope"]["route_match"] == "test"
    assert payload[0]["event_payload"]["routeConversationTarget"]["peer_id"] == "deploy-room"
    assert payload[0]["event_payload"]["summary"] == "OpenZues test delivery ping."


def test_routes_deliveries_reports_saved_direct_transport_identity(monkeypatch) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "cli-routes-deliveries-direct-transport"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)):
        pass

    database = Database(settings.db_path)
    asyncio.run(
        database.create_outbound_delivery(
            route_id=None,
            route_name="Announce delivery for CLI replay",
            route_kind="announce",
            route_target="telegram account coordinator channel deploy-room",
            event_type="cron/failure",
            session_key=(
                "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
                "peer:channel:deploy-room"
            ),
            conversation_target={
                "channel": "telegram",
                "account_id": "coordinator",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
                "summary": "telegram account coordinator channel deploy-room",
            },
            route_scope={
                "route_name": "Announce delivery for CLI replay",
                "route_kind": "announce",
                "route_target": "telegram account coordinator channel deploy-room",
                "route_match": "explicitTarget",
            },
            event_payload={
                "message": 'Cron job "CLI replay" failed: lane timed out',
            },
            message_summary='Cron job "CLI replay" failed: lane timed out',
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
            last_error="temporary delivery timeout",
        )
    )

    result = runner.invoke(app, ["routes", "deliveries"])

    assert result.exit_code == 0, result.stdout
    assert "route: Announce delivery for CLI replay [announce]" in result.stdout
    assert "target: telegram account coordinator channel deploy-room" in result.stdout
    assert (
        "session: launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
        in result.stdout
    )


def test_routes_replay_json_reports_saved_announce_transport_identity(
    monkeypatch,
) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "cli-routes-replay-announce-identity"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)):
        pass

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=None,
            route_name="Announce delivery for CLI replay",
            route_kind="announce",
            route_target="telegram account coordinator channel deploy-room",
            event_type="cron/failure",
            session_key=(
                "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
                "peer:channel:deploy-room"
            ),
            conversation_target={
                "channel": "telegram",
                "account_id": "coordinator",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
                "summary": "telegram account coordinator channel deploy-room",
            },
            route_scope={
                "route_name": "Announce delivery for CLI replay",
                "route_kind": "announce",
                "route_target": "telegram account coordinator channel deploy-room",
                "route_match": "explicitTarget",
            },
            event_payload={
                "message": 'Cron job "CLI replay" failed: lane timed out',
            },
            message_summary='Cron job "CLI replay" failed: lane timed out',
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
            last_error="temporary delivery timeout",
        )
    )

    result = runner.invoke(app, ["routes", "replay", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["attempted_count"] == 1
    assert payload["replayed_count"] == 1
    assert payload["deliveries"][0]["delivery_id"] == delivery_id
    assert payload["deliveries"][0]["route"]["kind"] == "announce"
    assert (
        payload["deliveries"][0]["route"]["target"]
        == "telegram account coordinator channel deploy-room"
    )
    assert payload["deliveries"][0]["route"]["enabled"] is True
    assert payload["deliveries"][0]["route"]["conversation_target"]["channel"] == "telegram"
    assert payload["deliveries"][0]["route"]["conversation_target"]["account_id"] == "coordinator"
    assert payload["deliveries"][0]["delivery"]["delivery_state"] == "delivered"


def test_routes_replay_reports_saved_announce_transport_identity(monkeypatch) -> None:
    tmp_path = Path.cwd() / ".tmp-pytest-local" / "cli-routes-replay-announce-plain"
    shutil.rmtree(tmp_path, ignore_errors=True)
    tmp_path.mkdir(parents=True, exist_ok=True)
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)):
        pass

    database = Database(settings.db_path)
    asyncio.run(
        database.create_outbound_delivery(
            route_id=None,
            route_name="Announce delivery for CLI replay",
            route_kind="announce",
            route_target="telegram account coordinator channel deploy-room",
            event_type="cron/failure",
            session_key=(
                "launch:mode:workspace_affinity:channel:telegram:account:coordinator:"
                "peer:channel:deploy-room"
            ),
            conversation_target={
                "channel": "telegram",
                "account_id": "coordinator",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
                "summary": "telegram account coordinator channel deploy-room",
            },
            route_scope={
                "route_name": "Announce delivery for CLI replay",
                "route_kind": "announce",
                "route_target": "telegram account coordinator channel deploy-room",
                "route_match": "explicitTarget",
            },
            event_payload={
                "message": 'Cron job "CLI replay" failed: lane timed out',
            },
            message_summary='Cron job "CLI replay" failed: lane timed out',
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
            last_error="temporary delivery timeout",
        )
    )

    result = runner.invoke(app, ["routes", "replay"])

    assert result.exit_code == 0, result.stdout
    assert "[ok] cron/failure -> Announce delivery for CLI replay [announce]" in result.stdout
    assert "target: telegram account coordinator channel deploy-room" in result.stdout


def test_routes_replay_json_retries_saved_failed_delivery(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-replay",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission resumed on the routed channel.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission resumed on the routed channel.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )

    result = runner.invoke(app, ["routes", "replay", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["attempted_count"] == 1
    assert payload["replayed_count"] == 1
    assert payload["failed_count"] == 0
    assert payload["deferred_count"] == 0
    assert payload["skipped_max_retries_count"] == 0
    assert len(deliveries) == 1
    assert deliveries[0][0] == "mission/updated"
    assert payload["deliveries"][0]["delivery_id"] == delivery_id
    assert payload["deliveries"][0]["delivery"]["delivery_state"] == "delivered"
    assert payload["deliveries"][0]["delivery"]["attempt_count"] == 2
    assert payload["deliveries"][0]["delivery"]["last_error"] is None


def test_routes_replay_json_reports_disabled_route_failure(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-disabled",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission resumed on the routed channel.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission resumed on the routed channel.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )
    asyncio.run(database.update_notification_route(route_id, enabled=False))

    result = runner.invoke(app, ["routes", "replay", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["attempted_count"] == 1
    assert payload["replayed_count"] == 0
    assert payload["failed_count"] == 1
    assert payload["deferred_count"] == 0
    assert payload["skipped_max_retries_count"] == 0
    assert deliveries == []
    assert payload["deliveries"][0]["delivery_id"] == delivery_id
    assert "unavailable for replay" in payload["deliveries"][0]["error"]
    assert payload["deliveries"][0]["delivery"]["delivery_state"] == "failed"
    assert payload["deliveries"][0]["delivery"]["max_retries_reached"] is True
    assert "unavailable for replay" in payload["deliveries"][0]["delivery"]["last_error"]


def test_routes_replay_json_reports_missing_saved_route_row_failure(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-missing-row",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission replay lost its saved route row.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission replay lost its saved route row.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )
    asyncio.run(database.delete_notification_route(route_id))

    result = runner.invoke(app, ["routes", "replay", "--json"])
    expected_error = f"Notification route {route_id} is unavailable for replay."

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["attempted_count"] == 1
    assert payload["replayed_count"] == 0
    assert payload["failed_count"] == 1
    assert payload["deferred_count"] == 0
    assert payload["skipped_max_retries_count"] == 0
    assert deliveries == []
    assert payload["deliveries"][0]["delivery_id"] == delivery_id
    assert payload["deliveries"][0]["route_id"] == route_id
    assert payload["deliveries"][0]["error"] == expected_error
    assert payload["deliveries"][0]["route"]["id"] == route_id
    assert payload["deliveries"][0]["route"]["name"] == "Deploy Room"
    assert payload["deliveries"][0]["route"]["enabled"] is False
    assert payload["deliveries"][0]["delivery"]["delivery_state"] == "failed"
    assert payload["deliveries"][0]["delivery"]["max_retries_reached"] is True
    assert payload["deliveries"][0]["delivery"]["last_error"] == expected_error


def test_routes_replay_reports_missing_saved_route_row_failure(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-missing-row-plain",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission replay lost its saved route row.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission replay lost its saved route row.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )
    asyncio.run(database.delete_notification_route(route_id))

    result = runner.invoke(app, ["routes", "replay"])
    expected_error = f"Notification route {route_id} is unavailable for replay."

    assert result.exit_code == 0, result.stdout
    assert "ok: False" in result.stdout
    assert "counts: attempted=1, replayed=0, failed=1, deferred=0, maxed=0" in result.stdout
    assert "[error] mission/updated -> Deploy Room" in result.stdout
    assert f"error: {expected_error}" in result.stdout
    assert deliveries == []

    refreshed_delivery = asyncio.run(database.get_outbound_delivery(delivery_id))
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == expected_error


def test_routes_replay_json_defers_saved_failed_delivery_in_backoff(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-deferred",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission resumed on the routed channel.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission resumed on the routed channel.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )

    result = runner.invoke(app, ["routes", "replay", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["attempted_count"] == 0
    assert payload["replayed_count"] == 0
    assert payload["failed_count"] == 0
    assert payload["deferred_count"] == 1
    assert payload["skipped_max_retries_count"] == 0
    assert payload["deliveries"] == []
    assert deliveries == []
    assert "1 deferred by backoff" in payload["summary"]

    refreshed_delivery = asyncio.run(database.get_outbound_delivery(delivery_id))
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == 1
    assert refreshed_delivery["last_error"] == "temporary upstream timeout"


def test_routes_replay_json_skips_saved_failed_delivery_at_max_retries(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-maxed",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission remained failed after exhausting retries.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission remained failed after exhausting retries.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=OUTBOUND_DELIVERY_MAX_RETRIES,
            last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
            last_error="delivery retries exhausted",
        )
    )

    result = runner.invoke(app, ["routes", "replay", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["attempted_count"] == 0
    assert payload["replayed_count"] == 0
    assert payload["failed_count"] == 0
    assert payload["deferred_count"] == 0
    assert payload["skipped_max_retries_count"] == 1
    assert payload["deliveries"] == []
    assert deliveries == []
    assert "1 hit max retries" in payload["summary"]

    refreshed_delivery = asyncio.run(database.get_outbound_delivery(delivery_id))
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == "delivery retries exhausted"


def test_routes_replay_skips_saved_failed_delivery_at_max_retries(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)) as client:
        route_response = client.post(
            "/api/notification-routes",
            json={
                "name": "Deploy Room",
                "kind": "webhook",
                "target": "https://example.invalid/deploy-room",
                "events": ["mission/*"],
                "conversation_target": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
                "enabled": True,
            },
        )
        assert route_response.status_code == 200, route_response.text
        route_id = route_response.json()["id"]

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=route_id,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-maxed-plain",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission remained failed after exhausting retries.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission remained failed after exhausting retries.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=OUTBOUND_DELIVERY_MAX_RETRIES,
            last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
            last_error="delivery retries exhausted",
        )
    )

    result = runner.invoke(app, ["routes", "replay"])

    assert result.exit_code == 0, result.stdout
    assert (
        "Replayed 0 delivery(s); 0 failed, 0 deferred by backoff, and 1 hit max retries."
        in result.stdout
    )
    assert "ok: True" in result.stdout
    assert "counts: attempted=0, replayed=0, failed=0, deferred=0, maxed=1" in result.stdout
    assert "[error]" not in result.stdout
    assert deliveries == []

    refreshed_delivery = asyncio.run(database.get_outbound_delivery(delivery_id))
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == "delivery retries exhausted"


def test_routes_replay_json_reports_missing_route_id_failure(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)):
        pass

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=None,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-missing-id",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission replay lost its saved route id.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission replay lost its saved route id.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )

    result = runner.invoke(app, ["routes", "replay", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["attempted_count"] == 1
    assert payload["replayed_count"] == 0
    assert payload["failed_count"] == 1
    assert payload["deferred_count"] == 0
    assert payload["skipped_max_retries_count"] == 0
    assert deliveries == []
    assert payload["deliveries"][0]["delivery_id"] == delivery_id
    assert (
        payload["deliveries"][0]["error"]
        == "Saved delivery is missing its notification route."
    )

    refreshed_delivery = asyncio.run(database.get_outbound_delivery(delivery_id))
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == "Saved delivery is missing its notification route."


def test_routes_replay_reports_missing_route_id_failure(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    deliveries: list[tuple[str, dict[str, object]]] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del self, route, secret_token
        deliveries.append((event_type, event))

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook",
        fake_post_webhook,
    )

    settings = Settings(data_dir=data_dir, db_path=data_dir / "openzues.db")
    api_app = create_app(settings)
    with TestClient(api_app, client=("testclient", 50000)):
        pass

    database = Database(settings.db_path)
    delivery_id = asyncio.run(
        database.create_outbound_delivery(
            route_id=None,
            route_name="Deploy Room",
            route_kind="webhook",
            route_target="https://example.invalid/deploy-room",
            event_type="mission/updated",
            session_key="route-session-missing-id-plain",
            conversation_target={
                "channel": "slack",
                "account_id": "workspace-bot",
                "peer_kind": "channel",
                "peer_id": "deploy-room",
            },
            route_scope={
                "route_name": "Deploy Room",
                "route_kind": "webhook",
                "route_target": "https://example.invalid/deploy-room",
                "route_match": "peer",
                "matched_value": "deploy-room",
            },
            event_payload={
                "summary": "Mission replay lost its saved route id.",
                "routeConversationTarget": {
                    "channel": "slack",
                    "account_id": "workspace-bot",
                    "peer_kind": "channel",
                    "peer_id": "deploy-room",
                },
            },
            message_summary="Mission replay lost its saved route id.",
            test_delivery=False,
            delivery_state="failed",
            attempt_count=1,
            last_attempt_at=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
            last_error="temporary upstream timeout",
        )
    )

    result = runner.invoke(app, ["routes", "replay"])

    assert result.exit_code == 0, result.stdout
    assert "ok: False" in result.stdout
    assert "counts: attempted=1, replayed=0, failed=1, deferred=0, maxed=0" in result.stdout
    assert "[error] mission/updated -> Deploy Room" in result.stdout
    assert "error: Saved delivery is missing its notification route." in result.stdout
    assert deliveries == []

    refreshed_delivery = asyncio.run(database.get_outbound_delivery(delivery_id))
    assert refreshed_delivery is not None
    assert refreshed_delivery["delivery_state"] == "failed"
    assert int(refreshed_delivery["attempt_count"]) == OUTBOUND_DELIVERY_MAX_RETRIES
    assert refreshed_delivery["last_error"] == "Saved delivery is missing its notification route."


def test_watch_json_defaults_to_saved_launch_handoff_task(monkeypatch) -> None:
    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        assert payload is None
        if method == "GET" and path == "/api/dashboard":
            return _watch_dashboard_payload()
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)

    result = runner.invoke(app, ["watch", "--url", "http://watch.test", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["watch_target"]["task_name"] == "OpenClaw Total Parity Program"
    assert payload["watch_target"]["task_blueprint_id"] == 2
    assert payload["watched_mission"]["id"] == 35
    assert payload["watched_mission"]["status"] == "paused"
    assert payload["setup_launch_handoff"]["headline"] == "Saved launch handoff is ready"


def test_watch_launch_resumes_paused_saved_mission(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        calls.append((method, path))
        if method == "GET" and path == "/api/dashboard":
            if ("POST", "/api/missions/35/start") in calls:
                return _watch_dashboard_payload(mission_status="active")
            return _watch_dashboard_payload(mission_status="paused")
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        if method == "POST" and path == "/api/missions/35/start":
            return {
                "id": 35,
                "name": "OpenClaw Total Parity Program",
                "status": "active",
            }
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)

    result = runner.invoke(app, ["watch", "--url", "http://watch.test", "--launch", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["auto_action"]["action"] == "resume_mission"
    assert payload["watched_mission"]["status"] == "active"
    assert ("POST", "/api/missions/35/start") in calls


def test_watch_prefers_paused_task_mission_over_completed_history(monkeypatch) -> None:
    dashboard = _watch_dashboard_payload(mission_status="paused")
    dashboard["missions"].insert(
        0,
        {
            "id": 36,
            "name": "OpenClaw Total Parity Program",
            "status": "completed",
            "phase": "completed",
            "task_blueprint_id": 2,
            "toolsets": ["delegation"],
            "current_command": None,
            "last_commentary": "Completed checkpoint.",
            "last_checkpoint": "Checkpoint complete.",
            "last_error": None,
            "in_progress": False,
            "live_telemetry": {"summary": "Last thread event arrived 90s ago."},
            "delegation_brief": {"summary": "Completed history."},
            "updated_at": "2026-04-12T15:30:00Z",
        },
    )
    dashboard["missions"][1]["updated_at"] = "2026-04-12T15:20:00Z"

    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        assert payload is None
        if method == "GET" and path == "/api/dashboard":
            return dashboard
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)

    result = runner.invoke(app, ["watch", "--url", "http://watch.test", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["watched_mission"]["id"] == 35
    assert payload["watched_mission"]["status"] == "paused"


def test_watch_browser_verify_summarizes_browser_state(monkeypatch) -> None:
    outputs = {
        ("errors", "--clear"): "",
        ("console", "--clear"): "✓ Console log cleared",
        ("open", "http://watch.test"): "",
        ("wait", "2000"): "",
        ("get", "url"): "http://watch.test/",
        ("get", "title"): "OpenZues",
        (
            "eval",
            "document.body && document.body.innerText.trim().length > 0 ? 'HAS_CONTENT' : 'BLANK'",
        ): '"HAS_CONTENT"',
        (
            "eval",
            "document.querySelector('[data-nextjs-dialog], .vite-error-overlay, "
            "#webpack-dev-server-client-overlay') ? 'ERROR_OVERLAY' : 'OK'",
        ): '"OK"',
        ("--annotate", "screenshot"): "✓ Screenshot saved to C:\\temp\\watch.png",
        (
            "snapshot",
            "-i",
        ): '- heading "OpenZues" [level=1, ref=e1]\n- button "Quick Connect" [ref=e2]',
        ("errors",): "",
        ("console",): "",
    }

    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        del timeout_seconds, allow_failure
        assert session_name == "watch-browser"
        key = tuple(args)
        if len(key) == 3 and key[:2] == ("--annotate", "screenshot"):
            return f"Screenshot saved to {key[2]}"
        if key not in outputs:
            raise AssertionError(f"Unexpected browser command: {key}")
        return outputs[key]

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    payload = _watch_browser_verify(
        browser_url="http://watch.test",
        session_name="watch-browser",
    )

    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["title"] == "OpenZues"
    assert payload["has_content"] is True
    assert payload["overlay_status"] == "OK"
    assert payload["screenshot_path"] is not None
    assert payload["screenshot_path"].endswith(".png")
    assert "OpenZues" in payload["snapshot_summary"]


def test_summarize_browser_snapshot_truncates_large_snapshot_output() -> None:
    huge_snapshot = "\n".join(
        f'- heading "OpenZues {index}" [level=1, ref=e{index}]'
        for index in range(5000)
    )

    summary = _summarize_browser_snapshot(huge_snapshot, limit=4)

    assert 'heading "OpenZues 0"' in summary
    assert 'heading "OpenZues 3"' in summary
    assert "[snapshot truncated]" in summary
    assert len(summary) < 1000


def test_watch_browser_verify_uses_screenshot_fallback_when_browser_probes_are_empty(
    tmp_path,
    monkeypatch,
) -> None:
    screenshot_path = tmp_path / "watch.png"
    screenshot_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 40_000)
    outputs = {
        ("errors", "--clear"): "",
        ("console", "--clear"): "",
        ("open", "http://watch.test"): "",
        ("wait", "2000"): "",
        ("get", "url"): "",
        ("get", "title"): "",
        (
            "eval",
            "document.body && document.body.innerText.trim().length > 0 ? 'HAS_CONTENT' : 'BLANK'",
        ): "",
        (
            "eval",
            "document.querySelector('[data-nextjs-dialog], .vite-error-overlay, "
            "#webpack-dev-server-client-overlay') ? 'ERROR_OVERLAY' : 'OK'",
        ): "",
        ("--annotate", "screenshot"): f"Screenshot saved to {screenshot_path}",
        ("snapshot", "-i"): "",
        ("errors",): "",
        ("console",): "",
    }

    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        del timeout_seconds, allow_failure
        assert session_name == "watch-browser"
        key = tuple(args)
        if len(key) == 3 and key[:2] == ("--annotate", "screenshot"):
            Path(key[2]).write_bytes(screenshot_path.read_bytes())
            return f"Screenshot saved to {key[2]}"
        if key not in outputs:
            raise AssertionError(f"Unexpected browser command: {key}")
        return outputs[key]

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)
    monkeypatch.setattr("openzues.cli._watch_http_content_signal", lambda *_args, **_kwargs: True)

    payload = _watch_browser_verify(
        browser_url="http://watch.test",
        session_name="watch-browser",
    )

    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["has_content"] is True
    assert payload["content_source"] == "screenshot"
    assert payload["screenshot_signal"] == "rendered"
    assert payload["screenshot_bytes"] == screenshot_path.stat().st_size


def test_watch_json_can_include_browser_verification(monkeypatch) -> None:
    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        assert payload is None
        if method == "GET" and path == "/api/dashboard":
            return _watch_dashboard_payload(mission_status="active")
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "watch-browser"
        return {
            "ok": True,
            "status": "ready",
            "summary": (
                "url http://watch.test, content visible, no overlay, "
                "0 page error(s), 0 console line(s)."
            ),
            "title": "OpenZues",
            "snapshot_summary": '- heading "OpenZues" [level=1, ref=e1]',
            "screenshot_path": "C:\\temp\\watch.png",
        }

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)
    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(
        app,
        [
            "watch",
            "--url",
            "http://watch.test",
            "--browser",
            "--browser-session",
            "watch-browser",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["watched_mission"]["status"] == "active"
    assert payload["browser_verification"]["status"] == "ready"
    assert payload["browser_verification"]["title"] == "OpenZues"
    assert payload["browser_verification"]["screenshot_path"] == "C:\\temp\\watch.png"


def test_watch_json_can_write_log_and_copy_browser_artifact(tmp_path, monkeypatch) -> None:
    source_screenshot = tmp_path / "browser-source.png"
    source_screenshot.write_bytes(b"browser-proof")
    log_path = tmp_path / "watch.log"
    artifact_path = tmp_path / "watch-latest.png"

    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        assert payload is None
        if method == "GET" and path == "/api/dashboard":
            return _watch_dashboard_payload(mission_status="active")
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "watch-browser"
        return {
            "ok": True,
            "status": "ready",
            "summary": "browser verification passed.",
            "title": "OpenZues",
            "snapshot_summary": '- heading "OpenZues" [level=1, ref=e1]',
            "screenshot_path": str(source_screenshot),
        }

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)
    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(
        app,
        [
            "watch",
            "--url",
            "http://watch.test",
            "--browser",
            "--browser-session",
            "watch-browser",
            "--browser-screenshot-copy",
            str(artifact_path),
            "--log-file",
            str(log_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["browser_verification"]["artifact_path"] == str(artifact_path)
    assert log_path.exists()
    assert "OpenClaw Total Parity Program" in log_path.read_text(encoding="utf-8")
    assert artifact_path.read_bytes() == b"browser-proof"


def test_append_watch_log_writes_utf8_bom_once(tmp_path) -> None:
    log_path = tmp_path / "watch.log"

    _append_watch_log(log_path, text="I’m here", max_bytes=10_000, backups=2)
    _append_watch_log(log_path, text="Still here", max_bytes=10_000, backups=2)

    raw = log_path.read_bytes()
    assert raw.startswith(codecs.BOM_UTF8)
    assert raw.count(codecs.BOM_UTF8) == 1
    decoded = raw.decode("utf-8-sig")
    assert "I’m here" in decoded
    assert "Still here" in decoded


def test_watch_json_surfaces_browser_timeout_warning(monkeypatch) -> None:
    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        assert payload is None
        if method == "GET" and path == "/api/dashboard":
            return _watch_dashboard_payload(mission_status="active")
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    def fake_browser_verify(*, browser_url: str, session_name: str):
        assert browser_url == "http://watch.test"
        assert session_name == "watch-browser"
        raise RuntimeError("browser verification timed out after 45s.")

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)
    monkeypatch.setattr(
        "openzues.cli._watch_browser_verify_guarded",
        fake_browser_verify,
    )

    result = runner.invoke(
        app,
        [
            "watch",
            "--url",
            "http://watch.test",
            "--browser",
            "--browser-session",
            "watch-browser",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["browser_verification"]["ok"] is False
    assert payload["browser_verification"]["status"] == "warn"
    assert payload["browser_verification"]["summary"] == (
        "browser verification timed out after 45s."
    )


def test_append_watch_log_upgrades_existing_utf8_file_without_bom(tmp_path) -> None:
    log_path = tmp_path / "watch.log"
    log_path.write_text("Already here\n", encoding="utf-8")

    _append_watch_log(log_path, text="I’m next", max_bytes=10_000, backups=2)

    raw = log_path.read_bytes()
    assert raw.startswith(codecs.BOM_UTF8)
    assert raw.count(codecs.BOM_UTF8) == 1
    decoded = raw.decode("utf-8-sig")
    assert "Already here" in decoded
    assert "I’m next" in decoded


def test_watch_browser_verify_tolerates_optional_browser_artifact_failures(
    monkeypatch,
) -> None:
    outputs = {
        ("errors", "--clear"): "",
        ("console", "--clear"): "",
        ("open", "http://watch.test"): "",
        ("wait", "2000"): "",
        ("get", "url"): "http://watch.test/",
        ("get", "title"): "OpenZues",
        (
            "eval",
            "document.body && document.body.innerText.trim().length > 0 ? 'HAS_CONTENT' : 'BLANK'",
        ): '"HAS_CONTENT"',
        (
            "eval",
            "document.querySelector('[data-nextjs-dialog], .vite-error-overlay, "
            "#webpack-dev-server-client-overlay') ? 'ERROR_OVERLAY' : 'OK'",
        ): '"OK"',
        ("errors",): "",
        ("console",): "",
    }

    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        del timeout_seconds, allow_failure
        assert session_name == "watch-browser"
        key = tuple(args)
        if len(key) == 3 and key[:2] == ("--annotate", "screenshot"):
            raise RuntimeError("annotated screenshot timed out")
        if key == ("snapshot", "-i"):
            raise RuntimeError("snapshot timed out")
        if key not in outputs:
            raise AssertionError(f"Unexpected browser command: {key}")
        return outputs[key]

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    payload = _watch_browser_verify(
        browser_url="http://watch.test",
        session_name="watch-browser",
    )

    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["screenshot_path"] is None
    assert payload["snapshot_summary"] == "Browser snapshot unavailable."
    assert payload["screenshot_error"] == "annotated screenshot timed out"
    assert payload["snapshot_error"] == "snapshot timed out"


def test_watch_browser_verify_uses_bounded_timeout_budget(monkeypatch) -> None:
    observed: list[tuple[tuple[str, ...], float, bool]] = []
    outputs = {
        ("errors", "--clear"): "",
        ("console", "--clear"): "",
        ("open", "http://watch.test"): "",
        ("wait", "2000"): "",
        ("get", "url"): "http://watch.test/",
        ("get", "title"): "OpenZues",
        (
            "eval",
            "document.body && document.body.innerText.trim().length > 0 ? 'HAS_CONTENT' : 'BLANK'",
        ): '"HAS_CONTENT"',
        (
            "eval",
            "document.querySelector('[data-nextjs-dialog], .vite-error-overlay, "
            "#webpack-dev-server-client-overlay') ? 'ERROR_OVERLAY' : 'OK'",
        ): '"OK"',
        ("snapshot", "-i"): "",
        ("errors",): "",
        ("console",): "",
    }

    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        assert session_name == "watch-browser"
        key = tuple(args)
        observed.append((key, timeout_seconds, allow_failure))
        if len(key) == 3 and key[:2] == ("--annotate", "screenshot"):
            return f"Screenshot saved to {key[2]}"
        if key not in outputs:
            raise AssertionError(f"Unexpected browser command: {key}")
        return outputs[key]

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)

    _watch_browser_verify(
        browser_url="http://watch.test",
        session_name="watch-browser",
    )

    timeout_by_command = {key: timeout for key, timeout, _allow_failure in observed}
    assert timeout_by_command[("open", "http://watch.test")] == 15.0
    assert timeout_by_command[("wait", "2000")] == 5.0
    assert timeout_by_command[("get", "url")] == 3.0
    assert timeout_by_command[("get", "title")] == 3.0
    assert timeout_by_command[("snapshot", "-i")] == 4.0
    assert timeout_by_command[("errors",)] == 3.0
    assert timeout_by_command[("console",)] == 3.0


def test_watch_browser_verify_ignores_invalid_windows_probe_output(
    tmp_path,
    monkeypatch,
) -> None:
    screenshot_path = tmp_path / "watch.png"
    screenshot_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 40_000)
    clr_failure = "Starting the CLR failed with HRESULT 80004005."
    outputs = {
        ("errors", "--clear"): "",
        ("console", "--clear"): "",
        ("open", "http://watch.test"): "",
        ("wait", "2000"): "",
        ("get", "url"): clr_failure,
        ("get", "title"): clr_failure,
        (
            "eval",
            "document.body && document.body.innerText.trim().length > 0 ? 'HAS_CONTENT' : 'BLANK'",
        ): clr_failure,
        (
            "eval",
            "document.querySelector('[data-nextjs-dialog], .vite-error-overlay, "
            "#webpack-dev-server-client-overlay') ? 'ERROR_OVERLAY' : 'OK'",
        ): clr_failure,
        ("snapshot", "-i"): "",
        ("errors",): "",
        ("console",): "",
    }

    def fake_run_browser_command(
        args: list[str],
        *,
        session_name: str,
        timeout_seconds: float = 60.0,
        allow_failure: bool = False,
    ) -> str:
        del timeout_seconds, allow_failure
        assert session_name == "watch-browser"
        key = tuple(args)
        if len(key) == 3 and key[:2] == ("--annotate", "screenshot"):
            Path(key[2]).write_bytes(screenshot_path.read_bytes())
            return f"Screenshot saved to {key[2]}"
        if key not in outputs:
            raise AssertionError(f"Unexpected browser command: {key}")
        return outputs[key]

    monkeypatch.setattr("openzues.cli._run_browser_command", fake_run_browser_command)
    monkeypatch.setattr("openzues.cli._watch_http_content_signal", lambda *_args, **_kwargs: True)

    payload = _watch_browser_verify(
        browser_url="http://watch.test",
        session_name="watch-browser",
    )

    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["url"] == "http://watch.test"
    assert payload["title"] is None
    assert payload["overlay_status"] == "unknown"
    assert "HRESULT" not in payload["summary"]


def test_run_windows_browser_command_captures_redirected_child_output(monkeypatch) -> None:
    def fake_subprocess_run(command, **kwargs):  # noqa: ANN001
        del kwargs
        script = command[3]
        stdout_match = re.search(r"RedirectStandardOutput = '([^']+)'", script)
        stderr_match = re.search(r"RedirectStandardError = '([^']+)'", script)
        assert stdout_match is not None
        assert stderr_match is not None
        Path(stdout_match.group(1)).write_bytes("http://watch.test/\n".encode("utf-16-le"))
        Path(stderr_match.group(1)).write_bytes(b"")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("openzues.cli.subprocess.run", fake_subprocess_run)

    output = cli_module._run_windows_browser_command(
        [
            r"C:\Users\skull\AppData\Roaming\npm\agent-browser.cmd",
            "--session",
            "watch-browser",
            "get",
            "url",
        ],
        args=["get", "url"],
        timeout_seconds=6.0,
        allow_failure=False,
    )

    assert output == "http://watch.test/"


def test_run_browser_command_uses_direct_capture_for_windows_output_probes(monkeypatch) -> None:
    monkeypatch.setattr(cli_module.os, "name", "nt", raising=False)
    monkeypatch.setattr("openzues.cli._browser_command", lambda: "agent-browser.cmd")

    def fake_direct(invocation, **kwargs):  # noqa: ANN001
        assert invocation == ["agent-browser.cmd", "--session", "watch-browser", "get", "url"]
        assert kwargs["args"] == ["get", "url"]
        return "http://watch.test/"

    def fake_background(invocation, **kwargs):  # noqa: ANN001
        raise AssertionError(f"Unexpected background runner call: {invocation} {kwargs}")

    monkeypatch.setattr("openzues.cli._run_windows_browser_command_direct", fake_direct)
    monkeypatch.setattr("openzues.cli._run_windows_browser_command", fake_background)

    output = cli_module._run_browser_command(
        ["get", "url"],
        session_name="watch-browser",
        timeout_seconds=3.0,
    )

    assert output == "http://watch.test/"


def test_watch_human_output_calls_out_observer_mode(monkeypatch) -> None:
    dashboard = _watch_dashboard_payload(mission_status="active")
    dashboard["control_chat"] = {
        "headline": "Observer mode is active",
        "summary": (
            "Observer mode is active because another OpenZues server already owns the "
            "autonomous control plane for this data dir. Leader PID: 18672."
        ),
        "messages": [],
    }
    dashboard["attention_queue"] = {
        "enabled": False,
        "headline": "Observer mode is active",
        "summary": (
            "Autonomous queue workers are paused in this window because another OpenZues "
            "server already owns the control-plane lease. Leader PID: 18672."
        ),
        "actions": [],
    }
    dashboard["instances"][0]["connected"] = False
    dashboard["gateway_capability"]["summary"] = "0/2 lane(s) connected in the observer window."

    def fake_watch_api_json(
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        payload=None,
        **_kwargs,
    ):
        assert base_url == "http://watch.test"
        assert payload is None
        if method == "GET" and path == "/api/dashboard":
            return dashboard
        if method == "GET" and path == "/api/setup/launch":
            return _watch_handoff_payload()
        raise AssertionError(f"Unexpected watch request: {method} {path}")

    monkeypatch.setattr("openzues.cli._watch_api_json", fake_watch_api_json)

    result = runner.invoke(app, ["watch", "--url", "http://watch.test"])

    assert result.exit_code == 0, result.stdout
    assert "mode: observer / leader PID 18672" in result.stdout
    assert "mode note: Mission telemetry may be leader-owned" in result.stdout
    assert "observer handoff:" in result.stdout
    assert "observer lanes:" in result.stdout
    assert "observer gateway:" in result.stdout


def test_status_human_output_includes_gateway_radar_launchpad_and_queue(
    tmp_path, monkeypatch
) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch)
    monkeypatch.setattr(
        "openzues.services.browser_posture.find_agent_browser_command",
        lambda: "agent-browser.cmd",
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.stdout
    assert "missions:" in result.stdout
    assert "lanes:" in result.stdout
    assert "status:" in result.stdout
    assert "gateway:" in result.stdout
    assert "browser:" in result.stdout
    assert "lane health:" in result.stdout
    assert "inventory:" in result.stdout
    assert "approvals:" in result.stdout
    assert "launch policy:" in result.stdout
    assert "radar:" in result.stdout
    assert "launchpad:" in result.stdout
    assert "queue:" in result.stdout
    assert "next:" in result.stdout


def test_emit_status_human_output_includes_launchpad_opportunity_ids(capsys) -> None:
    _emit_status(
        {
            "headline": "OpenZues is operator-ready",
            "summary": "One explicit launch is available.",
            "status_plan": {"reply": "Status reply"},
            "mission_summary": {
                "active_count": 0,
                "blocked_count": 0,
                "paused_count": 0,
                "failed_count": 0,
            },
            "instance_summary": {"connected_count": 1, "total_count": 1},
            "gateway_capability": {
                "summary": "Gateway summary",
                "connected_lane_health": {"summary": "Lane summary"},
                "inventory": {"summary": "Inventory summary"},
                "approval_posture": {"summary": "Approval summary"},
                "launch_policy": {"summary": "Launch summary"},
                "warnings": [],
            },
            "radar": {
                "summary": "Radar summary",
                "signals": [
                    {
                        "id": "gateway/capability",
                        "level": "warn",
                        "title": "Gateway capability has live gaps",
                        "detail": "Connected lanes need repair before launch.",
                    }
                ],
            },
            "launchpad": {
                "summary": "Launchpad summary",
                "opportunities": [
                    {"id": "gateway-repair", "title": "Stabilize gateway posture"},
                ],
            },
            "queue_plan": {"reply": "Queue reply"},
            "brief": {"next_actions": ["Next action"]},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert (
        "[WARN] Gateway capability has live gaps (gateway/capability): "
        "Connected lanes need repair before launch."
    ) in output
    assert "opportunity: Stabilize gateway posture (gateway-repair)" in output


def test_launch_plan_targets_selected_launchpad_opportunity(monkeypatch) -> None:
    draft = MissionDraftView(
        name="Stabilize Gateway Posture",
        objective="Repair the gateway posture before the next launch.",
        instance_id=3,
        project_id=None,
        cwd="C:\\repo",
        model="gpt-5.4-mini",
        max_turns=3,
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
        start_immediately=True,
    )
    opportunity = SimpleNamespace(
        id="gateway-repair",
        title="Stabilize gateway posture",
        summary="Repair the gateway before launching more work.",
        why_now="Gateway Doctor says the saved launch posture needs repair.",
        action_label="Load gateway repair",
        mission_draft=draft,
    )

    async def fake_dashboard(_services):
        return SimpleNamespace(launchpad=SimpleNamespace(opportunities=[opportunity]))

    async def fake_run_with_services(action):
        return await action(SimpleNamespace())

    monkeypatch.setattr("openzues.cli._build_operator_dashboard", fake_dashboard)
    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["launch", "gateway-repair", "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "plan"
    assert payload["executed"] is False
    assert payload["action_kind"] == "launch_opportunity"
    assert payload["opportunity_id"] == "gateway-repair"
    assert payload["target_label"] == "Stabilize gateway posture"
    assert "launchpad because" in payload["reply"]
    assert payload["mission_id"] is None
    assert payload["mission_payload"]["name"] == "Stabilize Gateway Posture"


def test_launch_execute_creates_selected_launchpad_mission(monkeypatch) -> None:
    draft = MissionDraftView(
        name="Stabilize Gateway Posture",
        objective="Repair the gateway posture before the next launch.",
        instance_id=3,
        project_id=None,
        cwd="C:\\repo",
        model="gpt-5.4-mini",
        max_turns=3,
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
        start_immediately=True,
    )
    opportunity = SimpleNamespace(
        id="gateway-repair",
        title="Stabilize gateway posture",
        summary="Repair the gateway before launching more work.",
        why_now="Gateway Doctor says the saved launch posture needs repair.",
        action_label="Load gateway repair",
        mission_draft=draft,
    )

    async def fake_dashboard(_services):
        return SimpleNamespace(launchpad=SimpleNamespace(opportunities=[opportunity]))

    class FakeMissionService:
        async def create(self, payload):
            assert payload.name == "Stabilize Gateway Posture"
            return SimpleNamespace(id=44, name=payload.name)

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(mission_service=FakeMissionService()))

    monkeypatch.setattr("openzues.cli._build_operator_dashboard", fake_dashboard)
    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["launch", "gateway-repair", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "executed"
    assert payload["executed"] is True
    assert payload["action_kind"] == "launch_opportunity"
    assert payload["opportunity_id"] == "gateway-repair"
    assert payload["mission_id"] is not None
    assert payload["target_label"] == "Stabilize Gateway Posture"
    assert "I launched `Stabilize gateway posture`" in payload["reply"]


def test_launch_plan_can_force_swarm_constitution(monkeypatch) -> None:
    draft = MissionDraftView(
        name="Stabilize Gateway Posture",
        objective="Repair the gateway posture before the next launch.",
        instance_id=3,
        project_id=None,
        cwd="C:\\repo",
        model="gpt-5.4-mini",
        max_turns=3,
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
        start_immediately=True,
    )
    opportunity = SimpleNamespace(
        id="gateway-repair",
        title="Stabilize gateway posture",
        summary="Repair the gateway before launching more work.",
        why_now="Gateway Doctor says the saved launch posture needs repair.",
        action_label="Load gateway repair",
        mission_draft=draft,
    )

    async def fake_dashboard(_services):
        return SimpleNamespace(launchpad=SimpleNamespace(opportunities=[opportunity]))

    async def fake_run_with_services(action):
        return await action(SimpleNamespace())

    monkeypatch.setattr("openzues.cli._build_operator_dashboard", fake_dashboard)
    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["launch", "gateway-repair", "--swarm", "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "plan"
    assert payload["swarm_enabled"] is True
    assert payload["mission_payload"]["swarm_enabled"] is True
    assert payload["mission_payload"]["collaboration_mode"] == "swarm_constitution"
    assert "swarm constitution" in payload["reply"].lower()


def test_launch_execute_can_force_swarm_constitution(monkeypatch) -> None:
    draft = MissionDraftView(
        name="Stabilize Gateway Posture",
        objective="Repair the gateway posture before the next launch.",
        instance_id=3,
        project_id=None,
        cwd="C:\\repo",
        model="gpt-5.4-mini",
        max_turns=3,
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
        start_immediately=True,
    )
    opportunity = SimpleNamespace(
        id="gateway-repair",
        title="Stabilize gateway posture",
        summary="Repair the gateway before launching more work.",
        why_now="Gateway Doctor says the saved launch posture needs repair.",
        action_label="Load gateway repair",
        mission_draft=draft,
    )

    async def fake_dashboard(_services):
        return SimpleNamespace(launchpad=SimpleNamespace(opportunities=[opportunity]))

    class FakeMissionService:
        async def create(self, payload):
            assert payload.name == "Stabilize Gateway Posture"
            assert payload.swarm_enabled is True
            assert payload.collaboration_mode == "swarm_constitution"
            return SimpleNamespace(id=44, name=payload.name)

    async def fake_run_with_services(action):
        return await action(SimpleNamespace(mission_service=FakeMissionService()))

    monkeypatch.setattr("openzues.cli._build_operator_dashboard", fake_dashboard)
    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["launch", "gateway-repair", "--swarm", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "executed"
    assert payload["executed"] is True
    assert payload["swarm_enabled"] is True
    assert payload["mission_id"] is not None
    assert "swarm constitution" in payload["reply"].lower()


def test_launch_rejects_unknown_launchpad_opportunity_id(monkeypatch) -> None:
    opportunity = SimpleNamespace(
        id="gateway-repair",
        title="Stabilize gateway posture",
        summary="Repair the gateway before launching more work.",
        why_now="Gateway Doctor says the saved launch posture needs repair.",
        action_label="Load gateway repair",
        mission_draft=MissionDraftView(
            name="Stabilize Gateway Posture",
            objective="Repair the gateway posture before the next launch.",
            instance_id=3,
            project_id=None,
            cwd="C:\\repo",
            model="gpt-5.4-mini",
            max_turns=3,
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
            start_immediately=True,
        ),
    )

    async def fake_dashboard(_services):
        return SimpleNamespace(launchpad=SimpleNamespace(opportunities=[opportunity]))

    async def fake_run_with_services(action):
        return await action(SimpleNamespace())

    monkeypatch.setattr("openzues.cli._build_operator_dashboard", fake_dashboard)
    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["launch", "not-a-real-opportunity"])

    assert result.exit_code == 1
    assert (
        "Launchpad opportunity 'not-a-real-opportunity' is not available right now."
        in result.stderr
    )
    assert "Available ids: gateway-repair." in result.stderr


def test_recover_plan_passes_recover_prompt_to_control_chat_planner(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Recover Loop")

    captured: list[str] = []

    def fake_plan(prompt: str, dashboard) -> ControlChatPlan:
        captured.append(prompt)
        return ControlChatPlan(
            action_kind="launch_opportunity",
            reply="I launched `Recover ForumForge` because the failed checkpoint is reusable.",
            opportunity_id="recover-7",
            target_label="Recover ForumForge",
        )

    monkeypatch.setattr("openzues.cli.plan_control_chat", fake_plan)

    result = runner.invoke(app, ["recover", "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert captured == ["recover"]
    assert payload["mode"] == "plan"
    assert payload["executed"] is False
    assert payload["action_kind"] == "launch_opportunity"
    assert payload["target_label"] == "Recover ForumForge"
    assert payload["opportunity_id"] == "recover-7"


def test_recover_plan_smoke_builds_real_dashboard(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Recover Loop")

    result = runner.invoke(app, ["recover", "--plan", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["mode"] == "plan"
    assert isinstance(payload["action_kind"], str)
    assert "reply" in payload


def test_harden_execute_submits_harden_prompt(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Harden Loop")

    captured: list[str] = []

    async def fake_submit(self, prompt: str, dashboard) -> ControlChatResponse:
        captured.append(prompt)
        created_at = datetime.now(UTC)
        return ControlChatResponse(
            user=ControlChatMessageView(
                id=11,
                role="user",
                content=prompt,
                created_at=created_at,
            ),
            assistant=ControlChatMessageView(
                id=12,
                role="assistant",
                content=(
                    "I launched `Harden ForumForge` because the finished "
                    "checkpoint is the highest-leverage follow-through."
                ),
                action_kind="launch_opportunity",
                mission_id=44,
                opportunity_id="harden-44",
                target_label="Harden ForumForge",
                created_at=created_at,
            ),
            action_kind="launch_opportunity",
            executed=True,
        )

    monkeypatch.setattr("openzues.cli.ControlChatService.submit", fake_submit)

    result = runner.invoke(app, ["harden", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert captured == ["harden"]
    assert payload["mode"] == "executed"
    assert payload["executed"] is True
    assert payload["action_kind"] == "launch_opportunity"
    assert payload["mission_id"] == 44
    assert payload["opportunity_id"] == "harden-44"
    assert payload["target_label"] == "Harden ForumForge"


def test_routes_test_command_executes_delivery_ping(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Route Loop")

    database = Database(data_dir / "openzues.db")
    asyncio.run(database.initialize())
    route_id = asyncio.run(
        database.create_notification_route(
            name="CLI Ops Hook",
            kind="webhook",
            target="https://example.invalid/cli-webhook",
            events=["ops/inbox/*"],
            enabled=True,
            secret_header_name=None,
            secret_token=None,
            vault_secret_id=None,
        )
    )
    deliveries: list[str] = []

    def fake_post_webhook(
        self,  # noqa: ANN001
        route: dict[str, object],
        event_type: str,
        event: dict[str, object],
        secret_token: str | None,
    ) -> None:
        del route, event, secret_token
        deliveries.append(event_type)

    monkeypatch.setattr(
        "openzues.services.ops_mesh.OpsMeshService._post_webhook", fake_post_webhook
    )

    result = runner.invoke(app, ["routes", "test", str(route_id), "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["event_type"] == "ops/inbox/test"
    assert payload["route_id"] == route_id
    assert deliveries == ["ops/inbox/test"]


def test_hermes_arm_shell_command_uses_saved_gateway_workspace(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Shell Loop")

    result = runner.invoke(app, ["hermes", "arm-shell", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["executor_key"] == "workspace_shell"
    assert payload["derived_from"] == "gateway_default_cwd"
    assert payload["instance"]["transport"] == "stdio"
    assert payload["connected"] is False
    assert payload["cwd"] == str(tmp_path)


def test_hermes_arm_docker_command_uses_saved_gateway_workspace(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Docker Loop")
    monkeypatch.setattr(
        "openzues.services.hermes_platform._which", lambda command: command == "docker"
    )

    result = runner.invoke(app, ["hermes", "arm-docker", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["executor_key"] == "docker"
    assert payload["derived_from"] == "gateway_default_cwd"
    assert payload["instance"]["transport"] == "desktop"
    assert payload["connected"] is False
    assert payload["cwd"] == str(tmp_path)
    assert payload["image"] == "nikolaik/python-nodejs:python3.11-nodejs20"


def test_hermes_preflight_docker_command_reports_ready_backend(tmp_path, monkeypatch) -> None:
    _bootstrap_cli_workspace(tmp_path, monkeypatch, task_name="CLI Docker Preflight")
    monkeypatch.setattr(
        "openzues.services.hermes_platform._which", lambda command: command == "docker"
    )
    monkeypatch.setattr(
        "openzues.services.hermes_platform.shutil.which",
        lambda command: "C:\\docker\\docker.exe" if command == "docker" else None,
    )

    async def fake_run_process_capture(
        *args: str, timeout_seconds: float = 20.0
    ) -> tuple[int, str, str]:
        del timeout_seconds
        command = tuple(args)
        if command[-1] == "--version":
            return 0, "Docker version 29.3.1, build c2be9cc", ""
        if command[1:3] == ("info", "--format"):
            return 0, "29.3.1", ""
        if command[1:4] == ("image", "inspect", "nikolaik/python-nodejs:python3.11-nodejs20"):
            return 0, "sha256:testimage", ""
        raise AssertionError(f"Unexpected docker command: {command}")

    monkeypatch.setattr(
        "openzues.services.hermes_platform._run_process_capture",
        fake_run_process_capture,
    )

    runner.invoke(app, ["hermes", "arm-docker", "--json"])
    result = runner.invoke(app, ["hermes", "preflight-docker", "--json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["image_present"] is True
    assert payload["daemon_version"] == "29.3.1"


def test_emit_gateway_capability_human_output_includes_memory_proof(capsys) -> None:
    _emit_gateway_capability(
        {
            "headline": "Gateway capability is operator-ready",
            "summary": "Gateway summary",
            "connected_lane_health": {"summary": "1/1 lanes connected"},
            "inventory": {
                "summary": "Inventory summary",
                "memory_summary": "Memory summary",
                "memory_evidence": ["Tool proof passed."],
                "memory_proof_continuity": {
                    "id": "mission:7",
                    "mission_id": 7,
                    "mission_name": "MemPalace Memory Loop",
                    "project_label": "Memory Workspace",
                    "state": "anchored",
                    "score": 84,
                    "freshness_minutes": 3,
                    "drift_signatures": ["thin checkpoint memory"],
                    "summary": (
                        "This mission is packed cleanly enough for a low-friction handoff "
                        "or later resume."
                    ),
                    "anchor": "Roundtrip status: verified",
                    "drift": (
                        "Context currently looks stable; the main risk is letting the next "
                        "turn broaden the scope without refreshing the handoff."
                    ),
                    "next_handoff": (
                        "Continue from the current anchor, verify one concrete claim, and "
                        "refresh the relay packet at turn end."
                    ),
                    "relay_prompt": "You are resuming or taking over an OpenZues mission.",
                },
                "memory_proof_launchable": True,
                "memory_proof_target_instance_id": 3,
                "memory_proof_launch_label": "Run direct memory proof for Memory Workspace",
                "memory_proof_reference": {
                    "mission_id": 7,
                    "mission_name": "MemPalace Memory Loop",
                    "task_blueprint_id": 5,
                    "task_name": "MemPalace Memory Loop",
                    "scope_label": "Memory Workspace",
                    "proof_kind": "roundtrip",
                    "proof_status": "verified",
                    "summary": (
                        "Mission 7 verified MemPalace roundtrip recall for Memory Workspace."
                    ),
                    "checkpoint_excerpt": "Roundtrip status: verified",
                    "continuity_path": "/api/missions/7/continuity",
                },
            },
            "approval_posture": {"summary": "Approval posture is armed"},
            "launch_policy": {"summary": "Saved local launch policy"},
            "diagnostics": {"summary": "Gateway diagnostics are steady"},
        },
        json_output=False,
    )

    output = capsys.readouterr().out
    assert "memory proof:" in output
    assert "Mission 7 verified MemPalace roundtrip recall" in output
    assert "memory proof continuity: /api/missions/7/continuity" in output
    assert "memory relay: anchored (84/100)" in output
    assert "memory relay summary: This mission is packed cleanly enough" in output
    assert "memory relay anchor: Roundtrip status: verified" in output
    assert "memory relay next: Continue from the current anchor" in output
    assert "memory proof launch: Run direct memory proof for Memory Workspace" in output


def test_gateway_memory_prove_command_emits_direct_proof_mission(monkeypatch) -> None:
    class FakeMissionResult:
        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            assert mode == "json"
            return {
                "id": 11,
                "name": "MemPalace Direct Proof: Memory Workspace",
                "instance_name": "Memory Lane",
                "project_label": "Memory Workspace",
                "status": "active",
                "phase": "thinking",
                "thread_id": "thread-memory-proof-direct",
                "objective": "# MemPalace Direct Proof\n\nProject: Memory Workspace",
            }

    async def fake_run_with_services(action):
        return FakeMissionResult()

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["gateway", "memory-prove"])

    assert result.exit_code == 0, result.stdout
    assert "memory proof mission 11: MemPalace Direct Proof: Memory Workspace" in result.stdout
    assert "lane: Memory Lane" in result.stdout
    assert "scope: Memory Workspace" in result.stdout
    assert "status: active (thinking)" in result.stdout
    assert "thread: thread-memory-proof-direct" in result.stdout


def test_recall_command_emits_human_output(monkeypatch) -> None:
    class FakeRecallResult:
        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            assert mode == "json"
            return {
                "headline": "Recall found 1 match",
                "summary": "Saved mission memory matched forum migration.",
                "items": [
                    {
                        "mission_id": 7,
                        "mission_name": "ForumForge Inbox + Queue Build",
                        "project_label": "OpenZues Workspace",
                        "match_source": "checkpoint",
                        "score": 18,
                        "freshness_minutes": 5,
                        "excerpt": "Forum migration handoff captured for durable recall.",
                        "next_handoff": "Resume from the verified forum migration checkpoint.",
                        "continuity_path": "/api/missions/7/continuity",
                    }
                ],
            }

    async def fake_run_with_services(action):
        return FakeRecallResult()

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["recall", "forum migration"])

    assert result.exit_code == 0, result.stdout
    assert "Recall found 1 match" in result.stdout
    assert "[M7] ForumForge Inbox + Queue Build" in result.stdout
    assert "checkpoint | score 18 | OpenZues Workspace | 5m ago" in result.stdout
    assert "Forum migration handoff captured for durable recall." in result.stdout
    assert "continuity: /api/missions/7/continuity" in result.stdout


def test_learn_command_emits_learning_reviews(monkeypatch) -> None:
    class FakeCortexResult:
        def model_dump(self, *, mode: str = "json") -> dict[str, object]:
            assert mode == "json"
            return {
                "headline": "The autonomy cortex is learning",
                "summary": "Hermes review passes surfaced 2 reusable lessons.",
                "doctrines": [],
                "inoculations": [],
                "reviews": [
                    {
                        "level": "warn",
                        "title": "Promote the winning tool posture for Beacon",
                        "project_label": "Beacon",
                        "evidence_count": 4,
                        "recommended_toolsets": ["browser", "debugging", "delegation"],
                        "summary": "Checkpointed runs kept landing with browser-led verification.",
                        "recommendation": "Carry those toolsets into the next launch.",
                    }
                ],
            }

    async def fake_run_with_services(action):
        return FakeCortexResult()

    monkeypatch.setattr("openzues.cli._run_with_services", fake_run_with_services)

    result = runner.invoke(app, ["learn"])

    assert result.exit_code == 0, result.stdout
    assert "The autonomy cortex is learning" in result.stdout
    assert "[WARN] Promote the winning tool posture for Beacon" in result.stdout
    assert "Beacon | 4 evidence points | browser, debugging, delegation" in result.stdout
    assert "Carry those toolsets into the next launch." in result.stdout


def test_setup_bootstrap_can_stage_mempalace_from_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(data_dir))

    result = runner.invoke(
        app,
        [
            "setup",
            "bootstrap",
            "--project-path",
            str(tmp_path),
            "--operator-name",
            "CLI Builder",
            "--task-name",
            "CLI Memory Loop",
            "--objective-template",
            "Ship the next verified memory-backed slice.",
            "--use-mempalace",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["integration"]["label"] == "MemPalace"
    assert payload["memory_task_blueprint"]["label"] == "MemPalace Memory Loop"
    assert "MemPalace memory protocol:" in payload["mission_draft"]["objective"]


def test_setup_bootstrap_cli_persists_default_device_bootstrap_profile(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(data_dir))

    bootstrap = runner.invoke(
        app,
        [
            "setup",
            "bootstrap",
            "--project-path",
            str(tmp_path),
            "--operator-name",
            "CLI Builder",
            "--task-name",
            "CLI Bootstrap Profile",
            "--objective-template",
            "Ship the next verified bootstrap slice.",
            "--json",
        ],
    )

    assert bootstrap.exit_code == 0, bootstrap.stdout

    gateway = runner.invoke(app, ["gateway", "show", "--json"])

    assert gateway.exit_code == 0, gateway.stdout
    payload = json.loads(gateway.stdout)
    assert payload["bootstrap_roles"] == ["node", "operator"]
    assert payload["bootstrap_scopes"] == list(BOOTSTRAP_HANDOFF_OPERATOR_SCOPES)


def test_doctor_and_update_status_json_include_hermes_sections(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    hermes_root = tmp_path / "hermes-agent-main"
    (hermes_root / "plugins" / "memory" / "mem0").mkdir(parents=True, exist_ok=True)
    (hermes_root / "plugins" / "memory" / "mem0" / "__init__.py").write_text(
        "# stub\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(data_dir))
    monkeypatch.setenv("OPENZUES_HERMES_SOURCE_PATH", str(hermes_root))

    bootstrap = runner.invoke(
        app,
        [
            "setup",
            "bootstrap",
            "--project-path",
            str(tmp_path),
            "--operator-name",
            "CLI Builder",
            "--task-name",
            "CLI Hermes Loop",
            "--objective-template",
            "Ship the next verified Hermes slice.",
            "--json",
        ],
    )
    assert bootstrap.exit_code == 0, bootstrap.stdout

    doctor = runner.invoke(app, ["doctor", "--json"])
    update = runner.invoke(app, ["update", "status", "--json"])

    assert doctor.exit_code == 0, doctor.stdout
    assert update.exit_code == 0, update.stdout

    doctor_payload = json.loads(doctor.stdout)
    update_payload = json.loads(update.stdout)
    assert "profile" in doctor_payload
    assert "promotion_loop" in doctor_payload
    assert "memory" in doctor_payload
    assert "executors" in doctor_payload
    assert "plugins" in doctor_payload
    assert "delivery" in doctor_payload
    assert "updates" in doctor_payload
    assert update_payload["headline"]


def test_hermes_profile_set_updates_saved_defaults(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    hermes_root = tmp_path / "hermes-agent-main"
    (hermes_root / "plugins" / "memory" / "mem0").mkdir(parents=True, exist_ok=True)
    (hermes_root / "plugins" / "memory" / "mem0" / "__init__.py").write_text(
        "# stub\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENZUES_DATA_DIR", str(data_dir))
    monkeypatch.setenv("OPENZUES_HERMES_SOURCE_PATH", str(hermes_root))

    result = runner.invoke(
        app,
        [
            "hermes",
            "profile",
            "set",
            "--memory-provider",
            "mem0",
            "--executor",
            "workspace_shell",
            "--no-auto-promote",
            "--no-plugin-discovery",
            "--no-channel-inventory",
            "--no-acp-inventory",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["preferred_memory_provider"] == "mem0"
    assert payload["preferred_executor"] == "workspace_shell"
    assert payload["learning_autopromote_enabled"] is False
    assert payload["plugin_discovery_enabled"] is False
    assert payload["channel_inventory_enabled"] is False
    assert payload["acp_inventory_enabled"] is False
