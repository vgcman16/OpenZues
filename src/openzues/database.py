from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from openzues.services.session_keys import session_key_lookup_aliases

THREAD_EVENT_COMPACT_COMMAND_LIMIT = 4096
THREAD_EVENT_COMPACT_DELTA_LIMIT = 2048
THREAD_EVENT_COMPACT_TEXT_LIMIT = 2048
THREAD_EVENT_COMPACT_PROMPT_LIMIT = 1024
APPEND_EVENT_BUSY_TIMEOUT_SECONDS = 30.0
APPEND_EVENT_LOCK_RETRY_ATTEMPTS = 5
APPEND_EVENT_LOCK_RETRY_BASE_DELAY_SECONDS = 0.05
_GATEWAY_WAKE_REASON_PRIORITY = {
    "retry": 0,
    "interval": 1,
    "default": 2,
    "action": 3,
}


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_gateway_wake_reason(reason: str | None) -> str:
    trimmed = str(reason or "").strip()
    return trimmed or "wake"


def _resolve_gateway_wake_reason_priority(reason: str | None) -> int:
    normalized = _normalize_gateway_wake_reason(reason)
    if normalized == "retry":
        return _GATEWAY_WAKE_REASON_PRIORITY["retry"]
    if normalized == "interval":
        return _GATEWAY_WAKE_REASON_PRIORITY["interval"]
    if normalized == "manual" or normalized == "exec-event" or normalized.startswith("hook:"):
        return _GATEWAY_WAKE_REASON_PRIORITY["action"]
    return _GATEWAY_WAKE_REASON_PRIORITY["default"]


def _gateway_wake_target_matches(
    row: aiosqlite.Row,
    *,
    agent_id: str | None,
    session_key: str | None,
) -> bool:
    existing_agent_id = str(row["agent_id"]) if row["agent_id"] is not None else None
    existing_session_key = str(row["session_key"]) if row["session_key"] is not None else None
    return existing_agent_id == agent_id and existing_session_key == session_key


