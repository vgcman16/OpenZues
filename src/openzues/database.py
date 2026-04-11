from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

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
                CREATE TABLE IF NOT EXISTS control_chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    action_kind TEXT,
                    mission_id INTEGER,
                    opportunity_id TEXT,
                    target_label TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_control_chat_messages_created
                    ON control_chat_messages(id DESC);
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
                CREATE TABLE IF NOT EXISTS notification_routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    target TEXT NOT NULL,
                    events_json TEXT NOT NULL,
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
            await self._ensure_column(db, "missions", "last_reflex_kind", "TEXT")
            await self._ensure_column(db, "missions", "last_reflex_at", "TEXT")
            await self._ensure_column(db, "missions", "task_blueprint_id", "INTEGER")
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
            await self._ensure_column(db, "notification_routes", "vault_secret_id", "INTEGER")
            await self._ensure_column(db, "integrations", "vault_secret_id", "INTEGER")
            await self._ensure_column(db, "missions", "session_key", "TEXT")
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
                CREATE INDEX IF NOT EXISTS idx_notification_routes_vault_secret
                ON notification_routes(vault_secret_id)
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
                output.append({**item, **payload})
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
            return {**item, **payload}

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
            row = await cursor.fetchone()
            return dict(row) if row else None

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
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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

    async def list_notification_routes(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                "SELECT * FROM notification_routes ORDER BY id ASC"
            )
            output = []
            for row in rows:
                item = dict(row)
                item["events"] = json.loads(item.pop("events_json"))
                output.append(item)
            return output

    async def create_notification_route(
        self,
        *,
        name: str,
        kind: str,
        target: str,
        events: list[str],
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
                    enabled,
                    secret_header_name,
                    secret_token,
                    vault_secret_id,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    kind,
                    target,
                    json.dumps(events),
                    int(enabled),
                    secret_header_name,
                    secret_token,
                    vault_secret_id,
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def update_notification_route(self, route_id: int, **fields: Any) -> None:
        if "events" in fields:
            fields["events_json"] = json.dumps(fields.pop("events"))
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
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
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
            return [dict(row) for row in rows]

    async def get_mission(self, mission_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

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
            return dict(row) if row else None

    async def update_mission(self, mission_id: int, **fields: Any) -> None:
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
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                """
                INSERT INTO events (instance_id, thread_id, method, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (instance_id, thread_id, method, json.dumps(payload), now),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

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

    async def append_control_chat_message(
        self,
        *,
        role: str,
        content: str,
        action_kind: str | None = None,
        mission_id: int | None = None,
        opportunity_id: str | None = None,
        target_label: str | None = None,
    ) -> int:
        now = utcnow()
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
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (role, content, action_kind, mission_id, opportunity_id, target_label, now),
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

    async def list_control_chat_messages(self, *, limit: int = 24) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """
                SELECT *
                FROM control_chat_messages
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return list(reversed([dict(row) for row in rows]))

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
