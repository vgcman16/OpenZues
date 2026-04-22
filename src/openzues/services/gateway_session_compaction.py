from __future__ import annotations

from typing import Any
from uuid import uuid4

from openzues.database import Database
from openzues.services.session_keys import canonicalize_session_key, parse_thread_session_suffix

_MAX_COMPACTION_CHECKPOINTS = 25
_CHECKPOINT_SUMMARY_LIMIT = 240
_SUMMARY_COMPACTION_KEEP_MESSAGES = 2
_SUMMARY_COMPACTION_ACTION_KIND = "compaction_summary"
_SUMMARY_COMPACTION_FALLBACK = "No earlier content to summarize."


class GatewaySessionCompactionUnavailableError(RuntimeError):
    pass


class GatewaySessionCompactionService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def compact(
        self,
        *,
        session_key: str,
        max_lines: int | None,
        now_ms: int,
    ) -> dict[str, Any]:
        canonical_key = _canonical_session_key(session_key)
        message_count = await self._database.count_control_chat_messages(session_key=canonical_key)
        if message_count <= 0:
            return {"ok": True, "key": canonical_key, "compacted": False, "reason": "no transcript"}

        rows = await self._database.list_control_chat_messages(
            limit=max(1, message_count),
            session_key=canonical_key,
        )
        if not rows:
            return {"ok": True, "key": canonical_key, "compacted": False, "reason": "no transcript"}
        if max_lines is None:
            return await self._compact_with_summary(
                session_key=canonical_key,
                rows=rows,
                now_ms=now_ms,
            )

        total_lines = sum(_message_line_count(str(row.get("content") or "")) for row in rows)
        if total_lines <= max_lines:
            return {"ok": True, "key": canonical_key, "compacted": False, "kept": total_lines}

        kept_rows = _rows_to_keep(rows, max_lines=max_lines)
        archived_rows = rows[: len(rows) - len(kept_rows)]
        if not archived_rows:
            return {"ok": True, "key": canonical_key, "compacted": False, "kept": total_lines}

        resolved_session_id = await self._resolve_compaction_session_id(canonical_key)
        first_kept_id = _row_id_or_none(kept_rows[0]) if kept_rows else None
        last_archived_id = _row_id_or_none(archived_rows[-1])
        if last_archived_id is None:
            return {"ok": True, "key": canonical_key, "compacted": False, "kept": total_lines}
        checkpoint_id = str(uuid4())
        checkpoint = {
            "checkpointId": checkpoint_id,
            "sessionKey": canonical_key,
            "sessionId": resolved_session_id,
            "createdAt": now_ms,
            "reason": "manual",
            "summary": _checkpoint_summary(archived_rows),
            "firstKeptEntryId": str(first_kept_id) if first_kept_id is not None else None,
            "preCompaction": {
                "sessionId": resolved_session_id,
                "entryId": str(last_archived_id) if last_archived_id is not None else None,
            },
            "postCompaction": {
                "sessionId": resolved_session_id,
                "entryId": str(first_kept_id) if first_kept_id is not None else None,
            },
        }
        normalized_checkpoint = _without_none(checkpoint)
        await self._database.append_control_chat_compaction_checkpoint(
            checkpoint_id=checkpoint_id,
            session_key=canonical_key,
            created_at_ms=now_ms,
            payload=normalized_checkpoint,
            archived_messages=[_checkpoint_message_payload(canonical_key, row) for row in rows],
        )
        await self._database.delete_control_chat_messages_through_id(
            session_key=canonical_key,
            max_id=last_archived_id,
        )
        kept_lines = sum(_message_line_count(str(row.get("content") or "")) for row in kept_rows)
        return {
            "ok": True,
            "key": canonical_key,
            "compacted": True,
            "kept": kept_lines,
            "archivedCount": len(archived_rows),
            "checkpointId": checkpoint_id,
        }

    async def _compact_with_summary(
        self,
        *,
        session_key: str,
        rows: list[dict[str, Any]],
        now_ms: int,
    ) -> dict[str, Any]:
        total_lines = sum(_message_line_count(str(row.get("content") or "")) for row in rows)
        if len(rows) <= _SUMMARY_COMPACTION_KEEP_MESSAGES:
            return {"ok": True, "key": session_key, "compacted": False, "kept": total_lines}

        kept_rows = rows[-_SUMMARY_COMPACTION_KEEP_MESSAGES:]
        archived_rows = rows[: len(rows) - len(kept_rows)]
        if not archived_rows:
            return {"ok": True, "key": session_key, "compacted": False, "kept": total_lines}

        resolved_session_id = await self._resolve_compaction_session_id(session_key)
        checkpoint_id = str(uuid4())
        summary_text = _checkpoint_summary(archived_rows) or _SUMMARY_COMPACTION_FALLBACK
        summary_content = _compaction_summary_message(summary_text)
        last_archived_id = _row_id_or_none(archived_rows[-1])
        if last_archived_id is None:
            return {"ok": True, "key": session_key, "compacted": False, "kept": total_lines}

        await self._database.delete_control_chat_messages(session_key=session_key)
        summary_message_id = await self._database.append_control_chat_message(
            role="system",
            content=summary_content,
            action_kind=_SUMMARY_COMPACTION_ACTION_KIND,
            mission_id=None,
            session_key=session_key,
        )
        for row in kept_rows:
            await self._database.append_control_chat_message(
                role=str(row.get("role") or "assistant"),
                content=str(row.get("content") or ""),
                action_kind=_optional_string(row.get("action_kind")),
                mission_id=_optional_int(row.get("mission_id")),
                opportunity_id=_optional_string(row.get("opportunity_id")),
                target_label=_optional_string(row.get("target_label")),
                session_key=session_key,
                created_at=_optional_string(row.get("created_at")),
            )

        checkpoint = {
            "checkpointId": checkpoint_id,
            "sessionKey": session_key,
            "sessionId": resolved_session_id,
            "createdAt": now_ms,
            "reason": "summary",
            "summary": summary_text,
            "firstKeptEntryId": str(summary_message_id),
            "preCompaction": {
                "sessionId": resolved_session_id,
                "entryId": str(last_archived_id),
            },
            "postCompaction": {
                "sessionId": resolved_session_id,
                "entryId": str(summary_message_id),
            },
        }
        normalized_checkpoint = _without_none(checkpoint)
        await self._database.append_control_chat_compaction_checkpoint(
            checkpoint_id=checkpoint_id,
            session_key=session_key,
            created_at_ms=now_ms,
            payload=normalized_checkpoint,
            archived_messages=[_checkpoint_message_payload(session_key, row) for row in rows],
        )
        kept_lines = _message_line_count(summary_content) + sum(
            _message_line_count(str(row.get("content") or "")) for row in kept_rows
        )
        return {
            "ok": True,
            "key": session_key,
            "compacted": True,
            "kept": kept_lines,
            "archivedCount": len(archived_rows),
            "checkpointId": checkpoint_id,
        }

    async def restore(
        self,
        *,
        session_key: str,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        canonical_key = _canonical_session_key(session_key)
        checkpoint = await self._database.get_control_chat_compaction_checkpoint(
            session_key=canonical_key,
            checkpoint_id=checkpoint_id,
        )
        if checkpoint is None:
            raise ValueError(f"checkpoint not found: {checkpoint_id}")
        snapshot_messages = await self._database.get_control_chat_compaction_checkpoint_messages(
            session_key=canonical_key,
            checkpoint_id=checkpoint_id,
        )
        if not snapshot_messages:
            raise GatewaySessionCompactionUnavailableError(
                "checkpoint snapshot transcript is missing"
            )
        await self._database.delete_control_chat_messages(session_key=canonical_key)
        for message in snapshot_messages:
            await self._database.append_control_chat_message(
                role=str(message.get("role") or "assistant"),
                content=str(message.get("content") or ""),
                action_kind=_optional_string(message.get("actionKind")),
                mission_id=_optional_int(message.get("missionId")),
                opportunity_id=_optional_string(message.get("opportunityId")),
                target_label=_optional_string(message.get("targetLabel")),
                session_key=canonical_key,
                created_at=_optional_string(message.get("createdAt")),
            )
        return {
            "ok": True,
            "key": canonical_key,
            "checkpoint": checkpoint,
        }

    async def branch(
        self,
        *,
        session_key: str,
        checkpoint_id: str,
        target_session_key: str,
    ) -> dict[str, Any]:
        canonical_key = _canonical_session_key(session_key)
        checkpoint = await self._database.get_control_chat_compaction_checkpoint(
            session_key=canonical_key,
            checkpoint_id=checkpoint_id,
        )
        if checkpoint is None:
            raise ValueError(f"checkpoint not found: {checkpoint_id}")
        snapshot_messages = await self._database.get_control_chat_compaction_checkpoint_messages(
            session_key=canonical_key,
            checkpoint_id=checkpoint_id,
        )
        if not snapshot_messages:
            raise GatewaySessionCompactionUnavailableError(
                "checkpoint snapshot transcript is missing"
            )
        target_key = _canonical_session_key(target_session_key)
        for message in snapshot_messages:
            await self._database.append_control_chat_message(
                role=str(message.get("role") or "assistant"),
                content=str(message.get("content") or ""),
                action_kind=_optional_string(message.get("actionKind")),
                mission_id=_optional_int(message.get("missionId")),
                opportunity_id=_optional_string(message.get("opportunityId")),
                target_label=_optional_string(message.get("targetLabel")),
                session_key=target_key,
                created_at=_optional_string(message.get("createdAt")),
            )
        return {
            "ok": True,
            "sourceKey": canonical_key,
            "key": target_key,
            "checkpoint": checkpoint,
        }

    async def list_checkpoints(self, *, session_key: str) -> dict[str, Any]:
        canonical_key = _canonical_session_key(session_key)
        checkpoints = await self._database.list_control_chat_compaction_checkpoints(
            session_key=canonical_key,
            limit=_MAX_COMPACTION_CHECKPOINTS,
        )
        return {"ok": True, "key": canonical_key, "checkpoints": checkpoints}

    async def get_checkpoint(
        self,
        *,
        session_key: str,
        checkpoint_id: str,
    ) -> dict[str, Any]:
        canonical_key = _canonical_session_key(session_key)
        checkpoint = await self._database.get_control_chat_compaction_checkpoint(
            session_key=canonical_key,
            checkpoint_id=checkpoint_id,
        )
        if checkpoint is None:
            raise ValueError(f"checkpoint not found: {checkpoint_id}")
        return {"ok": True, "key": canonical_key, "checkpoint": checkpoint}

    async def _resolve_compaction_session_id(self, session_key: str) -> str:
        mission = await self._database.get_latest_mission_by_session_key(
            session_key,
            require_thread=False,
        )
        mission_thread_id = _optional_string(mission.get("thread_id") if mission else None)
        if mission_thread_id:
            return mission_thread_id
        parsed_session_key = parse_thread_session_suffix(session_key)
        return _optional_string(parsed_session_key.thread_id) or session_key


def _canonical_session_key(session_key: str) -> str:
    return canonicalize_session_key(session_key) or session_key.strip()


def _message_line_count(content: str) -> int:
    non_empty_lines = [line for line in content.splitlines() if line.strip()]
    return max(1, len(non_empty_lines)) if content.strip() else 1


def _rows_to_keep(rows: list[dict[str, Any]], *, max_lines: int) -> list[dict[str, Any]]:
    kept_reversed: list[dict[str, Any]] = []
    kept_lines = 0
    for row in reversed(rows):
        row_lines = _message_line_count(str(row.get("content") or ""))
        if kept_reversed and kept_lines + row_lines > max_lines:
            break
        kept_reversed.append(row)
        kept_lines += row_lines
        if kept_lines >= max_lines:
            break
    return list(reversed(kept_reversed or rows[-1:]))


def _checkpoint_summary(rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in rows:
        text = " ".join(str(row.get("content") or "").split())
        if text:
            parts.append(text)
    summary = " ".join(parts).strip()
    if len(summary) <= _CHECKPOINT_SUMMARY_LIMIT:
        return summary
    return f"{summary[: _CHECKPOINT_SUMMARY_LIMIT - 3].rstrip()}..."


def _compaction_summary_message(summary_text: str) -> str:
    return f"Compaction summary of earlier turns:\n{summary_text}"


def _row_id_or_none(row: dict[str, Any]) -> int | None:
    value = row.get("id")
    return value if isinstance(value, int) else None


def _checkpoint_message_payload(session_key: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "sessionKey": session_key,
        "role": row.get("role"),
        "content": row.get("content"),
        "createdAt": row.get("created_at"),
        "actionKind": row.get("action_kind"),
        "missionId": row.get("mission_id"),
        "opportunityId": row.get("opportunity_id"),
        "targetLabel": row.get("target_label"),
    }


def _without_none(value: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, entry in value.items():
        if isinstance(entry, dict):
            nested = _without_none(entry)
            if nested:
                output[key] = nested
            continue
        if entry is not None:
            output[key] = entry
    return output


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None
