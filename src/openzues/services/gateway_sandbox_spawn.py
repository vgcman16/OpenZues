from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from openzues.services.codex_rpc import extract_turn_id

FORBIDDEN_SANDBOX_RUNTIME_UNAVAILABLE = (
    'sessions_spawn sandbox="require" needs a sandboxed target runtime. '
    'Pick a sandboxed agentId or use sandbox="inherit".'
)
WORKSPACE_WRITE_SANDBOX_POLICY: dict[str, str] = {"type": "workspaceWrite"}
READ_ONLY_SANDBOX_POLICY: dict[str, str] = {"type": "readOnly"}


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


def _sandbox_policy_for_mode(sandbox_mode: str) -> dict[str, str]:
    if sandbox_mode == "read-only":
        return dict(READ_ONLY_SANDBOX_POLICY)
    return dict(WORKSPACE_WRITE_SANDBOX_POLICY)


class RuntimeManagerSandboxChatSendService:
    def __init__(
        self,
        manager: Any,
        *,
        default_model: str = "gpt-5.4",
        sandbox_mode: str = "workspace-write",
    ) -> None:
        self._manager = manager
        self._default_model = default_model
        self._sandbox_mode = sandbox_mode

    async def __call__(self, **kwargs: object) -> dict[str, object]:
        session_key = _optional_string(kwargs.get("session_key"))
        message = _optional_string(kwargs.get("message"))
        if session_key is None:
            return {"status": "error", "error": "session_key is required"}
        if message is None:
            return {"status": "error", "error": "message is required"}
        if kwargs.get("sandbox") != "require":
            return {"status": "error", "error": 'sandbox_chat_send requires sandbox="require"'}

        sandbox_mode = _optional_string(kwargs.get("sandbox_mode")) or self._sandbox_mode
        instance_id = await self._select_instance_id()
        if instance_id is None:
            return {
                "status": "forbidden",
                "error": FORBIDDEN_SANDBOX_RUNTIME_UNAVAILABLE,
            }
        cwd = _optional_string(kwargs.get("cwd"))
        try:
            thread_result = await self._manager.start_thread(
                instance_id,
                model=self._default_model,
                cwd=cwd,
                reasoning_effort=None,
                collaboration_mode=None,
                sandbox_mode=sandbox_mode,
            )
            thread_id = _read_thread_id(thread_result)
            if thread_id is None:
                return {
                    "status": "error",
                    "error": "Sandbox runtime did not return a thread id.",
                }
            turn_result = await self._manager.start_turn(
                instance_id,
                thread_id=thread_id,
                text=message,
                cwd=cwd,
                model=None,
                reasoning_effort=None,
                collaboration_mode=None,
                sandbox_mode=sandbox_mode,
            )
        except Exception as exc:  # noqa: BLE001 - surface runtime failures to tool callers.
            return {
                "status": "error",
                "error": str(exc).strip() or type(exc).__name__,
            }

        return {
            "status": "ok",
            "runId": extract_turn_id(turn_result)
            or _optional_string(kwargs.get("idempotency_key"))
            or thread_id,
            "runtime": "codex-app-server",
            "runtimeId": instance_id,
            "runtimeThreadId": thread_id,
            "runtimeSessionId": thread_id,
            "sandboxed": True,
            "sandboxMode": sandbox_mode,
            "sandboxPolicy": _sandbox_policy_for_mode(sandbox_mode),
        }

    async def _select_instance_id(self) -> int | None:
        views = await self._manager.list_views()
        for view in views:
            instance_id = getattr(view, "id", None)
            if (
                isinstance(instance_id, int)
                and getattr(view, "connected", False)
                and getattr(view, "initialized", False)
            ):
                return instance_id
        return None


def sandbox_runtime_metadata(payload: Mapping[str, object]) -> dict[str, object]:
    metadata: dict[str, object] = {}
    for key in ("runtime", "runtimeThreadId", "runtimeSessionId", "sandboxMode"):
        value = _optional_string(payload.get(key))
        if value is not None:
            metadata[key] = value
    runtime_id = payload.get("runtimeId")
    if isinstance(runtime_id, int) and not isinstance(runtime_id, bool):
        metadata["runtimeId"] = runtime_id
    sandboxed = payload.get("sandboxed")
    if isinstance(sandboxed, bool):
        metadata["sandboxed"] = sandboxed
    sandbox_policy = payload.get("sandboxPolicy")
    if isinstance(sandbox_policy, dict):
        metadata["sandboxPolicy"] = dict(sandbox_policy)
    return metadata
