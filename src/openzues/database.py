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
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id INTEGER,
                    thread_id TEXT,
                    method TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
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
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            await db.commit()

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

    async def list_projects(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall("SELECT * FROM projects ORDER BY id ASC")
            return [dict(row) for row in rows]

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
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    kind,
                    instance_id,
                    json.dumps(payload),
                    now,
                    now,
                ),
            )
            await db.commit()
            assert cursor.lastrowid is not None
            return int(cursor.lastrowid)

    async def delete_playbook(self, playbook_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM playbooks WHERE id = ?", (playbook_id,))
            await db.commit()

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
