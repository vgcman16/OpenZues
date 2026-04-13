import asyncio
import codecs
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from openzues.app import create_app
from openzues.cli import (
    _append_watch_log,
    _emit_attention_queue_action,
    _emit_continue_action,
    _emit_gateway_capability,
    _emit_status,
    _watch_browser_verify,
    app,
)
from openzues.database import Database
from openzues.schemas import ControlChatMessageView, ControlChatResponse, MissionDraftView
from openzues.services.control_chat import ControlChatPlan
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


def test_status_json_reuses_gateway_contract_and_surfaces_queue_plan(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _bootstrap_cli_workspace(tmp_path, monkeypatch)

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
    assert payload["queue_plan"] is not None
    assert payload["queue_plan"]["signal_id"] is not None
    assert "Gateway Doctor says" in payload["queue_plan"]["reply"]
    assert cli_gateway == api_payload


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
    assert payload["screenshot_path"] == "C:\\temp\\watch.png"
    assert "OpenZues" in payload["snapshot_summary"]


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
    monkeypatch.setattr("openzues.cli._watch_browser_verify", fake_browser_verify)

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
    monkeypatch.setattr("openzues.cli._watch_browser_verify", fake_browser_verify)

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
        if key == ("--annotate", "screenshot"):
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

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0, result.stdout
    assert "missions:" in result.stdout
    assert "lanes:" in result.stdout
    assert "status:" in result.stdout
    assert "gateway:" in result.stdout
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
