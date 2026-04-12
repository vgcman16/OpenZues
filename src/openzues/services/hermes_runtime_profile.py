from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, TypedDict

from openzues.database import Database
from openzues.schemas import LaunchRouteStatus
from openzues.services.memory_protocol import is_mempalace_integration

DEFAULT_HERMES_MEMORY_PROVIDER = "openzues_recall"
DEFAULT_HERMES_EXECUTOR = "codex_desktop"

_MEMORY_PROVIDER_LABELS = {
    "openzues_recall": "OpenZues Recall",
    "mempalace": "MemPalace",
}
_EXECUTOR_LABELS = {
    "codex_desktop": "Codex Desktop Lanes",
    "workspace_shell": "Workspace Shell Profile",
    "docker": "Docker Backend",
    "ssh": "SSH Backend",
    "modal": "Modal Backend",
    "daytona": "Daytona Backend",
    "singularity": "Singularity Backend",
}
_EXTERNAL_EXECUTOR_COMMANDS = {
    "docker": "docker",
    "ssh": "ssh",
    "modal": "modal",
    "daytona": "daytona",
    "singularity": "singularity",
}


@dataclass(slots=True)
class ExecutorLaunchAssessment:
    status: LaunchRouteStatus
    summary: str
    warnings: list[str]


class MissionDraftRuntimeProfileFields(TypedDict):
    preferred_memory_provider: str
    preferred_memory_provider_label: str
    preferred_executor: str
    preferred_executor_label: str
    runtime_profile_summary: str


def _titleize_slug(value: str) -> str:
    return " ".join(part.capitalize() for part in value.replace("_", " ").split())