def _select_gateway_wake_row_winner(
    rows: Sequence[aiosqlite.Row],
) -> tuple[str, str | None, int]:
    winning_row = rows[0]
    winning_text = str(winning_row["text"])
    winning_reason = str(winning_row["reason"]) if winning_row["reason"] is not None else None
    winning_priority = _resolve_gateway_wake_reason_priority(winning_reason)
    winning_id = int(winning_row["id"])
    for row in rows[1:]:
        row_reason = str(row["reason"]) if row["reason"] is not None else None
        row_priority = _resolve_gateway_wake_reason_priority(row_reason)
        row_id = int(row["id"])
        if row_priority > winning_priority or (
            row_priority == winning_priority and row_id >= winning_id
        ):
            winning_row = row
            winning_text = str(row["text"])
            winning_reason = row_reason
            winning_priority = row_priority
            winning_id = row_id
    return winning_text, winning_reason, winning_priority


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _decode_json_list(value: Any) -> list[str]:
        try:
            decoded = json.loads(str(value or "[]"))
        except (TypeError, ValueError):
            return []
        if not isinstance(decoded, list):
            return []
        output: list[str] = []
        for item in decoded:
            text = str(item or "").strip()
            if text:
                output.append(text)
        return output

    @staticmethod
    def _decode_json_object(value: Any) -> dict[str, Any] | None:
        try:
            decoded = json.loads(str(value or "null"))
        except (TypeError, ValueError):
            return None
        return decoded if isinstance(decoded, dict) else None

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    transport TEXT NOT NULL,
                    command TEXT,
                    args TEXT,
                    websocket_url TEXT,
                    cwd TEXT,
                    auto_connect INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT,
                    role TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    api_key_hash TEXT,
                    api_key_preview TEXT,
                    api_key_issued_at TEXT,
                    api_key_last_used_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_operators_team_role
                    ON operators(team_id, role);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_operators_api_key_hash
                    ON operators(api_key_hash);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id INTEGER,
                    thread_id TEXT,
                    method TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_instance_thread
                    ON events(instance_id, thread_id, id DESC);
                CREATE TABLE IF NOT EXISTS control_chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    action_kind TEXT,
                    mission_id INTEGER,
                    opportunity_id TEXT,
                    target_label TEXT,
                    session_key TEXT,
                    model_provider TEXT,
                    model TEXT,
                    usage_json TEXT,
                    cost_json TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_control_chat_messages_created
                    ON control_chat_messages(id DESC);
                CREATE INDEX IF NOT EXISTS idx_control_chat_messages_session_key
                    ON control_chat_messages(session_key, id DESC);
                CREATE TABLE IF NOT EXISTS control_chat_compaction_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_key TEXT NOT NULL,
                    created_at_ms INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    archived_messages_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_control_chat_compaction_checkpoints_session_key
                    ON control_chat_compaction_checkpoints(session_key, created_at_ms DESC);
                CREATE TABLE IF NOT EXISTS attention_queue_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    signal_fingerprint TEXT NOT NULL,
                    signal_level TEXT NOT NULL,
                    mission_id INTEGER,
                    opportunity_id TEXT,
                    target_label TEXT,
                    action_kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_attention_queue_actions_signal
                    ON attention_queue_actions(signal_fingerprint, id DESC);
                CREATE INDEX IF NOT EXISTS idx_attention_queue_actions_created
                    ON attention_queue_actions(id DESC);
                CREATE TABLE IF NOT EXISTS gateway_wake_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT NOT NULL,
                    text TEXT NOT NULL,
                    reason TEXT,
                    agent_id TEXT,
                    session_key TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    claimed_at TEXT,
                    dispatched_at TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_gateway_wake_requests_status
                    ON gateway_wake_requests(status, id ASC);
                CREATE TABLE IF NOT EXISTS server_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id INTEGER NOT NULL,
                    request_id TEXT NOT NULL,
                    thread_id TEXT,
                    method TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    UNIQUE(instance_id, request_id)
                );
                CREATE TABLE IF NOT EXISTS gateway_node_pairing_requests (
                    request_id TEXT PRIMARY KEY,
                    node_id TEXT NOT NULL,
                    display_name TEXT,
                    platform TEXT,
                    version TEXT,
                    core_version TEXT,
                    ui_version TEXT,
                    device_family TEXT,
                    model_identifier TEXT,
                    caps_json TEXT NOT NULL DEFAULT '[]',
                    commands_json TEXT NOT NULL DEFAULT '[]',
                    remote_ip TEXT,
                    silent INTEGER NOT NULL DEFAULT 0,
                    requested_at_ms INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_gateway_node_pairing_requests_node
                    ON gateway_node_pairing_requests(node_id);
                CREATE TABLE IF NOT EXISTS gateway_node_paired_nodes (
                    node_id TEXT PRIMARY KEY,
                    token TEXT NOT NULL,
                    display_name TEXT,
                    platform TEXT,
                    version TEXT,
                    core_version TEXT,
                    ui_version TEXT,
                    device_family TEXT,
                    model_identifier TEXT,
                    caps_json TEXT NOT NULL DEFAULT '[]',
                    commands_json TEXT NOT NULL DEFAULT '[]',
                    permissions_json TEXT,
                    remote_ip TEXT,
                    created_at_ms INTEGER NOT NULL,
                    approved_at_ms INTEGER NOT NULL,
                    last_connected_at_ms INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gateway_node_device_tokens (
                    device_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    token TEXT NOT NULL,
                    scopes_json TEXT NOT NULL DEFAULT '[]',
                    created_at_ms INTEGER NOT NULL,
                    rotated_at_ms INTEGER,
                    revoked_at_ms INTEGER,
                    last_used_at_ms INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(device_id, role)
                );
                CREATE INDEX IF NOT EXISTS idx_gateway_node_device_tokens_device
                    ON gateway_node_device_tokens(device_id, role);
                CREATE TABLE IF NOT EXISTS gateway_agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    workspace TEXT NOT NULL,
                    model TEXT,
                    emoji TEXT,
                    avatar TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS playbooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    kind TEXT NOT NULL,
                    instance_id INTEGER,
                    cadence_minutes INTEGER,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    payload_json TEXT NOT NULL,
                    last_run_at TEXT,
                    last_status TEXT,
                    last_result_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_blueprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    summary TEXT,
                    project_id INTEGER,
                    instance_id INTEGER,
                    cadence_minutes INTEGER,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    payload_json TEXT NOT NULL,
                    last_launched_at TEXT,
                    last_status TEXT,
                    last_result_summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gateway_bootstrap (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    setup_mode TEXT NOT NULL DEFAULT 'local',
                    setup_flow TEXT NOT NULL DEFAULT 'quickstart',
                    route_binding_mode TEXT NOT NULL DEFAULT 'saved_lane',
                    preferred_instance_id INTEGER,
                    preferred_project_id INTEGER,
                    team_id INTEGER,
                    operator_id INTEGER,
                    task_blueprint_id INTEGER,
                    last_route_instance_id INTEGER,
                    last_route_resolved_at TEXT,
                    default_cwd TEXT,
                    bootstrap_roles_json TEXT NOT NULL DEFAULT '[]',
                    bootstrap_scopes_json TEXT NOT NULL DEFAULT '[]',
                    model TEXT NOT NULL,
                    max_turns INTEGER,
                    use_builtin_agents INTEGER NOT NULL DEFAULT 1,
                    run_verification INTEGER NOT NULL DEFAULT 1,
                    auto_commit INTEGER NOT NULL DEFAULT 0,
                    pause_on_approval INTEGER NOT NULL DEFAULT 1,
                    allow_auto_reflexes INTEGER NOT NULL DEFAULT 1,
                    auto_recover INTEGER NOT NULL DEFAULT 1,
                    auto_recover_limit INTEGER NOT NULL DEFAULT 2,
                    reflex_cooldown_seconds INTEGER NOT NULL DEFAULT 900,
                    allow_failover INTEGER NOT NULL DEFAULT 1,
                    toolsets_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS gateway_session_metadata (
                    session_key TEXT PRIMARY KEY,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS setup_footprint (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    footprint_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS setup_wizard_session (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    session_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS hermes_runtime_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    profile_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS notification_routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    target TEXT NOT NULL,
                    events_json TEXT NOT NULL,
                    conversation_target_json TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    secret_header_name TEXT,
                    secret_token TEXT,
                    vault_secret_id INTEGER,
                    last_delivery_at TEXT,
                    last_result TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbound_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route_id INTEGER,
                    route_name TEXT NOT NULL,
                    route_kind TEXT NOT NULL,
                    route_target TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    session_key TEXT,
                    conversation_target_json TEXT,
                    route_scope_json TEXT NOT NULL,
                    event_payload_json TEXT,
                    request_idempotency_key TEXT,
                    delivery_message_id TEXT,
                    message_summary TEXT NOT NULL,
                    test_delivery INTEGER NOT NULL DEFAULT 0,
                    delivery_state TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    last_attempt_at TEXT,
                    delivered_at TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS integrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    project_id INTEGER,
                    base_url TEXT,
                    auth_scheme TEXT NOT NULL,
                    vault_secret_id INTEGER,
                    secret_label TEXT,
                    secret_value TEXT,
                    notes TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS vault_secrets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    ciphertext TEXT NOT NULL,
                    preview TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS skill_pins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    prompt_hint TEXT NOT NULL,
                    source TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    instance_id INTEGER NOT NULL,
                    project_id INTEGER,
                    task_blueprint_id INTEGER,
                    thread_id TEXT,
                    session_key TEXT,
                    conversation_target_json TEXT,
                    cwd TEXT,
                    model TEXT NOT NULL,
                    reasoning_effort TEXT,
                    collaboration_mode TEXT,
                    max_turns INTEGER,
                    use_builtin_agents INTEGER NOT NULL DEFAULT 1,
                    run_verification INTEGER NOT NULL DEFAULT 1,
                    auto_commit INTEGER NOT NULL DEFAULT 1,
                    pause_on_approval INTEGER NOT NULL DEFAULT 1,
                    allow_auto_reflexes INTEGER NOT NULL DEFAULT 1,
                    auto_recover INTEGER NOT NULL DEFAULT 1,
                    auto_recover_limit INTEGER NOT NULL DEFAULT 2,
                    reflex_cooldown_seconds INTEGER NOT NULL DEFAULT 900,
                    allow_failover INTEGER NOT NULL DEFAULT 1,
                    swarm_state_json TEXT,
                    toolsets_json TEXT NOT NULL DEFAULT '[]',
                    in_progress INTEGER NOT NULL DEFAULT 0,
                    phase TEXT,
                    current_command TEXT,
                    command_count INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
                    last_commentary TEXT,
                    turns_started INTEGER NOT NULL DEFAULT 0,
                    turns_completed INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    last_turn_id TEXT,
                    last_error TEXT,
                    last_checkpoint TEXT,
                    last_reflex_kind TEXT,
                    last_reflex_at TEXT,
                    last_activity_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);
                CREATE INDEX IF NOT EXISTS idx_missions_thread
                    ON missions(instance_id, thread_id);
                CREATE TABLE IF NOT EXISTS mission_checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id INTEGER NOT NULL,
                    thread_id TEXT,
                    turn_id TEXT,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mission_checkpoints_mission
                    ON mission_checkpoints(mission_id, id DESC);
                CREATE TABLE IF NOT EXISTS lane_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id INTEGER NOT NULL,
                    snapshot_kind TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_lane_snapshots_instance
                    ON lane_snapshots(instance_id, id DESC);
                CREATE TABLE IF NOT EXISTS remote_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_id INTEGER NOT NULL,
                    operator_id INTEGER NOT NULL,
                    idempotency_key TEXT,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_ip TEXT,
                    user_agent TEXT,
                    target_kind TEXT,
                    target_id INTEGER,
                    target_label TEXT,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    requested_at TEXT NOT NULL,
                    resolved_at TEXT,
                    UNIQUE(operator_id, idempotency_key)
                );
                CREATE INDEX IF NOT EXISTS idx_remote_requests_requested
                    ON remote_requests(requested_at DESC, id DESC);
                CREATE INDEX IF NOT EXISTS idx_remote_requests_team
                    ON remote_requests(team_id, id DESC);
                """
            )
            await self._ensure_column(db, "missions", "phase", "TEXT")
            await self._ensure_column(db, "missions", "current_command", "TEXT")
            await self._ensure_column(db, "missions", "command_count", "INTEGER NOT NULL DEFAULT 0")
            await self._ensure_column(db, "missions", "total_tokens", "INTEGER NOT NULL DEFAULT 0")
            await self._ensure_column(db, "missions", "output_tokens", "INTEGER NOT NULL DEFAULT 0")
            await self._ensure_column(
                db, "missions", "reasoning_tokens", "INTEGER NOT NULL DEFAULT 0"
            )
            await self._ensure_column(db, "missions", "last_commentary", "TEXT")
            await self._ensure_column(
                db, "missions", "allow_auto_reflexes", "INTEGER NOT NULL DEFAULT 1"
            )
            await self._ensure_column(db, "missions", "auto_recover", "INTEGER NOT NULL DEFAULT 1")
            await self._ensure_column(
                db, "missions", "auto_recover_limit", "INTEGER NOT NULL DEFAULT 2"
            )
            await self._ensure_column(
                db, "missions", "reflex_cooldown_seconds", "INTEGER NOT NULL DEFAULT 900"
            )
            await self._ensure_column(
                db, "missions", "allow_failover", "INTEGER NOT NULL DEFAULT 1"
            )
            await self._ensure_column(db, "missions", "swarm_state_json", "TEXT")
            await self._ensure_column(db, "missions", "last_reflex_kind", "TEXT")
            await self._ensure_column(db, "missions", "last_reflex_at", "TEXT")
            await self._ensure_column(db, "missions", "task_blueprint_id", "INTEGER")
            await self._ensure_column(db, "missions", "conversation_target_json", "TEXT")
            await self._ensure_column(db, "playbooks", "cadence_minutes", "INTEGER")
            await self._ensure_column(db, "playbooks", "enabled", "INTEGER NOT NULL DEFAULT 1")
            await self._ensure_column(db, "playbooks", "last_run_at", "TEXT")
            await self._ensure_column(db, "playbooks", "last_status", "TEXT")
            await self._ensure_column(db, "playbooks", "last_result_summary", "TEXT")
            await self._ensure_column(
                db, "gateway_bootstrap", "setup_mode", "TEXT NOT NULL DEFAULT 'local'"
            )
            await self._ensure_column(
                db,
                "gateway_bootstrap",
                "setup_flow",
                "TEXT NOT NULL DEFAULT 'quickstart'",
            )
            await self._ensure_column(
                db,
                "gateway_bootstrap",
                "route_binding_mode",
                "TEXT NOT NULL DEFAULT 'saved_lane'",
            )
            await self._ensure_column(db, "gateway_bootstrap", "last_route_instance_id", "INTEGER")
            await self._ensure_column(db, "gateway_bootstrap", "last_route_resolved_at", "TEXT")
            await self._ensure_column(
                db,
                "gateway_bootstrap",
                "bootstrap_roles_json",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            await self._ensure_column(
                db,
                "gateway_bootstrap",
                "bootstrap_scopes_json",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            await self._ensure_column(
                db, "gateway_bootstrap", "toolsets_json", "TEXT NOT NULL DEFAULT '[]'"
            )
            await self._ensure_column(db, "notification_routes", "vault_secret_id", "INTEGER")
            await self._ensure_column(db, "notification_routes", "conversation_target_json", "TEXT")
            await self._ensure_column(db, "outbound_deliveries", "event_payload_json", "TEXT")
            await self._ensure_column(
                db, "outbound_deliveries", "request_idempotency_key", "TEXT"
            )
            await self._ensure_column(db, "outbound_deliveries", "delivery_message_id", "TEXT")
            await self._ensure_column(db, "integrations", "vault_secret_id", "INTEGER")
            await self._ensure_column(db, "gateway_wake_requests", "reason", "TEXT")
            await self._ensure_column(db, "gateway_wake_requests", "agent_id", "TEXT")
            await self._ensure_column(db, "gateway_wake_requests", "session_key", "TEXT")
            await self._ensure_column(db, "control_chat_messages", "session_key", "TEXT")
            await self._ensure_column(db, "control_chat_messages", "model_provider", "TEXT")
            await self._ensure_column(db, "control_chat_messages", "model", "TEXT")
            await self._ensure_column(db, "control_chat_messages", "usage_json", "TEXT")
            await self._ensure_column(db, "control_chat_messages", "cost_json", "TEXT")
            await self._ensure_column(db, "missions", "session_key", "TEXT")
            await self._ensure_column(db, "missions", "conversation_target_json", "TEXT")
            await self._ensure_column(db, "missions", "toolsets_json", "TEXT NOT NULL DEFAULT '[]'")
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_missions_task
                ON missions(task_blueprint_id, id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_missions_session_key
                ON missions(session_key, id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_control_chat_messages_session_key
                ON control_chat_messages(session_key, id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_notification_routes_vault_secret
                ON notification_routes(vault_secret_id)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbound_deliveries_created
                ON outbound_deliveries(id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbound_deliveries_route
                ON outbound_deliveries(route_id, id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbound_deliveries_session
                ON outbound_deliveries(session_key, id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_outbound_deliveries_idempotency
                ON outbound_deliveries(event_type, request_idempotency_key, id DESC)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_integrations_vault_secret
                ON integrations(vault_secret_id)
                """
            )
            await db.commit()

    async def _ensure_column(
        self,
        db: aiosqlite.Connection,
        table_name: str,
        column_name: str,
        definition: str,
    ) -> None:
        db.row_factory = aiosqlite.Row
        rows = await db.execute_fetchall(f"PRAGMA table_info({table_name})")
        existing = {str(row["name"]) for row in rows}
        if column_name in existing:
            return
        await db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    async def list_instances(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM instances ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def create_instance(
        self,
        *,
        name: str,
        transport: str,
        command: str | None,
        args: str | None,
        websocket_url: str | None,
        cwd: str | None,
        auto_connect: bool,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO instances (
                    name,
                    transport,
                    command,
                    args,
                    websocket_url,
                    cwd,
                    auto_connect,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, transport, command, args, websocket_url, cwd, int(auto_connect), now, now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def get_instance(self, instance_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM instances WHERE id = ?", (instance_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_instance_auto_connect(self, instance_id: int, *, auto_connect: bool) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE instances
                SET auto_connect = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(auto_connect), now, instance_id),
            )
            await db.commit()

    @staticmethod
    def _gateway_node_pairing_request_row(row: aiosqlite.Row | dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        return {
            "request_id": str(payload["request_id"]),
            "node_id": str(payload["node_id"]),
            "display_name": payload["display_name"],
            "platform": payload["platform"],
            "version": payload["version"],
            "core_version": payload["core_version"],
            "ui_version": payload["ui_version"],
            "device_family": payload["device_family"],
            "model_identifier": payload["model_identifier"],
            "caps": Database._decode_json_list(payload.get("caps_json")),
            "commands": Database._decode_json_list(payload.get("commands_json")),
            "remote_ip": payload["remote_ip"],
            "silent": bool(payload["silent"]),
            "requested_at_ms": int(payload["requested_at_ms"]),
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
        }

    async def list_gateway_node_pairing_requests(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM gateway_node_pairing_requests
                ORDER BY requested_at_ms DESC, request_id ASC
                """
            )
            return [self._gateway_node_pairing_request_row(row) for row in rows]

    async def get_gateway_node_pairing_request(self, request_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM gateway_node_pairing_requests WHERE request_id = ?",
                (request_id,),
            )
            row = await cursor.fetchone()
            return self._gateway_node_pairing_request_row(row) if row else None

    async def upsert_gateway_node_pairing_request(
        self,
        *,
        node_id: str,
        display_name: str | None,
        platform: str | None,
        version: str | None,
        core_version: str | None,
        ui_version: str | None,
        device_family: str | None,
        model_identifier: str | None,
        caps: Sequence[str],
        commands: Sequence[str],
        remote_ip: str | None,
        silent: bool | None,
        requested_at_ms: int,
        request_id: str,
    ) -> tuple[dict[str, Any], bool]:
        now = utcnow()
        caps_json = json.dumps(list(caps))
        commands_json = json.dumps(list(commands))
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            existing_cursor = await db.execute(
                """
                SELECT *
                FROM gateway_node_pairing_requests
                WHERE node_id = ?
                ORDER BY requested_at_ms DESC, request_id ASC
                LIMIT 1
                """,
                (node_id,),
            )
            existing = await existing_cursor.fetchone()
            created = existing is None
            persisted_request_id = request_id if existing is None else str(existing["request_id"])
            if created:
                await db.execute(
                    """
                    INSERT INTO gateway_node_pairing_requests (
                        request_id,
                        node_id,
                        display_name,
                        platform,
                        version,
                        core_version,
                        ui_version,
                        device_family,
                        model_identifier,
                        caps_json,
                        commands_json,
                        remote_ip,
                        silent,
                        requested_at_ms,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        persisted_request_id,
                        node_id,
                        display_name,
                        platform,
                        version,
                        core_version,
                        ui_version,
                        device_family,
                        model_identifier,
                        caps_json,
                        commands_json,
                        remote_ip,
                        int(bool(silent)),
                        requested_at_ms,
                        now,
                        now,
                    ),
                )
            else:
                await db.execute(
                    """
                    UPDATE gateway_node_pairing_requests
                    SET display_name = ?,
                        platform = ?,
                        version = ?,
                        core_version = ?,
                        ui_version = ?,
                        device_family = ?,
                        model_identifier = ?,
                        caps_json = ?,
                        commands_json = ?,
                        remote_ip = ?,
                        silent = ?,
                        requested_at_ms = ?,
                        updated_at = ?
                    WHERE request_id = ?
                    """,
                    (
                        display_name,
                        platform,
                        version,
                        core_version,
                        ui_version,
                        device_family,
                        model_identifier,
                        caps_json,
                        commands_json,
                        remote_ip,
                        int(bool(silent)),
                        requested_at_ms,
                        now,
                        persisted_request_id,
                    ),
                )
            await db.commit()
            stored_cursor = await db.execute(
                "SELECT * FROM gateway_node_pairing_requests WHERE request_id = ?",
                (persisted_request_id,),
            )
            stored = await stored_cursor.fetchone()
            if stored is None:
                raise RuntimeError("Failed to persist gateway node pairing request.")
            return self._gateway_node_pairing_request_row(stored), created

    async def delete_gateway_node_pairing_request(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            existing_cursor = await db.execute(
                "SELECT * FROM gateway_node_pairing_requests WHERE request_id = ?",
                (request_id,),
            )
            existing = await existing_cursor.fetchone()
            if existing is None:
                return None
            await db.execute(
                "DELETE FROM gateway_node_pairing_requests WHERE request_id = ?",
                (request_id,),
            )
            await db.commit()
            return self._gateway_node_pairing_request_row(existing)

    @staticmethod
    def _gateway_node_paired_node_row(row: aiosqlite.Row | dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        return {
            "node_id": str(payload["node_id"]),
            "token": str(payload["token"]),
            "display_name": payload["display_name"],
            "platform": payload["platform"],
            "version": payload["version"],
            "core_version": payload["core_version"],
            "ui_version": payload["ui_version"],
            "device_family": payload["device_family"],
            "model_identifier": payload["model_identifier"],
            "caps": Database._decode_json_list(payload.get("caps_json")),
            "commands": Database._decode_json_list(payload.get("commands_json")),
            "permissions": Database._decode_json_object(payload.get("permissions_json")),
            "remote_ip": payload["remote_ip"],
            "created_at_ms": int(payload["created_at_ms"]),
            "approved_at_ms": int(payload["approved_at_ms"]),
            "last_connected_at_ms": (
                int(payload["last_connected_at_ms"])
                if payload["last_connected_at_ms"] is not None
                else None
            ),
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
        }

    async def list_gateway_node_paired_nodes(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM gateway_node_paired_nodes
                ORDER BY approved_at_ms DESC, node_id ASC
                """
            )
            return [self._gateway_node_paired_node_row(row) for row in rows]

    async def get_gateway_node_paired_node(self, node_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM gateway_node_paired_nodes WHERE node_id = ?",
                (node_id,),
            )
            row = await cursor.fetchone()
            return self._gateway_node_paired_node_row(row) if row else None

    async def upsert_gateway_node_paired_node(
        self,
        *,
        node_id: str,
        token: str,
        display_name: str | None,
        platform: str | None,
        version: str | None,
        core_version: str | None,
        ui_version: str | None,
        device_family: str | None,
        model_identifier: str | None,
        caps: Sequence[str],
        commands: Sequence[str],
        permissions: dict[str, bool] | None,
        remote_ip: str | None,
        created_at_ms: int,
        approved_at_ms: int,
        last_connected_at_ms: int | None,
    ) -> dict[str, Any]:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO gateway_node_paired_nodes (
                    node_id,
                    token,
                    display_name,
                    platform,
                    version,
                    core_version,
                    ui_version,
                    device_family,
                    model_identifier,
                    caps_json,
                    commands_json,
                    permissions_json,
                    remote_ip,
                    created_at_ms,
                    approved_at_ms,
                    last_connected_at_ms,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    token = excluded.token,
                    display_name = excluded.display_name,
                    platform = excluded.platform,
                    version = excluded.version,
                    core_version = excluded.core_version,
                    ui_version = excluded.ui_version,
                    device_family = excluded.device_family,
                    model_identifier = excluded.model_identifier,
                    caps_json = excluded.caps_json,
                    commands_json = excluded.commands_json,
                    permissions_json = excluded.permissions_json,
                    remote_ip = excluded.remote_ip,
                    created_at_ms = excluded.created_at_ms,
                    approved_at_ms = excluded.approved_at_ms,
                    last_connected_at_ms = excluded.last_connected_at_ms,
                    updated_at = excluded.updated_at
                """,
                (
                    node_id,
                    token,
                    display_name,
                    platform,
                    version,
                    core_version,
                    ui_version,
                    device_family,
                    model_identifier,
                    json.dumps(list(caps)),
                    json.dumps(list(commands)),
                    json.dumps(permissions) if permissions is not None else None,
                    remote_ip,
                    created_at_ms,
                    approved_at_ms,
                    last_connected_at_ms,
                    now,
                    now,
                ),
            )
            await db.commit()
        stored = await self.get_gateway_node_paired_node(node_id)
        if stored is None:
            raise RuntimeError("Failed to persist gateway node paired node.")
        return stored

    async def delete_gateway_node_paired_node(self, node_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM gateway_node_paired_nodes WHERE node_id = ?",
                (node_id,),
            )
            existing = await cursor.fetchone()
            if existing is None:
                return None
            await db.execute(
                "DELETE FROM gateway_node_paired_nodes WHERE node_id = ?",
                (node_id,),
            )
            await db.execute(
                "DELETE FROM gateway_node_device_tokens WHERE device_id = ?",
                (node_id,),
            )
            await db.commit()
            return self._gateway_node_paired_node_row(existing)

    async def update_gateway_node_paired_node_display_name(
        self,
        node_id: str,
        display_name: str,
    ) -> dict[str, Any] | None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM gateway_node_paired_nodes WHERE node_id = ?",
                (node_id,),
            )
            existing = await cursor.fetchone()
            if existing is None:
                return None
            await db.execute(
                """
                UPDATE gateway_node_paired_nodes
                SET display_name = ?, updated_at = ?
                WHERE node_id = ?
                """,
                (display_name, now, node_id),
            )
            await db.commit()
        return await self.get_gateway_node_paired_node(node_id)

    @staticmethod
    def _gateway_node_device_token_row(row: aiosqlite.Row | dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        return {
            "device_id": str(payload["device_id"]),
            "role": str(payload["role"]),
            "token": str(payload["token"]),
            "scopes": Database._decode_json_list(payload.get("scopes_json")),
            "created_at_ms": int(payload["created_at_ms"]),
            "rotated_at_ms": (
                int(payload["rotated_at_ms"]) if payload["rotated_at_ms"] is not None else None
            ),
            "revoked_at_ms": (
                int(payload["revoked_at_ms"]) if payload["revoked_at_ms"] is not None else None
            ),
            "last_used_at_ms": (
                int(payload["last_used_at_ms"])
                if payload["last_used_at_ms"] is not None
                else None
            ),
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
        }

    async def list_gateway_node_device_tokens(
        self,
        device_id: str,
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM gateway_node_device_tokens
                WHERE device_id = ?
                ORDER BY role ASC
                """,
                (device_id,),
            )
            return [self._gateway_node_device_token_row(row) for row in rows]

    async def get_gateway_node_device_token(
        self,
        device_id: str,
        role: str,
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM gateway_node_device_tokens
                WHERE device_id = ? AND role = ?
                """,
                (device_id, role),
            )
            row = await cursor.fetchone()
            return self._gateway_node_device_token_row(row) if row else None

    async def upsert_gateway_node_device_token(
        self,
        *,
        device_id: str,
        role: str,
        token: str,
        scopes: Sequence[str],
        created_at_ms: int,
        rotated_at_ms: int | None,
        revoked_at_ms: int | None,
        last_used_at_ms: int | None,
    ) -> dict[str, Any]:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO gateway_node_device_tokens (
                    device_id,
                    role,
                    token,
                    scopes_json,
                    created_at_ms,
                    rotated_at_ms,
                    revoked_at_ms,
                    last_used_at_ms,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id, role) DO UPDATE SET
                    token = excluded.token,
                    scopes_json = excluded.scopes_json,
                    created_at_ms = excluded.created_at_ms,
                    rotated_at_ms = excluded.rotated_at_ms,
                    revoked_at_ms = excluded.revoked_at_ms,
                    last_used_at_ms = excluded.last_used_at_ms,
                    updated_at = excluded.updated_at
                """,
                (
                    device_id,
                    role,
                    token,
                    json.dumps(list(scopes)),
                    created_at_ms,
                    rotated_at_ms,
                    revoked_at_ms,
                    last_used_at_ms,
                    now,
                    now,
                ),
            )
            await db.commit()
        stored = await self.get_gateway_node_device_token(device_id, role)
        if stored is None:
            raise RuntimeError("Failed to persist gateway node device token.")
        return stored

    async def revoke_gateway_node_device_token(
        self,
        *,
        device_id: str,
        role: str,
        revoked_at_ms: int,
    ) -> dict[str, Any] | None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM gateway_node_device_tokens
                WHERE device_id = ? AND role = ?
                """,
                (device_id, role),
            )
            existing = await cursor.fetchone()
            if existing is None:
                return None
            await db.execute(
                """
                UPDATE gateway_node_device_tokens
                SET revoked_at_ms = ?,
                    updated_at = ?
                WHERE device_id = ? AND role = ?
                """,
                (revoked_at_ms, now, device_id, role),
            )
            await db.commit()
        return await self.get_gateway_node_device_token(device_id, role)

    @staticmethod
    def _gateway_agent_row(row: aiosqlite.Row | dict[str, Any]) -> dict[str, Any]:
        payload = dict(row)
        return {
            "agent_id": str(payload["agent_id"]),
            "name": str(payload["name"]),
            "workspace": str(payload["workspace"]),
            "model": payload["model"],
            "emoji": payload["emoji"],
            "avatar": payload["avatar"],
            "created_at": payload["created_at"],
            "updated_at": payload["updated_at"],
        }

    async def list_gateway_agents(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM gateway_agents
                ORDER BY agent_id ASC
                """
            )
            return [self._gateway_agent_row(row) for row in rows]

    async def get_gateway_agent(self, agent_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM gateway_agents WHERE agent_id = ?",
                (agent_id,),
            )
            row = await cursor.fetchone()
            return self._gateway_agent_row(row) if row else None

    async def create_gateway_agent(
        self,
        *,
        agent_id: str,
        name: str,
        workspace: str,
        model: str | None,
        emoji: str | None,
        avatar: str | None,
    ) -> dict[str, Any]:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO gateway_agents (
                        agent_id,
                        name,
                        workspace,
                        model,
                        emoji,
                        avatar,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (agent_id, name, workspace, model, emoji, avatar, now, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f'agent "{agent_id}" already exists') from exc
            await db.commit()
        stored = await self.get_gateway_agent(agent_id)
        if stored is None:
            raise RuntimeError("Failed to persist gateway agent.")
        return stored

    async def update_gateway_agent(
        self,
        *,
        agent_id: str,
        name: str | None,
        workspace: str | None,
        model: str | None,
        emoji: str | None,
        avatar: str | None,
    ) -> dict[str, Any] | None:
        existing = await self.get_gateway_agent(agent_id)
        if existing is None:
            return None
        now = utcnow()
        next_name = name if name is not None else str(existing["name"])
        next_workspace = workspace if workspace is not None else str(existing["workspace"])
        next_model = model if model is not None else existing.get("model")
        next_emoji = emoji if emoji is not None else existing.get("emoji")
        next_avatar = avatar if avatar is not None else existing.get("avatar")
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE gateway_agents
                SET name = ?,
                    workspace = ?,
                    model = ?,
                    emoji = ?,
                    avatar = ?,
                    updated_at = ?
                WHERE agent_id = ?
                """,
                (
                    next_name,
                    next_workspace,
                    next_model,
                    next_emoji,
                    next_avatar,
                    now,
                    agent_id,
                ),
            )
            await db.commit()
        return await self.get_gateway_agent(agent_id)

    async def delete_gateway_agent(self, agent_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM gateway_agents WHERE agent_id = ?",
                (agent_id,),
            )
            existing = await cursor.fetchone()
            if existing is None:
                return None
            await db.execute("DELETE FROM gateway_agents WHERE agent_id = ?", (agent_id,))
            await db.commit()
            return self._gateway_agent_row(existing)

    async def delete_instance(self, instance_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM server_requests WHERE instance_id = ?", (instance_id,))
            await db.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
            await db.commit()

    async def list_projects(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM projects ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def get_project(self, project_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete_project(self, project_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            await db.commit()

    async def list_teams(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM teams ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def get_team(self, team_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM teams WHERE id = ?", (team_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_team(
        self,
        *,
        name: str,
        slug: str,
        description: str | None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO teams (
                    name,
                    slug,
                    description,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, slug, description, now, now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_team(self, team_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [team_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE teams SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def delete_team(self, team_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
            await db.commit()

    async def list_operators(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM operators ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def get_operator(self, operator_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM operators WHERE id = ?", (operator_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_operator_by_api_key_hash(
        self,
        api_key_hash: str,
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM operators WHERE api_key_hash = ?",
                (api_key_hash,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_operator(
        self,
        *,
        team_id: int,
        name: str,
        email: str | None,
        role: str,
        enabled: bool,
        api_key_hash: str | None,
        api_key_preview: str | None,
        api_key_issued_at: str | None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO operators (
                    team_id,
                    name,
                    email,
                    role,
                    enabled,
                    api_key_hash,
                    api_key_preview,
                    api_key_issued_at,
                    api_key_last_used_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)
                """,
                (
                    team_id,
                    name,
                    email,
                    role,
                    int(enabled),
                    api_key_hash,
                    api_key_preview,
                    api_key_issued_at,
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_operator(self, operator_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [operator_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE operators SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def delete_operator(self, operator_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM operators WHERE id = ?", (operator_id,))
            await db.commit()

    async def list_playbooks(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM playbooks ORDER BY id ASC")
            output = []
            for row in rows:
                item = dict(row)
                payload = json.loads(item.pop("payload_json"))
                output.append({**item, **payload})
            return output

    async def get_playbook(self, playbook_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM playbooks WHERE id = ?", (playbook_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            payload = json.loads(item.pop("payload_json"))
            return {**item, **payload}

    async def create_project(self, *, path: str, label: str) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT OR IGNORE INTO projects (path, label, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (path, label, now, now),
            )
            await db.commit()
            if cursor.lastrowid:
                return int(cursor.lastrowid)
            cursor = await db.execute("SELECT id FROM projects WHERE path = ?", (path,))
            row = await cursor.fetchone()
            assert row is not None
            return int(row[0])

    async def create_playbook(
        self,
        *,
        name: str,
        description: str | None,
        kind: str,
        instance_id: int | None,
        cadence_minutes: int | None,
        enabled: bool,
        payload: dict[str, Any],
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO playbooks (
                    name,
                    description,
                    kind,
                    instance_id,
                    cadence_minutes,
                    enabled,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    kind,
                    instance_id,
                    cadence_minutes,
                    int(enabled),
                    json.dumps(payload),
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_playbook(self, playbook_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [playbook_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE playbooks SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def list_task_blueprints(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM task_blueprints ORDER BY id ASC")
            output = []
            for row in rows:
                item = dict(row)
                payload = json.loads(item.pop("payload_json"))
                output.append({**payload, **item})
            return output

    async def list_task_blueprint_records(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM task_blueprints ORDER BY id ASC")
            output = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                output.append(item)
            return output

    async def get_task_blueprint(self, task_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM task_blueprints WHERE id = ?",
                (task_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            payload = json.loads(item.pop("payload_json"))
            return {**payload, **item}

    async def create_task_blueprint(
        self,
        *,
        name: str,
        summary: str | None,
        project_id: int | None,
        instance_id: int | None,
        cadence_minutes: int | None,
        enabled: bool,
        payload: dict[str, Any],
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO task_blueprints (
                    name,
                    summary,
                    project_id,
                    instance_id,
                    cadence_minutes,
                    enabled,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    summary,
                    project_id,
                    instance_id,
                    cadence_minutes,
                    int(enabled),
                    json.dumps(payload),
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_task_blueprint(self, task_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [task_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE task_blueprints SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def update_task_blueprint_payload(self, task_id: int, **payload_fields: Any) -> None:
        if not payload_fields:
            return
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT payload_json FROM task_blueprints WHERE id = ?",
                (task_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                raise ValueError(f"Unknown task blueprint {task_id}")
            payload = json.loads(str(row["payload_json"]) or "{}")
            payload.update(payload_fields)
            await db.execute(
                """
                UPDATE task_blueprints
                SET payload_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(payload), utcnow(), task_id),
            )
            await db.commit()

    async def delete_task_blueprint(self, task_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM task_blueprints WHERE id = ?", (task_id,))
            await db.commit()

    async def get_gateway_bootstrap(self) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM gateway_bootstrap WHERE id = 1")
            try:
                row = await cursor.fetchone()
            finally:
                await cursor.close()
            if row is None:
                return None
            item = dict(row)
            item["bootstrap_roles"] = self._decode_json_list(
                item.pop("bootstrap_roles_json", "[]")
            )
            item["bootstrap_scopes"] = self._decode_json_list(
                item.pop("bootstrap_scopes_json", "[]")
            )
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            return item

    async def clear_gateway_bootstrap(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM gateway_bootstrap WHERE id = 1")
            await db.commit()

    async def upsert_gateway_bootstrap(
        self,
        *,
        setup_mode: str,
        setup_flow: str,
        route_binding_mode: str = "saved_lane",
        preferred_instance_id: int | None,
        preferred_project_id: int | None,
        team_id: int | None,
        operator_id: int | None,
        task_blueprint_id: int | None,
        last_route_instance_id: int | None = None,
        last_route_resolved_at: str | None = None,
        default_cwd: str | None,
        bootstrap_roles: list[str] | None = None,
        bootstrap_scopes: list[str] | None = None,
        model: str,
        max_turns: int | None,
        use_builtin_agents: bool,
        run_verification: bool,
        auto_commit: bool,
        pause_on_approval: bool,
        allow_auto_reflexes: bool,
        auto_recover: bool,
        auto_recover_limit: int,
        reflex_cooldown_seconds: int,
        allow_failover: bool,
        toolsets: list[str] | None = None,
    ) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO gateway_bootstrap (
                    id,
                    setup_mode,
                    setup_flow,
                    route_binding_mode,
                    preferred_instance_id,
                    preferred_project_id,
                    team_id,
                    operator_id,
                    task_blueprint_id,
                    last_route_instance_id,
                    last_route_resolved_at,
                    default_cwd,
                    bootstrap_roles_json,
                    bootstrap_scopes_json,
                    model,
                    max_turns,
                    use_builtin_agents,
                    run_verification,
                    auto_commit,
                    pause_on_approval,
                    allow_auto_reflexes,
                    auto_recover,
                    auto_recover_limit,
                    reflex_cooldown_seconds,
                    allow_failover,
                    toolsets_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(id) DO UPDATE SET
                    setup_mode = excluded.setup_mode,
                    setup_flow = excluded.setup_flow,
                    route_binding_mode = excluded.route_binding_mode,
                    preferred_instance_id = excluded.preferred_instance_id,
                    preferred_project_id = excluded.preferred_project_id,
                    team_id = excluded.team_id,
                    operator_id = excluded.operator_id,
                    task_blueprint_id = excluded.task_blueprint_id,
                    last_route_instance_id = excluded.last_route_instance_id,
                    last_route_resolved_at = excluded.last_route_resolved_at,
                    default_cwd = excluded.default_cwd,
                    bootstrap_roles_json = excluded.bootstrap_roles_json,
                    bootstrap_scopes_json = excluded.bootstrap_scopes_json,
                    model = excluded.model,
                    max_turns = excluded.max_turns,
                    use_builtin_agents = excluded.use_builtin_agents,
                    run_verification = excluded.run_verification,
                    auto_commit = excluded.auto_commit,
                    pause_on_approval = excluded.pause_on_approval,
                    allow_auto_reflexes = excluded.allow_auto_reflexes,
                    auto_recover = excluded.auto_recover,
                    auto_recover_limit = excluded.auto_recover_limit,
                    reflex_cooldown_seconds = excluded.reflex_cooldown_seconds,
                    allow_failover = excluded.allow_failover,
                    toolsets_json = excluded.toolsets_json,
                    updated_at = excluded.updated_at
                """,
                (
                    1,
                    setup_mode,
                    setup_flow,
                    route_binding_mode,
                    preferred_instance_id,
                    preferred_project_id,
                    team_id,
                    operator_id,
                    task_blueprint_id,
                    last_route_instance_id,
                    last_route_resolved_at,
                    default_cwd,
                    json.dumps(bootstrap_roles or []),
                    json.dumps(bootstrap_scopes or []),
                    model,
                    max_turns,
                    int(use_builtin_agents),
                    int(run_verification),
                    int(auto_commit),
                    int(pause_on_approval),
                    int(allow_auto_reflexes),
                    int(auto_recover),
                    auto_recover_limit,
                    reflex_cooldown_seconds,
                    int(allow_failover),
                    json.dumps(toolsets or []),
                    now,
                    now,
                ),
            )
            await db.commit()

    async def update_gateway_bootstrap_route_state(
        self,
        *,
        last_route_instance_id: int | None,
        last_route_resolved_at: str | None,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE gateway_bootstrap
                SET last_route_instance_id = ?, last_route_resolved_at = ?, updated_at = ?
                WHERE id = 1
                """,
                (last_route_instance_id, last_route_resolved_at, utcnow()),
            )
            await db.commit()

    async def get_gateway_session_metadata(self, session_key: str) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return None
        placeholders = ", ".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT *
                FROM gateway_session_metadata
                WHERE LOWER(TRIM(session_key)) IN ({placeholders})
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                aliases,
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["metadata"] = self._decode_json_object(item.pop("metadata_json", "{}")) or {}
            return item

    async def list_gateway_session_metadata_rows(
        self,
        *,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        query = """
            SELECT *
            FROM gateway_session_metadata
            ORDER BY updated_at DESC
        """
        params: tuple[object, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(query, params)
            items: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["metadata"] = self._decode_json_object(item.pop("metadata_json", "{}")) or {}
                items.append(item)
            return items

    async def upsert_gateway_session_metadata(
        self,
        *,
        session_key: str,
        metadata: dict[str, Any],
    ) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO gateway_session_metadata (
                    session_key,
                    metadata_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_key) DO UPDATE SET
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (session_key, json.dumps(metadata), now, now),
            )
            await db.commit()

    async def delete_gateway_session_metadata(self, session_key: str) -> None:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return
        placeholders = ", ".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                (
                    "DELETE FROM gateway_session_metadata "
                    f"WHERE LOWER(TRIM(session_key)) IN ({placeholders})"
                ),
                aliases,
            )
            await db.commit()

    async def get_setup_footprint(self) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM setup_footprint WHERE id = 1")
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["footprint"] = json.loads(item.pop("footprint_json"))
            return item

    async def upsert_setup_footprint(self, footprint: dict[str, Any]) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO setup_footprint (
                    id,
                    footprint_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    footprint_json = excluded.footprint_json,
                    updated_at = excluded.updated_at
                """,
                (1, json.dumps(footprint), now, now),
            )
            await db.commit()

    async def clear_setup_footprint(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM setup_footprint WHERE id = 1")
            await db.commit()

    async def get_setup_wizard_session(self) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM setup_wizard_session WHERE id = 1")
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["session"] = json.loads(item.pop("session_json"))
            return item

    async def upsert_setup_wizard_session(self, session: dict[str, Any]) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO setup_wizard_session (
                    id,
                    session_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    session_json = excluded.session_json,
                    updated_at = excluded.updated_at
                """,
                (1, json.dumps(session), now, now),
            )
            await db.commit()

    async def clear_setup_wizard_session(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM setup_wizard_session WHERE id = 1")
            await db.commit()

    async def get_hermes_runtime_profile(self) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM hermes_runtime_profile WHERE id = 1")
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["profile"] = json.loads(item.pop("profile_json"))
            return item

    async def upsert_hermes_runtime_profile(self, profile: dict[str, Any]) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO hermes_runtime_profile (
                    id,
                    profile_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (1, json.dumps(profile), now, now),
            )
            await db.commit()

    async def list_notification_routes(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM notification_routes ORDER BY id ASC")
            try:
                rows = await cursor.fetchall()
                output = []
                for row in rows:
                    item = dict(row)
                    item["events"] = json.loads(item.pop("events_json"))
                    conversation_target = item.pop("conversation_target_json", None)
                    item["conversation_target"] = (
                        json.loads(conversation_target) if conversation_target else None
                    )
                    output.append(item)
                return output
            finally:
                await cursor.close()

    async def create_notification_route(
        self,
        *,
        name: str,
        kind: str,
        target: str,
        events: list[str],
        conversation_target: dict[str, Any] | None = None,
        enabled: bool,
        secret_header_name: str | None,
        secret_token: str | None,
        vault_secret_id: int | None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO notification_routes (
                    name,
                    kind,
                    target,
                    events_json,
                    conversation_target_json,
                    enabled,
                    secret_header_name,
                    secret_token,
                    vault_secret_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    kind,
                    target,
                    json.dumps(events),
                    json.dumps(conversation_target) if conversation_target is not None else None,
                    int(enabled),
                    secret_header_name,
                    secret_token,
                    vault_secret_id,
                    now,
                    now,
                ),
            )
            try:
                await db.commit()
                assert cursor.lastrowid is not None
                return int(cursor.lastrowid)
            finally:
                await cursor.close()

    async def update_notification_route(self, route_id: int, **fields: Any) -> None:
        if "events" in fields:
            fields["events_json"] = json.dumps(fields.pop("events"))
        if "conversation_target" in fields:
            conversation_target = fields.pop("conversation_target")
            fields["conversation_target_json"] = (
                json.dumps(conversation_target) if conversation_target is not None else None
            )
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [route_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE notification_routes SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def delete_notification_route(self, route_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM notification_routes WHERE id = ?", (route_id,))
            await db.commit()

    def _decode_outbound_delivery_row(self, row: aiosqlite.Row | dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        item["conversation_target"] = self._decode_json_object(
            item.pop("conversation_target_json", None)
        )
        item["route_scope"] = self._decode_json_object(item.pop("route_scope_json", None))
        item["event_payload"] = self._decode_json_object(item.pop("event_payload_json", None))
        return item

    async def list_outbound_deliveries(
        self,
        *,
        limit: int | None = 25,
        states: list[str] | None = None,
        newest_first: bool = True,
    ) -> list[dict[str, Any]]:
        where = ""
        params: list[Any] = []
        if states:
            placeholders = ", ".join("?" for _ in states)
            where = f"WHERE delivery_state IN ({placeholders})"
            params.extend(states)
        order = "DESC" if newest_first else "ASC"
        query = f"SELECT * FROM outbound_deliveries {where} ORDER BY id {order}"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            try:
                rows = await cursor.fetchall()
                return [self._decode_outbound_delivery_row(row) for row in rows]
            finally:
                await cursor.close()

    async def get_outbound_delivery(self, delivery_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM outbound_deliveries WHERE id = ?",
                (delivery_id,),
            )
            try:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._decode_outbound_delivery_row(row)
            finally:
                await cursor.close()

    async def find_outbound_delivery_by_request_idempotency_key(
        self,
        *,
        event_type: str,
        request_idempotency_key: str,
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM outbound_deliveries
                WHERE event_type = ? AND request_idempotency_key = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (event_type, request_idempotency_key),
            )
            try:
                row = await cursor.fetchone()
                if row is None:
                    return None
                return self._decode_outbound_delivery_row(row)
            finally:
                await cursor.close()

    async def create_outbound_delivery(
        self,
        *,
        route_id: int | None,
        route_name: str,
        route_kind: str,
        route_target: str,
        event_type: str,
        session_key: str | None,
        conversation_target: dict[str, Any] | None,
        route_scope: dict[str, Any],
        event_payload: dict[str, Any] | None,
        request_idempotency_key: str | None = None,
        delivery_message_id: str | None = None,
        message_summary: str,
        test_delivery: bool,
        delivery_state: str,
        attempt_count: int,
        last_attempt_at: str | None = None,
        delivered_at: str | None = None,
        last_error: str | None = None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO outbound_deliveries (
                    route_id,
                    route_name,
                    route_kind,
                    route_target,
                    event_type,
                    session_key,
                    conversation_target_json,
                    route_scope_json,
                    event_payload_json,
                    request_idempotency_key,
                    delivery_message_id,
                    message_summary,
                    test_delivery,
                    delivery_state,
                    attempt_count,
                    last_attempt_at,
                    delivered_at,
                    last_error,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    route_id,
                    route_name,
                    route_kind,
                    route_target,
                    event_type,
                    session_key,
                    json.dumps(conversation_target) if conversation_target is not None else None,
                    json.dumps(route_scope),
                    json.dumps(event_payload) if event_payload is not None else None,
                    request_idempotency_key,
                    delivery_message_id,
                    message_summary,
                    int(test_delivery),
                    delivery_state,
                    attempt_count,
                    last_attempt_at,
                    delivered_at,
                    last_error,
                    now,
                    now,
                ),
            )
            try:
                await db.commit()
                assert cursor.lastrowid is not None
                return int(cursor.lastrowid)
            finally:
                await cursor.close()

    async def update_outbound_delivery(self, delivery_id: int, **fields: Any) -> None:
        if "conversation_target" in fields:
            conversation_target = fields.pop("conversation_target")
            fields["conversation_target_json"] = (
                json.dumps(conversation_target) if conversation_target is not None else None
            )
        if "route_scope" in fields:
            fields["route_scope_json"] = json.dumps(fields.pop("route_scope"))
        if "event_payload" in fields:
            event_payload = fields.pop("event_payload")
            fields["event_payload_json"] = (
                json.dumps(event_payload) if event_payload is not None else None
            )
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [delivery_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE outbound_deliveries SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def list_integrations(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM integrations ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def get_integration(self, integration_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM integrations WHERE id = ?", (integration_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_integration(
        self,
        *,
        name: str,
        kind: str,
        project_id: int | None,
        base_url: str | None,
        auth_scheme: str,
        vault_secret_id: int | None,
        secret_label: str | None,
        secret_value: str | None,
        notes: str | None,
        enabled: bool,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO integrations (
                    name,
                    kind,
                    project_id,
                    base_url,
                    auth_scheme,
                    vault_secret_id,
                    secret_label,
                    secret_value,
                    notes,
                    enabled,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    kind,
                    project_id,
                    base_url,
                    auth_scheme,
                    vault_secret_id,
                    secret_label,
                    secret_value,
                    notes,
                    int(enabled),
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_integration(self, integration_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [integration_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE integrations SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def delete_integration(self, integration_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM integrations WHERE id = ?", (integration_id,))
            await db.commit()

    async def list_vault_secrets(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM vault_secrets ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def get_vault_secret(self, secret_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM vault_secrets WHERE id = ?", (secret_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_vault_secret(
        self,
        *,
        label: str,
        kind: str,
        ciphertext: str,
        preview: str | None,
        notes: str | None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO vault_secrets (
                    label,
                    kind,
                    ciphertext,
                    preview,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (label, kind, ciphertext, preview, notes, now, now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def delete_vault_secret(self, secret_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM vault_secrets WHERE id = ?", (secret_id,))
            await db.commit()

    async def list_skill_pins(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM skill_pins ORDER BY id ASC")
            return [dict(row) for row in rows]

    async def create_skill_pin(
        self,
        *,
        project_id: int,
        name: str,
        prompt_hint: str,
        source: str | None,
        enabled: bool,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO skill_pins (
                    project_id,
                    name,
                    prompt_hint,
                    source,
                    enabled,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, name, prompt_hint, source, int(enabled), now, now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def delete_skill_pin(self, skill_pin_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM skill_pins WHERE id = ?", (skill_pin_id,))
            await db.commit()

    async def delete_playbook(self, playbook_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
            await db.commit()

    async def create_mission(
        self,
        *,
        name: str,
        objective: str,
        status: str,
        instance_id: int,
        project_id: int | None,
        thread_id: str | None,
        session_key: str | None = None,
        conversation_target: dict[str, Any] | None = None,
        cwd: str | None,
        model: str,
        reasoning_effort: str | None,
        collaboration_mode: str | None,
        max_turns: int | None,
        use_builtin_agents: bool,
        run_verification: bool,
        auto_commit: bool,
        pause_on_approval: bool,
        allow_auto_reflexes: bool,
        auto_recover: bool,
        auto_recover_limit: int,
        reflex_cooldown_seconds: int,
        allow_failover: bool = True,
        swarm: dict[str, Any] | None = None,
        toolsets: list[str] | None = None,
        task_blueprint_id: int | None = None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO missions (
                    name,
                    objective,
                    status,
                    instance_id,
                    project_id,
                    task_blueprint_id,
                    thread_id,
                    session_key,
                    conversation_target_json,
                    cwd,
                    model,
                    reasoning_effort,
                    collaboration_mode,
                    max_turns,
                    use_builtin_agents,
                    run_verification,
                    auto_commit,
                    pause_on_approval,
                    allow_auto_reflexes,
                    auto_recover,
                    auto_recover_limit,
                    reflex_cooldown_seconds,
                    allow_failover,
                    swarm_state_json,
                    toolsets_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    name,
                    objective,
                    status,
                    instance_id,
                    project_id,
                    task_blueprint_id,
                    thread_id,
                    session_key,
                    json.dumps(conversation_target) if conversation_target is not None else None,
                    cwd,
                    model,
                    reasoning_effort,
                    collaboration_mode,
                    max_turns,
                    int(use_builtin_agents),
                    int(run_verification),
                    int(auto_commit),
                    int(pause_on_approval),
                    int(allow_auto_reflexes),
                    int(auto_recover),
                    auto_recover_limit,
                    reflex_cooldown_seconds,
                    int(allow_failover),
                    json.dumps(swarm) if swarm is not None else None,
                    json.dumps(toolsets or []),
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def list_missions(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM missions ORDER BY id ASC")
            output: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
                item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
                item["conversation_target"] = self._decode_json_object(
                    item.pop("conversation_target_json", None)
                )
                output.append(item)
            return output

    async def get_mission(self, mission_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def list_lane_snapshots(self, *, limit: int = 24) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                "SELECT * FROM lane_snapshots ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            output = []
            for row in rows:
                item = dict(row)
                item["summary"] = json.loads(item.pop("summary_json"))
                output.append(item)
            return list(reversed(output))

    async def append_lane_snapshot(
        self,
        *,
        instance_id: int,
        snapshot_kind: str,
        summary: dict[str, Any],
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO lane_snapshots (
                    instance_id,
                    snapshot_kind,
                    summary_json,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (instance_id, snapshot_kind, json.dumps(summary), now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def get_mission_by_thread(
        self, instance_id: int, thread_id: str
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM missions
                WHERE instance_id = ? AND thread_id = ?
                ORDER BY
                    CASE status
                        WHEN 'active' THEN 0
                        WHEN 'blocked' THEN 1
                        WHEN 'paused' THEN 2
                        WHEN 'failed' THEN 3
                        WHEN 'completed' THEN 4
                        ELSE 5
                    END,
                    CASE WHEN in_progress = 1 THEN 0 ELSE 1 END,
                    updated_at DESC,
                    id DESC
                LIMIT 1
                """,
                (instance_id, thread_id),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def get_latest_mission_by_session_key(
        self,
        session_key: str,
        *,
        instance_id: int | None = None,
        require_thread: bool = False,
    ) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return None
        placeholders = ", ".join("?" for _ in aliases)
        query = [
            f"SELECT * FROM missions WHERE LOWER(TRIM(session_key)) IN ({placeholders})",
        ]
        params: list[Any] = list(aliases)
        if instance_id is not None:
            query.append("AND instance_id = ?")
            params.append(instance_id)
        if require_thread:
            query.append("AND thread_id IS NOT NULL AND TRIM(thread_id) <> ''")
        query.extend(
            [
                "ORDER BY",
                "CASE status",
                "    WHEN 'active' THEN 0",
                "    WHEN 'blocked' THEN 1",
                "    WHEN 'paused' THEN 2",
                "    WHEN 'failed' THEN 3",
                "    WHEN 'completed' THEN 4",
                "    ELSE 5",
                "END,",
                "updated_at DESC,",
                "id DESC",
                "LIMIT 1",
            ]
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("\n".join(query), params)
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def get_latest_terminal_mission_by_session_key(
        self,
        session_key: str,
        *,
        instance_id: int | None = None,
        require_thread: bool = False,
    ) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return None
        placeholders = ", ".join("?" for _ in aliases)
        query = [
            f"SELECT * FROM missions WHERE LOWER(TRIM(session_key)) IN ({placeholders})",
            "AND status IN ('completed', 'failed')",
        ]
        params: list[Any] = list(aliases)
        if instance_id is not None:
            query.append("AND instance_id = ?")
            params.append(instance_id)
        if require_thread:
            query.append("AND thread_id IS NOT NULL AND TRIM(thread_id) <> ''")
        query.extend(
            [
                "ORDER BY",
                "updated_at DESC,",
                "id DESC",
                "LIMIT 1",
            ]
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("\n".join(query), params)
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def get_latest_thread_child_mission_by_parent_session_key(
        self,
        parent_session_key: str,
        *,
        instance_id: int | None = None,
        require_thread: bool = False,
    ) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(parent_session_key)
        if not aliases:
            return None
        predicates = " OR ".join("LOWER(TRIM(session_key)) LIKE ?" for _ in aliases)
        query = [f"SELECT * FROM missions WHERE ({predicates})"]
        params: list[Any] = [f"{alias}:thread:%" for alias in aliases]
        if instance_id is not None:
            query.append("AND instance_id = ?")
            params.append(instance_id)
        if require_thread:
            query.append("AND thread_id IS NOT NULL AND TRIM(thread_id) <> ''")
        query.extend(
            [
                "ORDER BY",
                "CASE status",
                "    WHEN 'active' THEN 0",
                "    WHEN 'blocked' THEN 1",
                "    WHEN 'paused' THEN 2",
                "    WHEN 'failed' THEN 3",
                "    WHEN 'completed' THEN 4",
                "    ELSE 5",
                "END,",
                "updated_at DESC,",
                "id DESC",
                "LIMIT 1",
            ]
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("\n".join(query), params)
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def get_latest_terminal_thread_child_mission_by_parent_session_key(
        self,
        parent_session_key: str,
        *,
        instance_id: int | None = None,
        require_thread: bool = False,
    ) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(parent_session_key)
        if not aliases:
            return None
        predicates = " OR ".join("LOWER(TRIM(session_key)) LIKE ?" for _ in aliases)
        query = [
            f"SELECT * FROM missions WHERE ({predicates})",
            "AND status IN ('completed', 'failed')",
        ]
        params: list[Any] = [f"{alias}:thread:%" for alias in aliases]
        if instance_id is not None:
            query.append("AND instance_id = ?")
            params.append(instance_id)
        if require_thread:
            query.append("AND thread_id IS NOT NULL AND TRIM(thread_id) <> ''")
        query.extend(
            [
                "ORDER BY",
                "updated_at DESC,",
                "id DESC",
                "LIMIT 1",
            ]
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("\n".join(query), params)
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def list_thread_child_missions_by_parent_session_key(
        self,
        parent_session_key: str,
        *,
        instance_id: int | None = None,
        require_thread: bool = False,
    ) -> list[dict[str, Any]]:
        aliases = session_key_lookup_aliases(parent_session_key)
        if not aliases:
            return []
        predicates = " OR ".join("LOWER(TRIM(session_key)) LIKE ?" for _ in aliases)
        query = [f"SELECT * FROM missions WHERE ({predicates})"]
        params: list[Any] = [f"{alias}:thread:%" for alias in aliases]
        if instance_id is not None:
            query.append("AND instance_id = ?")
            params.append(instance_id)
        if require_thread:
            query.append("AND thread_id IS NOT NULL AND TRIM(thread_id) <> ''")
        query.extend(
            [
                "ORDER BY",
                "updated_at DESC,",
                "id DESC",
            ]
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("\n".join(query), params)
            rows = await cursor.fetchall()
            items: list[dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
                item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
                item["conversation_target"] = self._decode_json_object(
                    item.pop("conversation_target_json", None)
                )
                items.append(item)
            return items

    async def get_latest_mission_by_run_id(
        self,
        run_id: str,
        *,
        instance_id: int | None = None,
        require_session_key: bool = False,
    ) -> dict[str, Any] | None:
        normalized_run_id = str(run_id or "").strip()
        if not normalized_run_id:
            return None
        query = [
            "SELECT * FROM missions",
            "WHERE CASE",
            "    WHEN json_valid(swarm_state_json)",
            "        THEN COALESCE(json_extract(swarm_state_json, '$.run_id'), '')",
            "    ELSE ''",
            "END = ?",
        ]
        params: list[Any] = [normalized_run_id]
        if instance_id is not None:
            query.append("AND instance_id = ?")
            params.append(instance_id)
        if require_session_key:
            query.append("AND session_key IS NOT NULL AND TRIM(session_key) <> ''")
        query.extend(
            [
                "ORDER BY",
                "CASE status",
                "    WHEN 'active' THEN 0",
                "    WHEN 'blocked' THEN 1",
                "    WHEN 'paused' THEN 2",
                "    WHEN 'failed' THEN 3",
                "    WHEN 'completed' THEN 4",
                "    ELSE 5",
                "END,",
                "updated_at DESC,",
                "id DESC",
                "LIMIT 1",
            ]
        )
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("\n".join(query), params)
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["swarm"] = self._decode_json_object(item.pop("swarm_state_json", None))
            item["toolsets"] = self._decode_json_list(item.pop("toolsets_json", "[]"))
            item["conversation_target"] = self._decode_json_object(
                item.pop("conversation_target_json", None)
            )
            return item

    async def update_mission(self, mission_id: int, **fields: Any) -> None:
        if "swarm" in fields:
            swarm = fields.pop("swarm")
            fields["swarm_state_json"] = json.dumps(swarm) if swarm is not None else None
        if "toolsets" in fields:
            fields["toolsets_json"] = json.dumps(fields.pop("toolsets"))
        if "conversation_target" in fields:
            target = fields.pop("conversation_target")
            fields["conversation_target_json"] = (
                json.dumps(target) if target is not None else None
            )
        if not fields:
            return
        fields["updated_at"] = utcnow()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [mission_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE missions SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()

    async def delete_mission(self, mission_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM mission_checkpoints WHERE mission_id = ?", (mission_id,))
            await db.execute("DELETE FROM missions WHERE id = ?", (mission_id,))
            await db.commit()

    async def append_mission_checkpoint(
        self,
        *,
        mission_id: int,
        thread_id: str | None,
        turn_id: str | None,
        kind: str,
        summary: str,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO mission_checkpoints (
                    mission_id,
                    thread_id,
                    turn_id,
                    kind,
                    summary,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mission_id, thread_id, turn_id, kind, summary, now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def list_mission_checkpoints(
        self,
        mission_id: int,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM mission_checkpoints
                WHERE mission_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (mission_id, limit),
            )
            return [dict(row) for row in rows]

    async def append_event(
        self,
        *,
        instance_id: int | None,
        thread_id: str | None,
        method: str,
        payload: dict[str, Any],
    ) -> int:
        now = utcnow()
        for attempt in range(APPEND_EVENT_LOCK_RETRY_ATTEMPTS):
            try:
                async with aiosqlite.connect(
                    self.path,
                    timeout=APPEND_EVENT_BUSY_TIMEOUT_SECONDS,
                ) as db:
                    cursor = await db.execute(
                        """
                        INSERT INTO events (
                            instance_id,
                            thread_id,
                            method,
                            payload_json,
                            created_at
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (instance_id, thread_id, method, json.dumps(payload), now),
                    )
                    await db.commit()
                    assert cursor.lastrowid is not None
                    return int(cursor.lastrowid)
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc).lower():
                    raise
                if attempt + 1 >= APPEND_EVENT_LOCK_RETRY_ATTEMPTS:
                    raise
                await asyncio.sleep(
                    APPEND_EVENT_LOCK_RETRY_BASE_DELAY_SECONDS * (attempt + 1)
                )
        raise RuntimeError("append_event exhausted all retry attempts without raising.")

    async def create_gateway_wake_request(
        self,
        *,
        mode: str,
        text: str,
        reason: str | None = None,
        agent_id: str | None = None,
        session_key: str | None = None,
    ) -> int:
        now = utcnow()
        normalized_reason = _normalize_gateway_wake_reason(reason)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            existing_rows = await db.execute_fetchall(
                """
                SELECT *
                FROM gateway_wake_requests
                WHERE status = 'pending'
                  AND mode = ?
                ORDER BY id ASC
                """,
                (mode,),
            )
            matching_rows = [
                row
                for row in existing_rows
                if _gateway_wake_target_matches(
                    row,
                    agent_id=agent_id,
                    session_key=session_key,
                )
            ]
            if matching_rows:
                canonical_row = matching_rows[0]
                canonical_id = int(canonical_row["id"])
                winning_text, winning_reason, winning_priority = _select_gateway_wake_row_winner(
                    matching_rows
                )
                next_priority = _resolve_gateway_wake_reason_priority(normalized_reason)
                if next_priority >= winning_priority:
                    winning_text = text
                    winning_reason = normalized_reason
                await db.execute(
                    """
                    UPDATE gateway_wake_requests
                    SET text = ?,
                        reason = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (winning_text, winning_reason, now, canonical_id),
                )
                duplicate_ids = [int(row["id"]) for row in matching_rows[1:]]
                if duplicate_ids:
                    placeholders = ", ".join("?" for _ in duplicate_ids)
                    await db.execute(
                        f"DELETE FROM gateway_wake_requests WHERE id IN ({placeholders})",
                        tuple(duplicate_ids),
                    )
                await db.commit()
                return canonical_id
            cursor = await db.execute(
                """
                INSERT INTO gateway_wake_requests (
                    mode,
                    text,
                    reason,
                    agent_id,
                    session_key,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (mode, text, normalized_reason, agent_id, session_key, now, now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def list_gateway_wake_requests(self, *, limit: int = 50) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM gateway_wake_requests
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in rows]

    async def claim_next_gateway_wake_request(
        self,
        *,
        modes: tuple[str, ...] | None = None,
    ) -> dict[str, Any] | None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            while True:
                if modes:
                    placeholders = ", ".join("?" for _ in modes)
                    mode_clause = f" AND mode IN ({placeholders})"
                    query_params: tuple[object, ...] = tuple(modes)
                else:
                    mode_clause = ""
                    query_params = ()
                row = await (
                    await db.execute(
                        f"""
                        SELECT *
                        FROM gateway_wake_requests
                        WHERE status = 'pending'
                        {mode_clause}
                        ORDER BY id ASC
                        LIMIT 1
                        """,
                        query_params,
                    )
                ).fetchone()
                if row is None:
                    return None
                row_mode = str(row["mode"])
                row_agent_id = str(row["agent_id"]) if row["agent_id"] is not None else None
                row_session_key = (
                    str(row["session_key"]) if row["session_key"] is not None else None
                )
                same_mode_rows = await db.execute_fetchall(
                    """
                    SELECT *
                    FROM gateway_wake_requests
                    WHERE status = 'pending'
                      AND mode = ?
                    ORDER BY id ASC
                    """,
                    (row_mode,),
                )
                matching_rows = [
                    candidate
                    for candidate in same_mode_rows
                    if _gateway_wake_target_matches(
                        candidate,
                        agent_id=row_agent_id,
                        session_key=row_session_key,
                    )
                ]
                if len(matching_rows) > 1:
                    canonical_row = matching_rows[0]
                    canonical_id = int(canonical_row["id"])
                    winning_text, winning_reason, _ = _select_gateway_wake_row_winner(
                        matching_rows
                    )
                    await db.execute(
                        """
                        UPDATE gateway_wake_requests
                        SET text = ?,
                            reason = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (winning_text, winning_reason, now, canonical_id),
                    )
                    duplicate_ids = [int(candidate["id"]) for candidate in matching_rows[1:]]
                    placeholders = ", ".join("?" for _ in duplicate_ids)
                    await db.execute(
                        f"DELETE FROM gateway_wake_requests WHERE id IN ({placeholders})",
                        tuple(duplicate_ids),
                    )
                    await db.commit()
                    row = await (
                        await db.execute(
                            """
                            SELECT *
                            FROM gateway_wake_requests
                            WHERE id = ?
                            LIMIT 1
                            """,
                            (canonical_id,),
                        )
                    ).fetchone()
                    if row is None:
                        continue
                request_id = int(row["id"])
                cursor = await db.execute(
                    """
                    UPDATE gateway_wake_requests
                    SET status = 'claimed',
                        claimed_at = ?,
                        updated_at = ?
                    WHERE id = ? AND status = 'pending'
                    """,
                    (now, now, request_id),
                )
                await db.commit()
                if cursor.rowcount:
                    claimed = dict(row)
                    claimed["status"] = "claimed"
                    claimed["claimed_at"] = now
                    claimed["updated_at"] = now
                    return claimed

    async def release_gateway_wake_request(self, request_id: int) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE gateway_wake_requests
                SET status = 'pending',
                    claimed_at = NULL,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, request_id),
            )
            await db.commit()

    async def mark_gateway_wake_request_dispatched(self, request_id: int) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE gateway_wake_requests
                SET status = 'dispatched',
                    dispatched_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, request_id),
            )
            await db.commit()

    async def list_events(self, limit: int = 200) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            output = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                output.append(item)
            return list(reversed(output))

    async def get_latest_node_event(self, *, event_name: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM events
                WHERE method = 'node.event'
                  AND json_extract(payload_json, '$.event') = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (event_name,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            return item

    async def list_thread_events(
        self,
        *,
        instance_id: int,
        thread_id: str,
        limit: int = 200,
        compact: bool = False,
        methods: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            method_clause = ""
            method_params: list[Any] = []
            if methods:
                placeholders = ", ".join("?" for _ in methods)
                method_clause = f" AND method IN ({placeholders})"
                method_params.extend(methods)

            if compact:
                try:
                    rows = await db.execute_fetchall(
                        f"""
                        SELECT
                            id,
                            instance_id,
                            thread_id,
                            method,
                            created_at,
                            COALESCE(
                                json_extract(payload_json, '$.turnId'),
                                json_extract(payload_json, '$.turn.id')
                            ) AS turn_id,
                            COALESCE(json_extract(payload_json, '$.itemId'), '') AS item_id,
                            substr(
                                COALESCE(json_extract(payload_json, '$.delta'), ''),
                                1,
                                ?
                            ) AS delta,
                            COALESCE(json_extract(payload_json, '$.item.type'), '') AS item_type,
                            COALESCE(json_extract(payload_json, '$.item.id'), '') AS item_nested_id,
                            COALESCE(json_extract(payload_json, '$.item.phase'), '') AS item_phase,
                            COALESCE(json_extract(payload_json, '$.item.tool'), '') AS item_tool,
                            substr(
                                COALESCE(json_extract(payload_json, '$.item.command'), ''),
                                1,
                                ?
                            ) AS item_command,
                            substr(
                                COALESCE(json_extract(payload_json, '$.item.text'), ''),
                                1,
                                ?
                            ) AS item_text,
                            substr(
                                COALESCE(json_extract(payload_json, '$.item.prompt'), ''),
                                1,
                                ?
                            ) AS item_prompt
                        FROM events
                        WHERE instance_id = ? AND thread_id = ?{method_clause}
                        ORDER BY id DESC
                        LIMIT ?
                        """,
                        (
                            THREAD_EVENT_COMPACT_DELTA_LIMIT,
                            THREAD_EVENT_COMPACT_COMMAND_LIMIT,
                            THREAD_EVENT_COMPACT_TEXT_LIMIT,
                            THREAD_EVENT_COMPACT_PROMPT_LIMIT,
                            instance_id,
                            thread_id,
                            *method_params,
                            limit,
                        ),
                    )
                except sqlite3.OperationalError as exc:
                    if "json_extract" not in str(exc).lower():
                        raise
                else:
                    output = []
                    for row in rows:
                        payload: dict[str, Any] = {}
                        turn_id_value = str(row["turn_id"] or "").strip()
                        if turn_id_value:
                            payload["turnId"] = turn_id_value
                        item_id_value = str(row["item_id"] or "").strip()
                        if item_id_value:
                            payload["itemId"] = item_id_value
                        delta_value = str(row["delta"] or "")
                        if delta_value:
                            payload["delta"] = delta_value
                        item_payload: dict[str, Any] = {}
                        item_type = str(row["item_type"] or "").strip()
                        if item_type:
                            item_payload["type"] = item_type
                        item_nested_id = str(row["item_nested_id"] or "").strip()
                        if item_nested_id:
                            item_payload["id"] = item_nested_id
                        item_phase = str(row["item_phase"] or "").strip()
                        if item_phase:
                            item_payload["phase"] = item_phase
                        item_tool = str(row["item_tool"] or "").strip()
                        if item_tool:
                            item_payload["tool"] = item_tool
                        item_command = str(row["item_command"] or "").strip()
                        if item_command:
                            item_payload["command"] = item_command
                        item_text = str(row["item_text"] or "")
                        if item_text:
                            item_payload["text"] = item_text
                        item_prompt = str(row["item_prompt"] or "")
                        if item_prompt:
                            item_payload["prompt"] = item_prompt
                        if item_payload:
                            payload["item"] = item_payload
                        output.append(
                            {
                                "id": row["id"],
                                "instance_id": row["instance_id"],
                                "thread_id": row["thread_id"],
                                "method": row["method"],
                                "created_at": row["created_at"],
                                "payload": payload,
                            }
                        )
                    return list(reversed(output))

            rows = await db.execute_fetchall(
                f"""
                SELECT *
                FROM events
                WHERE instance_id = ? AND thread_id = ?{method_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                (instance_id, thread_id, *method_params, limit),
            )
            output = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                output.append(item)
            return list(reversed(output))

    async def get_thread_event_metrics(
        self,
        *,
        instance_id: int,
        thread_id: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        cutoff_30s = (now - timedelta(seconds=30)).isoformat()
        cutoff_5m = (now - timedelta(minutes=5)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT
                    MAX(created_at) AS last_event_at,
                    COALESCE(SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END), 0)
                        AS recent_event_count_30s,
                    COALESCE(SUM(CASE WHEN created_at >= ? THEN 1 ELSE 0 END), 0)
                        AS recent_event_count_5m,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN created_at >= ?
                                AND method = 'item/commandExecution/outputDelta'
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS recent_output_delta_count_30s,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN created_at >= ?
                                AND method IN (
                                    'item/commandExecution/outputDelta',
                                    'item/started',
                                    'item/completed',
                                    'turn/started',
                                    'turn/completed'
                                )
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS recent_turn_activity_count_30s
                FROM events
                WHERE instance_id = ? AND thread_id = ?
                """,
                (cutoff_30s, cutoff_5m, cutoff_30s, cutoff_30s, instance_id, thread_id),
            )
            row = await cursor.fetchone()
            if row is None:
                return {
                    "last_event_at": None,
                    "recent_event_count_30s": 0,
                    "recent_event_count_5m": 0,
                    "recent_output_delta_count_30s": 0,
                    "recent_turn_activity_count_30s": 0,
                }
            item = dict(row)
            item["recent_event_count_30s"] = int(item.get("recent_event_count_30s") or 0)
            item["recent_event_count_5m"] = int(item.get("recent_event_count_5m") or 0)
            item["recent_output_delta_count_30s"] = int(
                item.get("recent_output_delta_count_30s") or 0
            )
            item["recent_turn_activity_count_30s"] = int(
                item.get("recent_turn_activity_count_30s") or 0
            )
            return item

    async def append_control_chat_message(
        self,
        *,
        role: str,
        content: str,
        action_kind: str | None = None,
        mission_id: int | None = None,
        opportunity_id: str | None = None,
        target_label: str | None = None,
        session_key: str | None = None,
        usage: dict[str, Any] | None = None,
        cost: dict[str, Any] | None = None,
        model_provider: str | None = None,
        model: str | None = None,
        created_at: str | None = None,
    ) -> int:
        now = created_at or utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO control_chat_messages (
                    role,
                    content,
                    action_kind,
                    mission_id,
                    opportunity_id,
                    target_label,
                    session_key,
                    model_provider,
                    model,
                    usage_json,
                    cost_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    role,
                    content,
                    action_kind,
                    mission_id,
                    opportunity_id,
                    target_label,
                    session_key,
                    model_provider,
                    model,
                    json.dumps(usage) if usage is not None else None,
                    json.dumps(cost) if cost is not None else None,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def get_control_chat_message(self, message_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM control_chat_messages WHERE id = ?",
                (message_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_control_chat_messages(
        self,
        *,
        limit: int = 24,
        session_key: str | None = None,
    ) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            if session_key is None:
                rows = await db.execute_fetchall(
                    """
                    SELECT *
                    FROM control_chat_messages
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                aliases = session_key_lookup_aliases(session_key)
                if not aliases:
                    return []
                placeholders = ",".join("?" for _ in aliases)
                rows = await db.execute_fetchall(
                    f"""
                    SELECT *
                    FROM control_chat_messages
                    WHERE LOWER(TRIM(session_key)) IN ({placeholders})
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (*aliases, limit),
                )
            return list(reversed([dict(row) for row in rows]))

    async def get_first_control_chat_message(
        self,
        *,
        session_key: str,
        role: str | None = None,
    ) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return None
        placeholders = ",".join("?" for _ in aliases)
        query = f"""
            SELECT *
            FROM control_chat_messages
            WHERE LOWER(TRIM(session_key)) IN ({placeholders})
        """
        params: list[object] = list(aliases)
        normalized_role = str(role or "").strip().lower()
        if normalized_role:
            query += " AND LOWER(TRIM(role)) = ?"
            params.append(normalized_role)
        query += " ORDER BY id ASC LIMIT 1"
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, tuple(params))
            row = await cursor.fetchone()
            return dict(row) if row is not None else None

    async def count_control_chat_messages(
        self,
        *,
        session_key: str,
        up_to_id: int | None = None,
    ) -> int:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return 0
        placeholders = ",".join("?" for _ in aliases)
        query = f"""
            SELECT COUNT(*) AS count
            FROM control_chat_messages
            WHERE LOWER(TRIM(session_key)) IN ({placeholders})
        """
        params: list[object] = list(aliases)
        if up_to_id is not None:
            query += " AND id <= ?"
            params.append(up_to_id)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, tuple(params))
            row = await cursor.fetchone()
            return int(row["count"]) if row is not None else 0

    async def list_control_chat_session_keys(self) -> list[str]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT session_key, MAX(id) AS latest_id
                FROM control_chat_messages
                WHERE session_key IS NOT NULL AND TRIM(session_key) <> ''
                GROUP BY LOWER(TRIM(session_key))
                ORDER BY latest_id DESC
                """
            )
            session_keys: list[str] = []
            for row in rows:
                session_key = str(row["session_key"] or "").strip()
                if session_key:
                    session_keys.append(session_key)
            return session_keys

    async def delete_control_chat_messages(
        self,
        *,
        session_key: str,
    ) -> int:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return 0
        placeholders = ",".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                f"""
                DELETE FROM control_chat_messages
                WHERE LOWER(TRIM(session_key)) IN ({placeholders})
                """,
                tuple(aliases),
            )
            await db.commit()
            return int(cursor.rowcount or 0)

    async def delete_control_chat_messages_through_id(
        self,
        *,
        session_key: str,
        max_id: int,
    ) -> int:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return 0
        placeholders = ",".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                f"""
                DELETE FROM control_chat_messages
                WHERE LOWER(TRIM(session_key)) IN ({placeholders})
                  AND id <= ?
                """,
                (*aliases, max_id),
            )
            await db.commit()
            return int(cursor.rowcount or 0)

    async def append_control_chat_compaction_checkpoint(
        self,
        *,
        checkpoint_id: str,
        session_key: str,
        created_at_ms: int,
        payload: dict[str, Any],
        archived_messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO control_chat_compaction_checkpoints (
                    checkpoint_id,
                    session_key,
                    created_at_ms,
                    payload_json,
                    archived_messages_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    session_key,
                    created_at_ms,
                    json.dumps(payload),
                    json.dumps(archived_messages),
                    now,
                ),
            )
            await db.commit()
        stored = await self.get_control_chat_compaction_checkpoint(
            session_key=session_key,
            checkpoint_id=checkpoint_id,
        )
        if stored is None:
            raise RuntimeError("Failed to persist control chat compaction checkpoint.")
        return stored

    async def list_control_chat_compaction_checkpoints(
        self,
        *,
        session_key: str,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return []
        placeholders = ",".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                f"""
                SELECT payload_json
                FROM control_chat_compaction_checkpoints
                WHERE LOWER(TRIM(session_key)) IN ({placeholders})
                ORDER BY created_at_ms DESC, checkpoint_id DESC
                LIMIT ?
                """,
                (*aliases, limit),
            )
            return [json.loads(str(row["payload_json"]) or "{}") for row in rows]

    async def count_control_chat_compaction_checkpoints(
        self,
        *,
        session_key: str,
    ) -> int:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return 0
        placeholders = ",".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM control_chat_compaction_checkpoints
                WHERE LOWER(TRIM(session_key)) IN ({placeholders})
                """,
                tuple(aliases),
            )
            row = await cursor.fetchone()
            return int(row["count"]) if row is not None else 0

    async def get_control_chat_compaction_checkpoint(
        self,
        *,
        session_key: str,
        checkpoint_id: str,
    ) -> dict[str, Any] | None:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return None
        placeholders = ",".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT payload_json
                FROM control_chat_compaction_checkpoints
                WHERE checkpoint_id = ?
                  AND LOWER(TRIM(session_key)) IN ({placeholders})
                LIMIT 1
                """,
                (checkpoint_id, *aliases),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(str(row["payload_json"]) or "{}")

    async def get_control_chat_compaction_checkpoint_messages(
        self,
        *,
        session_key: str,
        checkpoint_id: str,
    ) -> list[dict[str, Any]]:
        aliases = session_key_lookup_aliases(session_key)
        if not aliases:
            return []
        placeholders = ",".join("?" for _ in aliases)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT archived_messages_json
                FROM control_chat_compaction_checkpoints
                WHERE checkpoint_id = ?
                  AND LOWER(TRIM(session_key)) IN ({placeholders})
                LIMIT 1
                """,
                (checkpoint_id, *aliases),
            )
            row = await cursor.fetchone()
            if row is None:
                return []
            try:
                decoded = json.loads(str(row["archived_messages_json"]) or "[]")
            except (TypeError, ValueError):
                return []
            if not isinstance(decoded, list):
                return []
            return [item for item in decoded if isinstance(item, dict)]

    async def append_attention_queue_action(
        self,
        *,
        signal_id: str,
        signal_fingerprint: str,
        signal_level: str,
        action_kind: str,
        status: str,
        mission_id: int | None = None,
        opportunity_id: str | None = None,
        target_label: str | None = None,
        summary: str | None = None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO attention_queue_actions (
                    signal_id,
                    signal_fingerprint,
                    signal_level,
                    mission_id,
                    opportunity_id,
                    target_label,
                    action_kind,
                    status,
                    summary,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal_id,
                    signal_fingerprint,
                    signal_level,
                    mission_id,
                    opportunity_id,
                    target_label,
                    action_kind,
                    status,
                    summary,
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def get_latest_attention_queue_action(
        self,
        signal_fingerprint: str,
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM attention_queue_actions
                WHERE signal_fingerprint = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (signal_fingerprint,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_attention_queue_actions(self, *, limit: int = 24) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM attention_queue_actions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return list(reversed([dict(row) for row in rows]))

    async def upsert_server_request(
        self,
        *,
        instance_id: int,
        request_id: str,
        thread_id: str | None,
        method: str,
        payload: dict[str, Any],
        status: str,
    ) -> None:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO server_requests (
                    instance_id,
                    request_id,
                    thread_id,
                    method,
                    payload_json,
                    status,
                    created_at,
                    resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                ON CONFLICT(instance_id, request_id) DO UPDATE SET
                    thread_id = excluded.thread_id,
                    method = excluded.method,
                    payload_json = excluded.payload_json,
                    status = excluded.status
                """,
                (instance_id, request_id, thread_id, method, json.dumps(payload), status, now),
            )
            await db.commit()

    async def resolve_server_request(
        self,
        *,
        instance_id: int,
        request_id: str,
        status: str,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE server_requests
                SET status = ?, resolved_at = ?
                WHERE instance_id = ? AND request_id = ?
                """,
                (status, utcnow(), instance_id, request_id),
            )
            await db.commit()

    async def clear_server_requests_for_instance(self, instance_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM server_requests WHERE instance_id = ?", (instance_id,))
            await db.commit()

    async def list_unresolved_server_requests(self, instance_id: int) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT * FROM server_requests
                WHERE instance_id = ? AND status = 'pending'
                ORDER BY id DESC
                """,
                (instance_id,),
            )
            output = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                output.append(item)
            return output

    async def list_remote_requests(self, *, limit: int = 50) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM remote_requests
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            output = []
            for row in rows:
                item = dict(row)
                item["payload"] = json.loads(item.pop("payload_json"))
                result_json = item.pop("result_json")
                item["result"] = json.loads(result_json) if result_json else None
                output.append(item)
            return list(reversed(output))

    async def get_remote_request(self, request_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM remote_requests WHERE id = ?", (request_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result_json = item.pop("result_json")
            item["result"] = json.loads(result_json) if result_json else None
            return item

    async def get_remote_request_by_idempotency(
        self,
        *,
        operator_id: int,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT *
                FROM remote_requests
                WHERE operator_id = ? AND idempotency_key = ?
                """,
                (operator_id, idempotency_key),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result_json = item.pop("result_json")
            item["result"] = json.loads(result_json) if result_json else None
            return item

    async def create_remote_request(
        self,
        *,
        team_id: int,
        operator_id: int,
        idempotency_key: str | None,
        kind: str,
        status: str,
        source: str,
        source_ip: str | None,
        user_agent: str | None,
        target_kind: str | None,
        target_id: int | None,
        target_label: str | None,
        payload: dict[str, Any],
        result: dict[str, Any] | None = None,
        error: str | None = None,
        resolved_at: str | None = None,
    ) -> int:
        now = utcnow()
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO remote_requests (
                    team_id,
                    operator_id,
                    idempotency_key,
                    kind,
                    status,
                    source,
                    source_ip,
                    user_agent,
                    target_kind,
                    target_id,
                    target_label,
                    payload_json,
                    result_json,
                    error,
                    requested_at,
                    resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    team_id,
                    operator_id,
                    idempotency_key,
                    kind,
                    status,
                    source,
                    source_ip,
                    user_agent,
                    target_kind,
                    target_id,
                    target_label,
                    json.dumps(payload),
                    json.dumps(result) if result is not None else None,
                    error,
                    now,
                    resolved_at,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_remote_request(self, request_id: int, **fields: Any) -> None:
        if "payload" in fields:
            fields["payload_json"] = json.dumps(fields.pop("payload"))
        if "result" in fields:
            result = fields.pop("result")
            fields["result_json"] = json.dumps(result) if result is not None else None
        if not fields:
            return
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [request_id]
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"UPDATE remote_requests SET {assignments} WHERE id = ?",
                values,
            )
            await db.commit()
