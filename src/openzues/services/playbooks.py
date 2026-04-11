from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from openzues.schemas import PlaybookKind, PlaybookRun, PlaybookRunResult
from openzues.services.codex_rpc import extract_thread_id, split_args
from openzues.services.manager import RuntimeManager


class SafeVariables(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(template: str, variables: dict[str, str]) -> str:
    return template.format_map(SafeVariables(variables))


def resolve_thread_id(payload: dict[str, Any]) -> str | None:
    if isinstance(payload.get("threadId"), str):
        return payload["threadId"]
    maybe_thread = payload.get("thread")
    if isinstance(maybe_thread, dict) and isinstance(maybe_thread.get("id"), str):
        return maybe_thread["id"]
    return extract_thread_id(payload)


def summarize_playbook_result(
    playbook: dict[str, Any],
    result: PlaybookRunResult,
) -> str:
    name = str(playbook.get("name") or "Playbook")
    kind = result.kind.replace("_", " ")
    detail = f"Ran {name} ({kind}) on instance {result.resolved_instance_id}"
    if result.thread_id:
        detail += f" using {result.thread_id}"
    exit_code = result.result.get("exitCode") if isinstance(result.result, dict) else None
    if isinstance(exit_code, int):
        detail += f" with exit code {exit_code}"
    return f"{detail}."


@dataclass(slots=True)
class PlaybookService:
    async def execute(
        self,
        playbook: dict[str, Any],
        run: PlaybookRun,
        manager: RuntimeManager,
    ) -> PlaybookRunResult:
        instance_id = run.instance_id or playbook.get("instance_id")
        if instance_id is None:
            raise ValueError(
                "Playbook requires an instance_id either on the playbook or at run time."
            )

        variables = self._build_variables(playbook, run, instance_id)
        rendered_template = render_template(playbook["template"], variables)
        resolved_cwd = self._resolve_optional_template(run.cwd or playbook.get("cwd"), variables)
        kind = cast(PlaybookKind, playbook["kind"])

        if kind == "command":
            result = await manager.exec_command(
                instance_id,
                command=split_args(rendered_template),
                cwd=resolved_cwd,
                timeout_ms=playbook.get("timeout_ms"),
                tty=False,
            )
            return PlaybookRunResult(
                kind=kind,
                rendered_template=rendered_template,
                resolved_instance_id=instance_id,
                resolved_cwd=resolved_cwd,
                result=result,
            )

        if kind == "turn":
            thread_id = self._require_thread_id(playbook, run, variables)
            result = await manager.start_turn(
                instance_id,
                thread_id=thread_id,
                text=rendered_template,
                cwd=resolved_cwd,
                model=playbook.get("model"),
                reasoning_effort=playbook.get("reasoning_effort"),
                collaboration_mode=playbook.get("collaboration_mode"),
            )
            return PlaybookRunResult(
                kind=kind,
                rendered_template=rendered_template,
                resolved_instance_id=instance_id,
                resolved_cwd=resolved_cwd,
                thread_id=thread_id,
                result=result,
            )

        if kind == "thread_turn":
            thread_result = await manager.start_thread(
                instance_id,
                model=playbook.get("model") or "gpt-5.4",
                cwd=resolved_cwd,
                reasoning_effort=playbook.get("reasoning_effort"),
                collaboration_mode=playbook.get("collaboration_mode"),
            )
            created_thread_id = resolve_thread_id(thread_result)
            if created_thread_id is None:
                raise ValueError("Could not determine thread id from thread/start response.")
            result = await manager.start_turn(
                instance_id,
                thread_id=created_thread_id,
                text=rendered_template,
                cwd=resolved_cwd,
                model=playbook.get("model"),
                reasoning_effort=playbook.get("reasoning_effort"),
                collaboration_mode=playbook.get("collaboration_mode"),
            )
            return PlaybookRunResult(
                kind=kind,
                rendered_template=rendered_template,
                resolved_instance_id=instance_id,
                resolved_cwd=resolved_cwd,
                thread_id=created_thread_id,
                result={"thread": thread_result, "turn": result},
            )

        if kind == "review":
            thread_id = self._require_thread_id(playbook, run, variables)
            result = await manager.start_review(instance_id, thread_id)
            return PlaybookRunResult(
                kind=kind,
                rendered_template=rendered_template,
                resolved_instance_id=instance_id,
                resolved_cwd=resolved_cwd,
                thread_id=thread_id,
                result=result,
            )

        raise ValueError(f"Unsupported playbook kind: {kind}")

    def _resolve_optional_template(
        self,
        value: str | None,
        variables: dict[str, str],
    ) -> str | None:
        if value is None:
            return None
        return render_template(value, variables)

    def _require_thread_id(
        self,
        playbook: dict[str, Any],
        run: PlaybookRun,
        variables: dict[str, str],
    ) -> str:
        raw_thread = run.thread_id or playbook.get("thread_id")
        if not raw_thread:
            raise ValueError("This playbook requires a thread_id.")
        return render_template(raw_thread, variables)

    def _build_variables(
        self,
        playbook: dict[str, Any],
        run: PlaybookRun,
        instance_id: int,
    ) -> dict[str, str]:
        now = datetime.now(UTC)
        variables: dict[str, str] = {
            "date": now.date().isoformat(),
            "datetime": now.isoformat(),
            "instance_id": str(instance_id),
            "playbook_name": str(playbook["name"]),
            "thread_id": run.thread_id or playbook.get("thread_id") or "",
            "cwd": run.cwd or playbook.get("cwd") or "",
        }
        raw_default_variables = playbook.get("default_variables")
        if isinstance(raw_default_variables, dict):
            variables.update(
                {
                    str(key): str(value)
                    for key, value in raw_default_variables.items()
                    if value is not None
                }
            )
        variables.update(run.variables)
        return variables