def memory_provider_label(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if not key:
        return _MEMORY_PROVIDER_LABELS[DEFAULT_HERMES_MEMORY_PROVIDER]
    return _MEMORY_PROVIDER_LABELS.get(key, _titleize_slug(key))


def executor_label(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if not key:
        return _EXECUTOR_LABELS[DEFAULT_HERMES_EXECUTOR]
    return _EXECUTOR_LABELS.get(key, _titleize_slug(key))


def _executor_key(value: str | None) -> str:
    key = str(value or "").strip().lower()
    return key or DEFAULT_HERMES_EXECUTOR


def _instance_transport(instance: Any | None) -> str:
    return str(getattr(instance, "transport", "") or "").strip().lower()


def _instance_cwd(instance: Any | None) -> str | None:
    cwd = str(getattr(instance, "cwd", "") or "").strip()
    return cwd or None


def _instance_connected(instance: Any | None) -> bool:
    return bool(getattr(instance, "connected", False))


def _instance_name(instance: Any | None) -> str | None:
    name = str(getattr(instance, "name", "") or "").strip()
    return name or None


def executor_candidate_rank(
    preferred_executor: str,
    *,
    instance: Any,
    target_cwd: str | None,
) -> tuple[int, int, int]:
    executor_key = _executor_key(preferred_executor)
    transport = _instance_transport(instance)
    has_workspace = bool(target_cwd or _instance_cwd(instance))
    if executor_key == "codex_desktop":
        return (0 if transport == "desktop" else 1, 0 if has_workspace else 1, 0)
    if executor_key == "workspace_shell" or executor_key in _EXTERNAL_EXECUTOR_COMMANDS:
        return (
            0 if transport == "stdio" else 1,
            0 if has_workspace else 1,
            0 if _instance_cwd(instance) else 1,
        )
    return (0, 0, 0)


def executor_candidate_supported(
    preferred_executor: str,
    *,
    instance: Any,
    target_cwd: str | None,
) -> bool:
    executor_key = _executor_key(preferred_executor)
    if executor_key == "workspace_shell":
        return bool(target_cwd or _instance_cwd(instance))
    command = _EXTERNAL_EXECUTOR_COMMANDS.get(executor_key)
    if command is not None:
        return shutil.which(command) is not None and bool(target_cwd or _instance_cwd(instance))
    return True


def build_executor_launch_assessment(
    preferred_executor: str,
    *,
    instance: Any | None,
    instances: Iterable[Any] = (),
    target_cwd: str | None = None,
) -> ExecutorLaunchAssessment:
    executor_key = _executor_key(preferred_executor)
    label = executor_label(executor_key)
    workspace_cwd = target_cwd or _instance_cwd(instance)
    connected = _instance_connected(instance)
    name = _instance_name(instance) or "the selected lane"
    available_instances = tuple(instances)

    if executor_key == "codex_desktop":
        if instance is None:
            return ExecutorLaunchAssessment(
                status="staged",
                summary=(
                    "Codex Desktop execution is preferred, but no launch lane is resolved yet."
                ),
                warnings=[],
            )
        if _instance_transport(instance) == "desktop":
            return ExecutorLaunchAssessment(
                status="ready" if connected else "staged",
                summary=(
                    f"{label} is satisfied on {name}."
                    if connected
                    else f"{label} is pinned to {name}, but that lane is not connected yet."
                ),
                warnings=[],
            )
        if any(
            _instance_connected(candidate) and _instance_transport(candidate) == "desktop"
            for candidate in available_instances
        ):
            transport_label = _instance_transport(instance) or "a non-desktop"
            return ExecutorLaunchAssessment(
                status="staged",
                summary=(
                    f"{label} prefers a desktop lane, and a desktop-capable lane is available "
                    "for re-routing."
                ),
                warnings=[
                    f"The current route points at {transport_label} transport even though a "
                    "desktop lane is available."
                ],
            )
        return ExecutorLaunchAssessment(
            status="ready" if connected else "staged",
            summary=(
                f"{label} is falling back to {name} because no connected desktop lane is "
                "available right now."
            ),
            warnings=[
                "No connected desktop lane is available, so OpenZues is using the best live "
                "fallback."
            ],
        )

    if executor_key == "workspace_shell":
        if not workspace_cwd:
            return ExecutorLaunchAssessment(
                status="repair",
                summary=(
                    f"{label} needs a concrete workspace path before OpenZues can launch "
                    "the mission."
                ),
                warnings=["Add a project path or saved lane cwd before retrying this launch."],
            )
        if instance is None:
            return ExecutorLaunchAssessment(
                status="staged",
                summary=(f"{label} has a workspace target, but no eligible lane is resolved yet."),
                warnings=[],
            )
        if not connected:
            return ExecutorLaunchAssessment(
                status="staged",
                summary=(
                    f"{label} is waiting for {name} to reconnect before shell-first launch can "
                    "start."
                ),
                warnings=[],
            )
        if _instance_transport(instance) == "stdio":
            return ExecutorLaunchAssessment(
                status="ready",
                summary=f"{label} is ready on {name} with a concrete workspace anchor.",
                warnings=[],
            )
        return ExecutorLaunchAssessment(
            status="ready",
            summary=(
                f"{label} is ready to promote `{workspace_cwd}` into a shell-backed lane "
                f"through {name}."
            ),
            warnings=[],
        )

    command = _EXTERNAL_EXECUTOR_COMMANDS.get(executor_key)
    if command is not None:
        if shutil.which(command) is None:
            return ExecutorLaunchAssessment(
                status="repair",
                summary=(
                    f"{label} needs the `{command}` command available on the host before launch "
                    "can be armed."
                ),
                warnings=[f"Install or expose `{command}` before retrying this executor profile."],
            )
        if not workspace_cwd:
            return ExecutorLaunchAssessment(
                status="repair",
                summary=(
                    f"{label} needs a concrete workspace path before backend orchestration can "
                    "launch."
                ),
                warnings=["Save a project path or lane cwd before retrying this executor profile."],
            )
        if instance is None:
            return ExecutorLaunchAssessment(
                status="staged",
                summary=(
                    f"{label} prerequisites are present, but no connected control lane is "
                    "resolved yet."
                ),
                warnings=[],
            )
        if not connected:
            return ExecutorLaunchAssessment(
                status="staged",
                summary=(
                    f"{label} is configured, but {name} still needs to reconnect before launch "
                    "can start."
                ),
                warnings=[],
            )
        return ExecutorLaunchAssessment(
            status="ready",
            summary=(
                f"{label} prerequisites are present, so OpenZues can stage this launch through "
                f"{name} with workspace `{workspace_cwd}`."
            ),
            warnings=[],
        )

    return ExecutorLaunchAssessment(
        status="ready" if instance is not None and connected else "staged",
        summary=f"{label} is staged for the current launch profile.",
        warnings=[],
    )


async def load_saved_runtime_preferences(
    database: Database | None,
) -> tuple[str, str]:
    if database is None:
        return DEFAULT_HERMES_MEMORY_PROVIDER, DEFAULT_HERMES_EXECUTOR
    row = await database.get_hermes_runtime_profile()
    profile = row.get("profile") if isinstance(row, dict) else None
    if not isinstance(profile, dict):
        return DEFAULT_HERMES_MEMORY_PROVIDER, DEFAULT_HERMES_EXECUTOR
    preferred_memory_provider = (
        str(profile.get("preferred_memory_provider") or DEFAULT_HERMES_MEMORY_PROVIDER).strip()
        or DEFAULT_HERMES_MEMORY_PROVIDER
    )
    preferred_executor = (
        str(profile.get("preferred_executor") or DEFAULT_HERMES_EXECUTOR).strip()
        or DEFAULT_HERMES_EXECUTOR
    )
    return preferred_memory_provider, preferred_executor


def build_runtime_profile_summary(
    *,
    preferred_memory_provider: str,
    preferred_executor: str,
) -> str:
    return (
        f"Hermes runtime posture prefers {memory_provider_label(preferred_memory_provider)} "
        f"for memory and {executor_label(preferred_executor)} for execution."
    )


def build_runtime_profile_fields(
    *,
    preferred_memory_provider: str,
    preferred_executor: str,
) -> MissionDraftRuntimeProfileFields:
    return {
        "preferred_memory_provider": preferred_memory_provider,
        "preferred_memory_provider_label": memory_provider_label(preferred_memory_provider),
        "preferred_executor": preferred_executor,
        "preferred_executor_label": executor_label(preferred_executor),
        "runtime_profile_summary": build_runtime_profile_summary(
            preferred_memory_provider=preferred_memory_provider,
            preferred_executor=preferred_executor,
        ),
    }


def build_memory_provider_lines(
    preferred_memory_provider: str,
    *,
    integrations: Iterable[Any] = (),
    toolsets: Iterable[str] = (),
) -> list[str]:
    provider_key = str(preferred_memory_provider or DEFAULT_HERMES_MEMORY_PROVIDER).strip().lower()
    toolset_set = {
        str(toolset or "").strip().lower() for toolset in toolsets if str(toolset or "").strip()
    }
    if provider_key == "openzues_recall":
        return [
            "Preferred memory provider: OpenZues Recall.",
            (
                "- Search saved missions, checkpoints, and continuity packets before "
                "re-deriving prior decisions or repeating uncertainty."
            ),
        ]

    if provider_key == "mempalace":
        integrated = any(is_mempalace_integration(integration) for integration in integrations)
        lines = [
            "Preferred memory provider: MemPalace.",
            (
                "- Use MemPalace-oriented recall first for historical context and durable "
                "writeback checks before claiming memory is anchored."
            ),
        ]
        if integrated or "memory" in toolset_set or "session_search" in toolset_set:
            lines.append(
                "- After any writeback, verify the memory can be recalled again before "
                "treating the handoff as durable."
            )
        else:
            lines.append(
                "- If the MemPalace surface is not live on this lane, fall back to OpenZues "
                "Recall and name the missing provider step explicitly."
            )
        return lines

    return [
        f"Preferred memory provider: {memory_provider_label(provider_key)}.",
        (
            "- Treat this provider as the target memory contract. If provider-specific tooling "
            "is not live on the current lane, fall back to OpenZues Recall and leave the gap "
            "explicit instead of silently pretending parity exists."
        ),
    ]


def build_executor_profile_lines(
    preferred_executor: str,
    *,
    instance_name: str | None = None,
    cwd: str | None = None,
    runtime_profile: dict[str, Any] | None = None,
) -> list[str]:
    executor_key = str(preferred_executor or DEFAULT_HERMES_EXECUTOR).strip().lower()
    executor_profiles_raw = (
        runtime_profile.get("executor_profiles") if isinstance(runtime_profile, dict) else None
    )
    executor_profiles: dict[str, Any] = (
        executor_profiles_raw if isinstance(executor_profiles_raw, dict) else {}
    )
    if executor_key == "codex_desktop":
        lines = [
            "Preferred executor profile: Codex Desktop Lanes.",
            "- Use the connected Codex lane as the authoritative runtime for this cycle.",
        ]
        if cwd:
            lines.append(
                f"- Keep the working directory anchored on `{cwd}` unless the thread proves "
                "a better target."
            )
        return lines

    if executor_key == "workspace_shell":
        lines = [
            "Preferred executor profile: Workspace Shell Profile.",
            (
                "- Prefer shell-first execution in the saved workspace: inspect files, run "
                "verification, and prove changes locally before broadening into higher-level "
                "or browser-only exploration."
            ),
            (
                "- If no shell-backed lane is armed yet, create or reuse one for the current "
                "workspace before the next long run."
            ),
        ]
        if instance_name:
            lines.append(f"- Current shell-facing lane: {instance_name}.")
        if cwd:
            lines.append(f"- Primary shell workspace: `{cwd}`.")
        return lines

    if executor_key == "docker":
        docker_profile_raw = executor_profiles.get("docker")
        docker_profile: dict[str, Any] = (
            docker_profile_raw if isinstance(docker_profile_raw, dict) else {}
        )
        docker_cwd = str(docker_profile.get("cwd") or cwd or "").strip() or None
        docker_image = str(docker_profile.get("image") or "").strip() or None
        mount_workspace = bool(docker_profile.get("mount_workspace"))
        preflight_status = str(docker_profile.get("last_preflight_status") or "").strip()
        preflight_summary = str(docker_profile.get("last_preflight_summary") or "").strip()
        lines = [
            "Preferred executor profile: Docker Backend.",
            (
                "- Keep container assumptions explicit: treat the control lane as the staging "
                "surface, and surface missing Docker prerequisites immediately instead of "
                "pretending local shell execution is equivalent."
            ),
        ]
        if docker_cwd and docker_image:
            lines.append(f"- Docker staging is armed for `{docker_cwd}` on image `{docker_image}`.")
        else:
            lines.append(
                "- Arm the Docker backend with a concrete workspace and image before the next "
                "long run."
            )
        if preflight_summary:
            lines.append(f"- Latest Docker preflight: {preflight_summary}")
        elif preflight_status == "ready":
            lines.append("- Docker preflight last passed for the staged backend profile.")
        lines.append(
            "- Workspace mounting is enabled for the staged container profile."
            if mount_workspace
            else (
                "- Use isolated container defaults unless workspace mounting is "
                "explicitly enabled."
            )
        )
        if instance_name:
            lines.append(f"- Current control lane for Docker staging: {instance_name}.")
        return lines

    return [
        f"Preferred executor profile: {executor_label(executor_key)}.",
        (
            "- Full backend handoff for this executor is not wired yet, so emulate its "
            "discipline on the current lane: keep environment assumptions explicit, surface "
            "missing backend prerequisites as blockers, and do not silently fall back to a "
            "different runtime contract."
        ),
    ]
