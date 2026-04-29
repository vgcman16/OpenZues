from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from openzues.services.codex_rpc import extract_turn_id


class GatewayAcpSpawnService(Protocol):
    async def spawn(
        self,
        params: Mapping[str, object],
        context: Mapping[str, object],
    ) -> dict[str, object]:
        """Start an ACP-backed child run and return an OpenClaw-shaped result."""

    async def cancel_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
    ) -> dict[str, object]:
        """Cancel any active ACP runtime work before a session mutation."""

    async def close_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
        discard_persistent_state: bool,
        require_acp_session: bool,
        allow_backend_unavailable: bool,
    ) -> dict[str, object]:
        """Close ACP runtime handles before local session state is removed."""


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _read_thread_id(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    thread = result.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        return thread["id"].strip() or None
    thread_id = result.get("threadId")
    if isinstance(thread_id, str):
        return thread_id.strip() or None
    return None


class RuntimeManagerAcpSpawnService:
    def __init__(
        self,
        manager: Any,
        *,
        default_model: str = "gpt-5.4",
    ) -> None:
        self._manager = manager
        self._default_model = default_model

    async def spawn(
        self,
        params: Mapping[str, object],
        context: Mapping[str, object],
    ) -> dict[str, object]:
        del context
        task = _optional_string(params.get("task"))
        if task is None:
            return {"status": "error", "error": "task is required"}
        requested_mode = _optional_string(params.get("mode"))
        thread_requested = params.get("thread") is True
        mode = requested_mode if requested_mode in {"run", "session"} else (
            "session" if thread_requested else "run"
        )
        if mode == "session" and not thread_requested:
            return {
                "status": "error",
                "errorCode": "thread_required",
                "error": (
                    'mode="session" requires thread=true so the ACP session can stay '
                    "bound to a thread."
                ),
            }
        instance_id = await self._select_instance_id()
        if instance_id is None:
            return {
                "status": "error",
                "error": "runtime=acp sessions_spawn requires a connected Codex instance.",
            }
        cwd = _optional_string(params.get("cwd"))
        resume_session_id = _optional_string(params.get("resumeSessionId"))
        try:
            thread_id: str | None
            if resume_session_id is not None:
                thread_id = resume_session_id
            else:
                thread_result = await self._manager.start_thread(
                    instance_id,
                    model=self._default_model,
                    cwd=cwd,
                    reasoning_effort=None,
                    collaboration_mode=None,
                )
                thread_id = _read_thread_id(thread_result)
                if thread_id is None:
                    return {
                        "status": "error",
                        "error": "ACP runtime did not return a thread id.",
                    }
            turn_result = await self._manager.start_turn(
                instance_id,
                thread_id=thread_id,
                text=task,
                cwd=cwd,
                model=None,
                reasoning_effort=None,
                collaboration_mode=None,
            )
        except Exception as exc:  # noqa: BLE001 - surface runtime failures to tool callers.
            return {
                "status": "error",
                "error": str(exc).strip() or type(exc).__name__,
            }

        run_id = extract_turn_id(turn_result) or thread_id
        child_session_key = f"agent:main:acp:{thread_id}"
        return {
            "status": "accepted",
            "childSessionKey": child_session_key,
            "runId": run_id,
            "mode": mode,
            "runtimeThreadId": thread_id,
            "runtimeSessionId": thread_id,
        }

    async def _select_instance_id(self) -> int | None:
        views = await self._manager.list_views()
        fallback: int | None = None
        for view in views:
            instance_id = getattr(view, "id", None)
            if isinstance(instance_id, int) and fallback is None:
                fallback = instance_id
            if (
                isinstance(instance_id, int)
                and getattr(view, "connected", False)
                and getattr(view, "initialized", False)
            ):
                return instance_id
        return fallback

    async def cancel_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
    ) -> dict[str, object]:
        del session_key, runtime_session_id, reason
        if runtime_thread_id is None:
            return {"status": "ok", "cancelled": False, "reason": "missing_runtime_thread_id"}
        instance_id = await self._select_instance_id()
        if instance_id is None:
            return {"status": "ok", "cancelled": False, "reason": "runtime_unavailable"}
        result = await self._manager.interrupt_turn(instance_id, runtime_thread_id)
        cancelled = bool(result.get("ok")) if isinstance(result, dict) else True
        return {"status": "ok", "cancelled": cancelled}

    async def close_session(
        self,
        *,
        session_key: str,
        runtime_thread_id: str | None,
        runtime_session_id: str | None,
        reason: str,
        discard_persistent_state: bool,
        require_acp_session: bool,
        allow_backend_unavailable: bool,
    ) -> dict[str, object]:
        del (
            session_key,
            runtime_thread_id,
            runtime_session_id,
            reason,
            discard_persistent_state,
            require_acp_session,
            allow_backend_unavailable,
        )
        return {"status": "ok", "closed": True}
