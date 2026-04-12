from __future__ import annotations

import asyncio
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

from openzues.database import Database, utcnow
from openzues.schemas import (
    HermesCapabilityDeckView,
    HermesCapabilityItemView,
    HermesDoctorView,
    HermesExecutorArmResultView,
    HermesExecutorPreflightView,
    HermesExecutorProfileStateView,
    HermesLearningPromotionCandidateView,
    HermesPromotionLoopView,
    HermesRuntimeProfileUpdate,
    HermesRuntimeProfileView,
    HermesUpdateView,
    InstanceView,
    ProjectView,
    TaskBlueprintView,
)
from openzues.services.cortex import build_doctrines, build_learning_reviews
from openzues.services.gateway_bootstrap import GatewayBootstrapService
from openzues.services.hermes_toolsets import infer_hermes_toolsets
from openzues.services.hub import BroadcastHub
from openzues.services.manager import RuntimeManager
from openzues.services.memory_protocol import (
    MEMPALACE_REQUIRED_TOOLS,
    is_mempalace_integration,
)
from openzues.services.missions import MissionService
from openzues.services.projects import ProjectService
from openzues.services.runtime_updates import RuntimeUpdateService
from openzues.settings import Settings

logger = logging.getLogger(__name__)

_PROFILE_DEFAULTS: dict[str, Any] = {
    "preferred_memory_provider": "openzues_recall",
    "preferred_executor": "codex_desktop",
    "learning_autopromote_enabled": True,
    "plugin_discovery_enabled": True,
    "channel_inventory_enabled": True,
    "acp_inventory_enabled": True,
    "executor_profiles": {},
    "promotion_history": {},
    "last_learning_promotion_at": None,
    "last_learning_fingerprint": None,
}
_DEFAULT_DOCKER_IMAGE = "nikolaik/python-nodejs:python3.11-nodejs20"
_DELIVERY_PLATFORM_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("gateway_api", "Gateway API + Webhooks", ("api_server", "webhook", "email")),
    (
        "consumer_chat",
        "Chat Delivery Adapters",
        ("telegram", "telegram_network", "discord", "slack", "mattermost", "matrix"),
    ),
    ("private_chat", "Private Messaging Adapters", ("signal", "sms", "whatsapp")),
    ("enterprise_chat", "Enterprise Chat Adapters", ("feishu", "wecom", "dingtalk", "weixin")),
    ("home_surfaces", "Home + Device Surfaces", ("homeassistant",)),
)
_CHANNEL_LABEL_OVERRIDES = {
    "api_server": "API Server",
    "homeassistant": "Home Assistant",
    "mattermost": "Mattermost",
    "telegram_network": "Telegram Network",
    "wecom": "WeCom",
    "weixin": "Weixin",
}


def _titleize_slug(value: str) -> str:
    if value in _CHANNEL_LABEL_OVERRIDES:
        return _CHANNEL_LABEL_OVERRIDES[value]
    return " ".join(part.capitalize() for part in value.replace("_", " ").split())


def _catalog_names(value: Any) -> list[str]:
    names: list[str] = []
    if isinstance(value, dict):
        return [str(key).strip() for key in value if str(key).strip()]
    if not isinstance(value, list):
        return names
    for item in value:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
            continue
        if not isinstance(item, dict):
            continue
        for key in ("name", "id", "uri", "method", "title"):
            raw = item.get(key)
            if isinstance(raw, str) and raw.strip():
                names.append(raw.strip())
                break
    return names


def _count_statuses(items: list[HermesCapabilityItemView]) -> dict[str, int]:
    counts = {"ready": 0, "partial": 0, "advisory": 0, "missing": 0}
    for item in items:
        counts[item.status] += 1
    return counts


def _build_deck(
    *,
    headline: str,
    summary: str,
    items: list[HermesCapabilityItemView],
) -> HermesCapabilityDeckView:
    counts = _count_statuses(items)
    return HermesCapabilityDeckView(
        headline=headline,
        summary=summary,
        ready_count=counts["ready"],
        partial_count=counts["partial"],
        advisory_count=counts["advisory"],
        missing_count=counts["missing"],
        items=items,
    )


def _discover_child_directories(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    names: list[str] = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir() or child.name.startswith("__"):
            continue
        names.append(child.name)
    return names


def _discover_platform_modules(path: Path | None) -> list[str]:
    if path is None or not path.exists():
        return []
    names: list[str] = []
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        if child.suffix != ".py" or child.stem.startswith("_"):
            continue
        if child.stem in {"__init__", "base", "helpers"}:
            continue
        names.append(child.stem)
    return names


def _which(name: str) -> bool:
    return shutil.which(name) is not None


async def _run_process_capture(
    *args: str,
    timeout_seconds: float = 20.0,
) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError:
        process.kill()
        await process.communicate()
        return 124, "", f"Timed out after {timeout_seconds:.0f}s"
    return (
        int(process.returncode or 0),
        stdout.decode("utf-8", errors="replace").strip(),
        stderr.decode("utf-8", errors="replace").strip(),
    )


def _normalize_cwd(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _source_label_for_executor_resolution(derived_from: str) -> str:
    return {
        "explicit": "the explicit workspace path",
        "gateway_default_cwd": "the saved gateway workspace",
        "gateway_project": "the gateway's preferred project",
        "single_project": "the single saved project",
        "connected_lane": "a connected lane workspace",
        "saved_lane": "a saved lane workspace",
    }.get(derived_from, derived_from.replace("_", " "))


def _executor_profiles_payload(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = profile.get("executor_profiles")
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        normalized[str(key)] = dict(value)
    return normalized


def _merge_toolsets(existing: list[str], recommended: list[str]) -> list[str]:
    ordered: list[str] = []
    for item in [*existing, *recommended]:
        text = str(item or "").strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered


def _pick_preferred_key(
    items: list[HermesCapabilityItemView],
    desired: str | None,
    *,
    fallback: str,
) -> str:
    item_keys = {item.key for item in items}
    if desired and desired in item_keys:
        return desired
    for status in ("ready", "partial", "advisory"):
        for item in items:
            if item.status == status:
                return item.key
    return fallback


def _label_for_key(items: list[HermesCapabilityItemView], key: str) -> str:
    for item in items:
        if item.key == key:
            return item.label
    return key


def _mempalace_tools_ready(instances: list[InstanceView]) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    for instance in instances:
        for server in instance.mcp_servers:
            server_name = str(server.get("name") or server.get("source") or "").strip()
            tool_names = set(_catalog_names(server.get("tools")))
            if "mempalace" not in server_name.lower() and not tool_names.intersection(
                set(MEMPALACE_REQUIRED_TOOLS)
            ):
                continue
            if all(tool in tool_names for tool in MEMPALACE_REQUIRED_TOOLS):
                evidence.append(f"{instance.name} exposes {', '.join(MEMPALACE_REQUIRED_TOOLS)}.")
                return True, evidence
            missing = [
                tool_name for tool_name in MEMPALACE_REQUIRED_TOOLS if tool_name not in tool_names
            ]
            evidence.append(
                f"{instance.name} is missing {', '.join(missing)} on the live MemPalace lane."
            )
    return False, evidence


class HermesPlatformService:
    def __init__(
        self,
        database: Database,
        manager: RuntimeManager,
        mission_service: MissionService,
        project_service: ProjectService,
        gateway_bootstrap: GatewayBootstrapService,
        settings: Settings,
        *,
        runtime_updates: RuntimeUpdateService | None = None,
        hub: BroadcastHub | None = None,
        poll_interval_seconds: int = 300,
    ) -> None:
        self.database = database
        self.manager = manager
        self.mission_service = mission_service
        self.project_service = project_service
        self.gateway_bootstrap = gateway_bootstrap
        self.settings = settings
        self.runtime_updates = runtime_updates
        self.hub = hub
        self.poll_interval_seconds = max(60, int(poll_interval_seconds))
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._promotion_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._runner_loop(),
            name="openzues-hermes-platform",
        )

    async def close(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def arm_workspace_shell(
        self,
        *,
        cwd: str | None = None,
        auto_connect: bool = False,
    ) -> HermesExecutorArmResultView:
        resolved_cwd, derived_from = await self._resolve_workspace_shell_cwd(cwd)
        if resolved_cwd is None:
            raise ValueError(
                "Workspace Shell Profile needs a concrete workspace path. Save a project, "
                "bootstrap the gateway, or pass a cwd explicitly."
            )

        existing_ids = {
            instance.id
            for instance in await self.manager.list_views()
            if instance.transport == "stdio"
            and str(instance.cwd or "").strip().lower() == resolved_cwd.lower()
        }
        runtime = await self.manager.ensure_workspace_shell_instance(
            cwd=resolved_cwd,
            auto_connect=auto_connect,
        )
        instance_view = runtime.view()
        created = instance_view.id not in existing_ids
        source_label = _source_label_for_executor_resolution(derived_from)
        state_label = "connected and ready" if instance_view.connected else "prepared for launch"
        return HermesExecutorArmResultView(
            headline="Workspace shell lane is armed",
            summary=(
                f"Workspace Shell Profile {'created' if created else 'reused'} "
                f"`{instance_view.name}` for `{resolved_cwd}` from {source_label}; the lane is "
                f"{state_label}."
            ),
            executor_key="workspace_shell",
            executor_label="Workspace Shell Profile",
            cwd=resolved_cwd,
            derived_from=derived_from,
            created=created,
            connected=instance_view.connected,
            instance=instance_view,
        )

    async def _resolve_docker_control_lane(
        self,
        *,
        cwd: str,
        auto_connect: bool,
    ) -> tuple[InstanceView, bool]:
        normalized_cwd = str(cwd).strip().lower()
        desktop_candidates = [
            instance
            for instance in await self.manager.list_views()
            if instance.transport == "desktop"
        ]

        def matches_workspace(instance: InstanceView) -> bool:
            return str(instance.cwd or "").strip().lower() == normalized_cwd

        preferred_desktop = next(
            (
                instance
                for instance in desktop_candidates
                if matches_workspace(instance) and instance.connected
            ),
            None,
        )
        if preferred_desktop is None:
            preferred_desktop = next(
                (instance for instance in desktop_candidates if matches_workspace(instance)),
                None,
            )
        if preferred_desktop is None:
            preferred_desktop = next(
                (instance for instance in desktop_candidates if instance.connected),
                None,
            )
        if preferred_desktop is None and desktop_candidates:
            preferred_desktop = desktop_candidates[0]

        if preferred_desktop is not None:
            runtime = await self.manager.get(preferred_desktop.id)
            if not runtime.cwd:
                runtime.cwd = cwd
            if auto_connect and not runtime.connected:
                runtime = await self.manager.connect_instance(runtime.instance_id)
            return runtime.view(), False

        if sys.platform.startswith("win"):
            runtime = await self.manager.create_instance(
                name="Local Codex Desktop",
                transport="desktop",
                command=None,
                args=None,
                websocket_url=None,
                cwd=cwd,
                auto_connect=False,
            )
            if auto_connect:
                runtime = await self.manager.connect_instance(runtime.instance_id)
            return runtime.view(), True

        existing_ids = {
            instance.id
            for instance in await self.manager.list_views()
            if instance.transport == "stdio"
            and str(instance.cwd or "").strip().lower() == normalized_cwd
        }
        runtime = await self.manager.ensure_workspace_shell_instance(
            cwd=cwd,
            auto_connect=auto_connect,
        )
        return runtime.view(), runtime.instance_id not in existing_ids

    async def arm_docker_backend(
        self,
        *,
        cwd: str | None = None,
        image: str | None = None,
        auto_connect: bool = False,
        mount_workspace: bool = False,
    ) -> HermesExecutorArmResultView:
        if not _which("docker"):
            raise ValueError(
                "Docker Backend needs the `docker` command available on the host before it can be armed."
            )

        resolved_cwd, derived_from = await self._resolve_workspace_shell_cwd(cwd)
        if resolved_cwd is None:
            raise ValueError(
                "Docker Backend needs a concrete workspace path. Save a project, bootstrap "
                "the gateway, or pass a cwd explicitly."
            )

        profile = await self._load_profile_payload()
        executor_profiles = _executor_profiles_payload(profile)
        previous_docker_profile = executor_profiles.get("docker", {})
        docker_image = (
            _normalize_cwd(image)
            or _normalize_cwd(previous_docker_profile.get("image"))
            or _DEFAULT_DOCKER_IMAGE
        )
        instance_view, created = await self._resolve_docker_control_lane(
            cwd=resolved_cwd,
            auto_connect=auto_connect,
        )
        armed_at = utcnow()
        executor_profiles["docker"] = {
            **previous_docker_profile,
            "cwd": resolved_cwd,
            "image": docker_image,
            "mount_workspace": bool(mount_workspace),
            "derived_from": derived_from,
            "control_instance_id": instance_view.id,
            "armed_at": armed_at,
            "last_checked_at": armed_at,
        }
        profile["executor_profiles"] = executor_profiles
        await self.database.upsert_hermes_runtime_profile(profile)

        source_label = _source_label_for_executor_resolution(derived_from)
        mount_clause = (
            "with workspace mount enabled"
            if mount_workspace
            else "with isolated container defaults"
        )
        state_label = (
            "connected for immediate staging"
            if instance_view.connected
            else "prepared for the next staged launch"
        )
        return HermesExecutorArmResultView(
            headline="Docker backend profile is armed",
            summary=(
                f"Docker Backend {'created' if created else 'reused'} control lane "
                f"`{instance_view.name}` for `{resolved_cwd}` from {source_label}, pinned "
                f"image `{docker_image}`, and saved {mount_clause}; the lane is {state_label}."
            ),
            executor_key="docker",
            executor_label="Docker Backend",
            cwd=resolved_cwd,
            derived_from=derived_from,
            created=created,
            connected=instance_view.connected,
            instance=instance_view,
            image=docker_image,
            mount_workspace=bool(mount_workspace),
        )

    async def preflight_docker_backend(
        self,
        *,
        cwd: str | None = None,
        image: str | None = None,
    ) -> HermesExecutorPreflightView:
        profile = await self._load_profile_payload()
        executor_profiles = _executor_profiles_payload(profile)
        previous_docker_profile = executor_profiles.get("docker", {})
        explicit_cwd = _normalize_cwd(cwd)
        if explicit_cwd is not None:
            resolved_cwd = explicit_cwd
            derived_from = "explicit"
        else:
            resolved_cwd = _normalize_cwd(previous_docker_profile.get("cwd"))
            derived_from = (
                str(previous_docker_profile.get("derived_from") or "").strip() or "profile"
            )
            if resolved_cwd is None:
                resolved_cwd, derived_from = await self._resolve_workspace_shell_cwd(None)

        docker_image = (
            _normalize_cwd(image)
            or _normalize_cwd(previous_docker_profile.get("image"))
            or _DEFAULT_DOCKER_IMAGE
        )
        command_path = shutil.which("docker")
        checked_at = utcnow()
        docker_version: str | None = None
        daemon_version: str | None = None
        image_present: bool | None = None
        status = "repair"
        headline = "Docker backend preflight needs repair"
        summary = "Docker preflight has not run yet."

        if command_path is None:
            summary = "Docker Backend needs the `docker` command available on the host before preflight can pass."
        elif resolved_cwd is None:
            summary = (
                "Docker Backend needs a concrete workspace path before preflight can validate the staged profile."
            )
        else:
            version_code, version_stdout, version_stderr = await _run_process_capture(
                command_path,
                "--version",
            )
            if version_code == 0:
                docker_version = version_stdout or None
            else:
                summary = version_stderr or version_stdout or "Docker CLI could not report its version."

            if docker_version is not None:
                info_code, info_stdout, info_stderr = await _run_process_capture(
                    command_path,
                    "info",
                    "--format",
                    "{{.ServerVersion}}",
                )
                if info_code == 0:
                    daemon_version = info_stdout or None
                else:
                    summary = (
                        info_stderr
                        or info_stdout
                        or "Docker daemon is not reachable from this host."
                    )

            if docker_version is not None and daemon_version is not None:
                inspect_code, inspect_stdout, inspect_stderr = await _run_process_capture(
                    command_path,
                    "image",
                    "inspect",
                    docker_image,
                    "--format",
                    "{{.Id}}",
                )
                if inspect_code == 0:
                    image_present = bool((inspect_stdout or "").strip())
                else:
                    image_present = False
                    summary = (
                        inspect_stderr
                        or inspect_stdout
                        or f"Docker image `{docker_image}` is not present locally yet."
                    )

            if docker_version is not None and daemon_version is not None:
                if image_present:
                    status = "ready"
                    headline = "Docker backend preflight passed"
                    summary = (
                        f"Docker CLI and daemon are reachable, and image `{docker_image}` is ready "
                        f"for workspace `{resolved_cwd}`."
                    )
                else:
                    status = "staged"
                    headline = "Docker backend preflight is staged"
                    summary = (
                        f"Docker CLI and daemon are reachable for workspace `{resolved_cwd}`, but "
                        f"image `{docker_image}` is not present locally yet."
                    )

        executor_profiles["docker"] = {
            **previous_docker_profile,
            "cwd": resolved_cwd,
            "image": docker_image,
            "derived_from": derived_from,
            "last_checked_at": checked_at,
            "last_preflight_status": status,
            "last_preflight_summary": summary,
            "command_path": command_path,
            "docker_version": docker_version,
            "daemon_version": daemon_version,
            "image_present": image_present,
        }
        profile["executor_profiles"] = executor_profiles
        await self.database.upsert_hermes_runtime_profile(profile)

        return HermesExecutorPreflightView(
            headline=headline,
            summary=summary,
            executor_key="docker",
            executor_label="Docker Backend",
            ok=status == "ready",
            status=status,  # type: ignore[arg-type]
            cwd=resolved_cwd,
            image=docker_image,
            derived_from=derived_from,
            command_path=command_path,
            docker_version=docker_version,
            daemon_version=daemon_version,
            image_present=image_present,
            checked_at=checked_at,
        )

    async def _runner_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.promote_learning()
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - defensive guard
                logger.exception("Hermes learning promotion loop crashed.")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def get_runtime_profile(self) -> HermesRuntimeProfileView:
        profile = await self._load_profile_payload()
        instances = await self.manager.list_views()
        missions = await self.mission_service.list_views()
        memory = await self._build_memory_deck(profile, instances, missions)
        executors = self._build_executor_deck(profile, instances)
        preferred_memory = _pick_preferred_key(
            memory.items,
            str(profile.get("preferred_memory_provider") or ""),
            fallback="openzues_recall",
        )
        preferred_executor = _pick_preferred_key(
            executors.items,
            str(profile.get("preferred_executor") or ""),
            fallback="codex_desktop",
        )
        history = profile.get("promotion_history", {})
        history_count = len(history) if isinstance(history, dict) else 0
        return HermesRuntimeProfileView(
            headline="Hermes runtime profile is staged",
            summary=(
                f"Auto-promote is {'on' if profile['learning_autopromote_enabled'] else 'off'}, "
                f"preferred memory is {_label_for_key(memory.items, preferred_memory)}, and "
                f"preferred executor is {_label_for_key(executors.items, preferred_executor)}."
            ),
            hermes_source_path=(
                str(self.settings.hermes_source_path) if self.settings.hermes_source_path else None
            ),
            preferred_memory_provider=preferred_memory,
            preferred_executor=preferred_executor,
            learning_autopromote_enabled=bool(profile["learning_autopromote_enabled"]),
            plugin_discovery_enabled=bool(profile["plugin_discovery_enabled"]),
            channel_inventory_enabled=bool(profile["channel_inventory_enabled"]),
            acp_inventory_enabled=bool(profile["acp_inventory_enabled"]),
            executor_profiles=self._build_executor_profile_states(profile, instances),
            promotion_history_count=history_count,
            last_learning_promotion_at=profile.get("last_learning_promotion_at"),
            last_learning_fingerprint=profile.get("last_learning_fingerprint"),
        )

    async def update_runtime_profile(
        self,
        payload: HermesRuntimeProfileUpdate,
    ) -> HermesRuntimeProfileView:
        profile = await self._load_profile_payload()
        instances = await self.manager.list_views()
        missions = await self.mission_service.list_views()
        memory = await self._build_memory_deck(profile, instances, missions)
        executors = self._build_executor_deck(profile, instances)
        memory_keys = {item.key for item in memory.items}
        executor_keys = {item.key for item in executors.items}

        if payload.preferred_memory_provider is not None:
            if payload.preferred_memory_provider not in memory_keys:
                raise ValueError(
                    f"Unknown Hermes memory provider: {payload.preferred_memory_provider}"
                )
            profile["preferred_memory_provider"] = payload.preferred_memory_provider
        if payload.preferred_executor is not None:
            if payload.preferred_executor not in executor_keys:
                raise ValueError(f"Unknown Hermes executor: {payload.preferred_executor}")
            profile["preferred_executor"] = payload.preferred_executor
        for field in (
            "learning_autopromote_enabled",
            "plugin_discovery_enabled",
            "channel_inventory_enabled",
            "acp_inventory_enabled",
        ):
            value = getattr(payload, field)
            if value is not None:
                profile[field] = bool(value)

        await self.database.upsert_hermes_runtime_profile(profile)
        return await self.get_runtime_profile()

    async def get_update_view(self) -> HermesUpdateView:
        snapshot = self.runtime_updates.snapshot() if self.runtime_updates is not None else {}
        enabled = bool(snapshot.get("enabled"))
        pending_restart = bool(snapshot.get("pending_restart"))
        safe_to_restart = bool(snapshot.get("safe_to_restart"))
        if not enabled:
            headline = "Runtime self-update is idle"
            summary = "OpenZues is not currently watching the repo for restart-safe self-updates."
        elif pending_restart and safe_to_restart:
            headline = "A newer repo revision is ready to restart"
            summary = (
                "OpenZues sees a newer checked-out revision and the mission lane is idle enough "
                "to restart safely."
            )
        elif pending_restart:
            headline = "A newer repo revision is waiting for a safe boundary"
            summary = (
                "OpenZues sees a newer checked-out revision, but it is still waiting for live "
                "missions to reach a restart-safe checkpoint."
            )
        else:
            headline = "Runtime self-update is watching the repo"
            summary = "The current process is aligned with the checked-out repo revision."
        return HermesUpdateView(
            headline=headline,
            summary=summary,
            enabled=enabled,
            repo_root=snapshot.get("repo_root"),
            startup_revision=snapshot.get("startup_revision"),
            current_revision=snapshot.get("current_revision"),
            pending_revision=snapshot.get("pending_revision"),
            pending_restart=pending_restart,
            restart_in_progress=bool(snapshot.get("restart_in_progress")),
            safe_to_restart=safe_to_restart,
            last_checked_at=snapshot.get("last_checked_at"),
            last_restart_at=snapshot.get("last_restart_at"),
            last_error=snapshot.get("last_error"),
            auto_restart=bool(snapshot.get("auto_restart")),
        )

    async def promote_learning(self) -> HermesPromotionLoopView:
        async with self._promotion_lock:
            return await self._build_promotion_loop(apply=True)

    async def get_doctor_view(self) -> HermesDoctorView:
        profile_payload = await self._load_profile_payload()
        instances = await self.manager.list_views()
        missions = await self.mission_service.list_views()
        promotion_loop = await self._build_promotion_loop(
            apply=False,
            profile_payload=profile_payload,
            instances=instances,
            missions=missions,
        )
        memory = await self._build_memory_deck(profile_payload, instances, missions)
        executors = self._build_executor_deck(profile_payload, instances)
        plugins = self._build_plugin_deck(profile_payload, instances)
        delivery = await self._build_delivery_deck(profile_payload)
        acp = self._build_acp_deck(profile_payload, instances)
        extras = self._build_extra_deck()
        updates = await self.get_update_view()
        preferred_memory = _pick_preferred_key(
            memory.items,
            str(profile_payload.get("preferred_memory_provider") or ""),
            fallback="openzues_recall",
        )
        preferred_executor = _pick_preferred_key(
            executors.items,
            str(profile_payload.get("preferred_executor") or ""),
            fallback="codex_desktop",
        )
        history = profile_payload.get("promotion_history", {})
        profile = HermesRuntimeProfileView(
            headline="Hermes runtime profile is staged",
            summary=(
                f"Preferred memory is {_label_for_key(memory.items, preferred_memory)} and "
                f"preferred executor is {_label_for_key(executors.items, preferred_executor)}."
            ),
            hermes_source_path=(
                str(self.settings.hermes_source_path) if self.settings.hermes_source_path else None
            ),
            preferred_memory_provider=preferred_memory,
            preferred_executor=preferred_executor,
            learning_autopromote_enabled=bool(profile_payload["learning_autopromote_enabled"]),
            plugin_discovery_enabled=bool(profile_payload["plugin_discovery_enabled"]),
            channel_inventory_enabled=bool(profile_payload["channel_inventory_enabled"]),
            acp_inventory_enabled=bool(profile_payload["acp_inventory_enabled"]),
            executor_profiles=self._build_executor_profile_states(profile_payload, instances),
            promotion_history_count=len(history) if isinstance(history, dict) else 0,
            last_learning_promotion_at=profile_payload.get("last_learning_promotion_at"),
            last_learning_fingerprint=profile_payload.get("last_learning_fingerprint"),
        )

        warnings: list[str] = []
        if (
            self.settings.hermes_source_path is None
            or not self.settings.hermes_source_path.exists()
        ):
            warnings.append(
                "Hermes source discovery is unavailable, so plugin/channel/provider inventory is "
                "falling back to built-in OpenZues seams only."
            )
        if not any(instance.connected for instance in instances):
            warnings.append(
                "No live Codex lane is connected, so executor and ACP posture are only "
                "partially armed."
            )
        if promotion_loop.pending_count and not profile.learning_autopromote_enabled:
            warnings.append(
                "Hermes learning promotions are pending, but auto-promote is disabled in "
                "the runtime profile."
            )
        if updates.pending_restart:
            warnings.append(updates.summary)

        level = "ready"
        if warnings or memory.missing_count or executors.missing_count:
            level = "warn"

        headline = (
            "Hermes parity kernel is active"
            if level == "ready"
            else "Hermes parity kernel needs a few more imports"
        )
        summary = (
            f"{promotion_loop.applied_count} learning promotion(s) are already applied, "
            f"{memory.ready_count + memory.partial_count} memory provider seam(s) are "
            "staged, and "
            f"{delivery.advisory_count + delivery.partial_count + delivery.ready_count} "
            "delivery surface(s) "
            "have been mapped from Hermes."
        )
        return HermesDoctorView(
            level=level,  # type: ignore[arg-type]
            headline=headline,
            summary=summary,
            warnings=warnings,
            profile=profile,
            promotion_loop=promotion_loop,
            memory=memory,
            executors=executors,
            plugins=plugins,
            delivery=delivery,
            acp=acp,
            extras=extras,
            updates=updates,
            checked_at=utcnow(),
        )

    async def _resolve_workspace_shell_cwd(
        self,
        explicit_cwd: str | None,
    ) -> tuple[str | None, str]:
        normalized = _normalize_cwd(explicit_cwd)
        if normalized is not None:
            return normalized, "explicit"

        gateway = await self.database.get_gateway_bootstrap()
        if gateway is not None:
            default_cwd = _normalize_cwd(gateway.get("default_cwd"))
            if default_cwd is not None:
                return default_cwd, "gateway_default_cwd"
            preferred_project_id = gateway.get("preferred_project_id")
            if preferred_project_id is not None:
                project = await self.database.get_project(int(preferred_project_id))
                if project is not None:
                    project_path = _normalize_cwd(project.get("path"))
                    if project_path is not None:
                        return project_path, "gateway_project"

        projects = await self.database.list_projects()
        if len(projects) == 1:
            project_path = _normalize_cwd(projects[0].get("path"))
            if project_path is not None:
                return project_path, "single_project"

        instances = await self.manager.list_views()
        connected_with_cwd = [
            instance for instance in instances if instance.connected and _normalize_cwd(instance.cwd)
        ]
        if connected_with_cwd:
            return str(connected_with_cwd[0].cwd), "connected_lane"
        saved_with_cwd = [instance for instance in instances if _normalize_cwd(instance.cwd)]
        if saved_with_cwd:
            return str(saved_with_cwd[0].cwd), "saved_lane"
        return None, "missing"

    async def _build_promotion_loop(
        self,
        *,
        apply: bool,
        profile_payload: dict[str, Any] | None = None,
        instances: list[InstanceView] | None = None,
        missions=None,
    ) -> HermesPromotionLoopView:
        profile = profile_payload or await self._load_profile_payload()
        current_missions = (
            missions if missions is not None else await self.mission_service.list_views()
        )
        project_rows = await self.database.list_projects()
        projects = [
            ProjectView.model_validate(self.project_service.inspect(row)) for row in project_rows
        ]
        doctrines = build_doctrines(current_missions, projects)
        reviews = build_learning_reviews(current_missions, projects, doctrines=doctrines)
        task_rows = await self.database.list_task_blueprints()
        tasks = [TaskBlueprintView.model_validate(row) for row in task_rows]
        tasks_by_project: dict[int, list[TaskBlueprintView]] = {}
        task_by_id: dict[int, TaskBlueprintView] = {}
        for task in tasks:
            task_by_id[task.id] = task
            if task.project_id is None or not task.enabled:
                continue
            tasks_by_project.setdefault(task.project_id, []).append(task)
        project_by_id = {project.id: project for project in projects}
        gateway_row = await self.database.get_gateway_bootstrap()
        current_target_toolsets: dict[tuple[str, int], list[str]] = {
            ("task_blueprint", task.id): list(task.toolsets or [])
            for task in tasks
        }
        if gateway_row is not None:
            current_target_toolsets[("gateway_bootstrap", 1)] = list(
                gateway_row.get("toolsets") or []
            )

        items: list[HermesLearningPromotionCandidateView] = []
        applied_count = 0
        already_armed_count = 0
        pending_count = 0
        history = profile.get("promotion_history")
        history = dict(history) if isinstance(history, dict) else {}
        changed = False
        last_applied_fingerprint = profile.get("last_learning_fingerprint")
        last_applied_at = profile.get("last_learning_promotion_at")

        for review in sorted(
            reviews,
            key=lambda item: (
                -item.evidence_count,
                (item.project_label or "").lower(),
                item.title.lower(),
            ),
        ):
            if review.project_id is None or not review.recommended_toolsets:
                continue
            recommended = list(review.recommended_toolsets)
            project = project_by_id.get(review.project_id)
            targets: list[tuple[str, int | None, str, list[str], str, str | None]] = []
            for task in tasks_by_project.get(review.project_id, []):
                targets.append(
                    (
                        "task_blueprint",
                        task.id,
                        task.name,
                        list(
                            current_target_toolsets.get(
                                ("task_blueprint", task.id),
                                list(task.toolsets or []),
                            )
                        ),
                        task.objective_template,
                        task.cwd or (project.path if project is not None else None),
                    )
                )
            if (
                gateway_row is not None
                and int(gateway_row.get("preferred_project_id") or -1) == review.project_id
            ):
                gateway_task = next(
                    (
                        task
                        for task in tasks
                        if gateway_row.get("task_blueprint_id") is not None
                        and task.id == int(gateway_row["task_blueprint_id"])
                    ),
                    None,
                )
                targets.append(
                    (
                        "gateway_bootstrap",
                        1,
                        "Saved Gateway Bootstrap",
                        list(
                            current_target_toolsets.get(
                                ("gateway_bootstrap", 1),
                                list(gateway_row.get("toolsets") or []),
                            )
                        ),
                        gateway_task.objective_template if gateway_task is not None else "",
                        str(
                            gateway_row.get("default_cwd")
                            or (project.path if project is not None else "")
                        )
                        or None,
                    )
                )
            for target_kind, target_id, target_label, existing_toolsets, objective, cwd in targets:
                fingerprint = (
                    f"{review.id}:{target_kind}:{target_id}:{','.join(sorted(recommended))}"
                )
                has_all_toolsets = all(toolset in existing_toolsets for toolset in recommended)
                applied_at = str(history.get(fingerprint) or "") or None
                status = "pending"
                if has_all_toolsets:
                    status = "already_armed"
                    already_armed_count += 1
                elif apply and bool(profile["learning_autopromote_enabled"]):
                    merged_toolsets = _merge_toolsets(existing_toolsets, recommended)
                    normalized_toolsets = infer_hermes_toolsets(
                        objective,
                        explicit_toolsets=merged_toolsets,
                        project_label=project.label if project is not None else None,
                        project_path=project.path if project is not None else cwd,
                        setup_mode="local",
                        use_builtin_agents=True,
                        run_verification=True,
                    )
                    if target_kind == "task_blueprint" and target_id is not None:
                        await self.database.update_task_blueprint_payload(
                            int(target_id),
                            toolsets=normalized_toolsets,
                        )
                        current_target_toolsets[("task_blueprint", int(target_id))] = list(
                            normalized_toolsets
                        )
                        task_row = task_by_id.get(int(target_id))
                        if task_row is not None:
                            task_row.toolsets = list(normalized_toolsets)
                    elif target_kind == "gateway_bootstrap" and gateway_row is not None:
                        await self.database.upsert_gateway_bootstrap(
                            setup_mode=str(gateway_row.get("setup_mode") or "local"),
                            setup_flow=str(gateway_row.get("setup_flow") or "quickstart"),
                            route_binding_mode=str(
                                gateway_row.get("route_binding_mode") or "saved_lane"
                            ),
                            preferred_instance_id=gateway_row.get("preferred_instance_id"),
                            preferred_project_id=gateway_row.get("preferred_project_id"),
                            team_id=gateway_row.get("team_id"),
                            operator_id=gateway_row.get("operator_id"),
                            task_blueprint_id=gateway_row.get("task_blueprint_id"),
                            last_route_instance_id=gateway_row.get("last_route_instance_id"),
                            last_route_resolved_at=gateway_row.get("last_route_resolved_at"),
                            default_cwd=gateway_row.get("default_cwd"),
                            model=str(gateway_row.get("model") or "gpt-5.4"),
                            max_turns=gateway_row.get("max_turns"),
                            use_builtin_agents=bool(gateway_row.get("use_builtin_agents", True)),
                            run_verification=bool(gateway_row.get("run_verification", True)),
                            auto_commit=bool(gateway_row.get("auto_commit", False)),
                            pause_on_approval=bool(gateway_row.get("pause_on_approval", True)),
                            allow_auto_reflexes=bool(gateway_row.get("allow_auto_reflexes", True)),
                            auto_recover=bool(gateway_row.get("auto_recover", True)),
                            auto_recover_limit=int(gateway_row.get("auto_recover_limit") or 2),
                            reflex_cooldown_seconds=int(
                                gateway_row.get("reflex_cooldown_seconds") or 900
                            ),
                            allow_failover=bool(gateway_row.get("allow_failover", True)),
                            toolsets=normalized_toolsets,
                        )
                        gateway_row["toolsets"] = normalized_toolsets
                        current_target_toolsets[("gateway_bootstrap", 1)] = list(
                            normalized_toolsets
                        )
                    applied_at = utcnow()
                    history[fingerprint] = applied_at
                    last_applied_fingerprint = fingerprint
                    last_applied_at = applied_at
                    status = "applied"
                    applied_count += 1
                    changed = True
                else:
                    pending_count += 1
                items.append(
                    HermesLearningPromotionCandidateView(
                        fingerprint=fingerprint,
                        status=status,  # type: ignore[arg-type]
                        title=review.title,
                        summary=review.summary,
                        target_kind=target_kind,  # type: ignore[arg-type]
                        target_id=target_id,
                        target_label=target_label,
                        recommended_toolsets=recommended,
                        evidence_count=review.evidence_count,
                        applied_at=applied_at,
                    )
                )

        if changed:
            profile["promotion_history"] = dict(sorted(history.items())[-128:])
            profile["last_learning_fingerprint"] = last_applied_fingerprint
            profile["last_learning_promotion_at"] = last_applied_at
            await self.database.upsert_hermes_runtime_profile(profile)
            if self.hub is not None:
                await self.hub.publish(
                    {
                        "type": "hermes/promotion/applied",
                        "createdAt": utcnow(),
                        "count": applied_count,
                        "fingerprint": last_applied_fingerprint,
                    }
                )

        if not items:
            return HermesPromotionLoopView(
                headline="Hermes learning promotion loop is idle",
                summary=(
                    "Zues has not accumulated enough durable repeated wins yet to safely promote "
                    "a stronger default posture."
                ),
                auto_apply=bool(profile["learning_autopromote_enabled"]),
                pending_count=0,
                applied_count=0,
                already_armed_count=0,
                items=[],
            )

        summary = (
            f"{applied_count} promotion(s) are already applied, {already_armed_count} target(s) "
            f"already carry the learned posture, and {pending_count} target(s) are waiting."
        )
        return HermesPromotionLoopView(
            headline="Hermes learning promotion loop is active",
            summary=summary,
            auto_apply=bool(profile["learning_autopromote_enabled"]),
            pending_count=pending_count,
            applied_count=applied_count,
            already_armed_count=already_armed_count,
            items=items[:12],
        )

    async def _build_memory_deck(
        self,
        profile: dict[str, Any],
        instances: list[InstanceView],
        missions,
    ) -> HermesCapabilityDeckView:
        integrations = await self.database.list_integrations()
        checkpoint_count = sum(len(mission.checkpoints) for mission in missions)
        items: list[HermesCapabilityItemView] = []

        recall_status = "ready" if missions or checkpoint_count else "partial"
        items.append(
            HermesCapabilityItemView(
                key="openzues_recall",
                label="OpenZues Recall",
                status=recall_status,  # type: ignore[arg-type]
                summary=(
                    f"Search is built into OpenZues across {len(missions)} mission(s) and "
                    f"{checkpoint_count} checkpoint(s)."
                ),
                capabilities=["checkpoint recall", "continuity packets", "session search"],
            )
        )

        mempalace_ready, mempalace_evidence = _mempalace_tools_ready(instances)
        mempalace_integrated = any(
            bool(integration.get("enabled", True)) and is_mempalace_integration(integration)
            for integration in integrations
        )
        if mempalace_ready:
            mempalace_status = "ready"
            mempalace_summary = (
                "MemPalace is staged and the live lane exposes the required memory MCP tools."
            )
        elif mempalace_integrated:
            mempalace_status = "partial"
            mempalace_summary = (
                "MemPalace is staged in OpenZues, but the current lane still needs a "
                "full live tool proof."
            )
        else:
            mempalace_status = "missing"
            mempalace_summary = "No MemPalace integration is currently staged in OpenZues."
        items.append(
            HermesCapabilityItemView(
                key="mempalace",
                label="MemPalace",
                status=mempalace_status,  # type: ignore[arg-type]
                summary=mempalace_summary,
                capabilities=list(MEMPALACE_REQUIRED_TOOLS),
                evidence=mempalace_evidence,
            )
        )

        provider_root = (
            self.settings.hermes_source_path / "plugins" / "memory"
            if self.settings.hermes_source_path is not None
            else None
        )
        for provider_name in _discover_child_directories(provider_root):
            matches_live_integration = any(
                provider_name in str(integration.get("kind") or "").lower()
                or provider_name in str(integration.get("name") or "").lower()
                for integration in integrations
            )
            status = "partial" if matches_live_integration else "advisory"
            summary = (
                "The Hermes source tree includes this provider and OpenZues can now inventory it "
                "as a candidate memory backend."
            )
            if matches_live_integration:
                summary = (
                    "A matching OpenZues integration exists, but provider-specific Hermes "
                    "runtime wiring is still advisory."
                )
            items.append(
                HermesCapabilityItemView(
                    key=provider_name,
                    label=_titleize_slug(provider_name),
                    status=status,  # type: ignore[arg-type]
                    summary=summary,
                    capabilities=["provider discovery", "future plugin import"],
                )
            )

        preferred_key = _pick_preferred_key(
            items,
            str(profile.get("preferred_memory_provider") or ""),
            fallback="openzues_recall",
        )
        items = [
            item.model_copy(update={"recommended": item.key == preferred_key}) for item in items
        ]
        return _build_deck(
            headline="Memory providers and recall seams are mapped",
            summary=f"Preferred memory provider is {_label_for_key(items, preferred_key)}.",
            items=items,
        )

    def _build_executor_deck(
        self,
        profile: dict[str, Any],
        instances: list[InstanceView],
    ) -> HermesCapabilityDeckView:
        connected_instances = [instance for instance in instances if instance.connected]
        instances_by_id = {instance.id: instance for instance in instances}
        shell_instances = [
            instance
            for instance in instances
            if instance.transport == "stdio" and bool(_normalize_cwd(instance.cwd))
        ]
        connected_shell_instances = [instance for instance in shell_instances if instance.connected]
        executor_profiles = _executor_profiles_payload(profile)
        docker_profile = executor_profiles.get("docker", {})
        docker_cwd = _normalize_cwd(docker_profile.get("cwd"))
        docker_image = _normalize_cwd(docker_profile.get("image"))
        docker_mount_workspace = bool(docker_profile.get("mount_workspace"))
        docker_control = instances_by_id.get(int(docker_profile.get("control_instance_id") or 0))
        docker_preflight_status = str(docker_profile.get("last_preflight_status") or "").strip()
        docker_preflight_summary = str(docker_profile.get("last_preflight_summary") or "").strip()
        docker_available = _which("docker")
        items = [
            HermesCapabilityItemView(
                key="codex_desktop",
                label="Codex Desktop Lanes",
                status=(
                    "ready" if connected_instances else "partial" if instances else "missing"
                ),  # type: ignore[arg-type]
                summary=(
                    f"{len(connected_instances)} connected lane(s) are available for "
                    "OpenZues executor work."
                    if connected_instances
                    else "OpenZues is designed around Codex-connected lanes, but none "
                    "are connected right now."
                ),
                capabilities=["desktop bridge", "workspace execution", "built-in agents"],
            ),
            HermesCapabilityItemView(
                key="workspace_shell",
                label="Workspace Shell Profile",
                status=(
                    "ready"
                    if connected_shell_instances
                    else "partial"
                    if shell_instances or any(instance.cwd for instance in instances)
                    else "missing"
                ),  # type: ignore[arg-type]
                summary=(
                    f"{len(connected_shell_instances)} connected shell-backed lane(s) are armed."
                    if connected_shell_instances
                    else (
                        f"{len(shell_instances)} shell-backed lane(s) are staged, and "
                        "operators can arm another one directly."
                    )
                    if shell_instances
                    else "OpenZues can arm a shell-backed lane directly once a saved workspace "
                    "path is available."
                ),
                capabilities=[
                    "cwd affinity",
                    "repo verification",
                    "shell tools",
                    "explicit arm",
                ],
            ),
            HermesCapabilityItemView(
                key="docker",
                label="Docker Backend",
                status=(
                    "ready"
                    if (
                        docker_available
                        and docker_cwd
                        and docker_image
                        and docker_preflight_status == "ready"
                        and docker_control
                        and docker_control.connected
                    )
                    else "partial"
                    if docker_available
                    else "missing"
                ),  # type: ignore[arg-type]
                summary=(
                    f"{docker_preflight_summary} Control lane `{docker_control.name}` is connected."
                    if (
                        docker_available
                        and docker_cwd
                        and docker_image
                        and docker_preflight_status == "ready"
                        and docker_control
                        and docker_control.connected
                    )
                    else (
                        f"{docker_preflight_summary} Waiting on `{docker_control.name if docker_control else 'a control lane'}`."
                    )
                    if docker_available and docker_cwd and docker_image and docker_preflight_summary
                    else (
                        f"Docker staging is armed for `{docker_cwd}` on `{docker_image}` and "
                        f"waiting on `{docker_control.name if docker_control else 'a control lane'}`."
                    )
                    if docker_available and docker_cwd and docker_image
                    else (
                        "The `docker` command is available locally, and operators can arm a "
                        "workspace/image staging profile directly."
                    )
                    if docker_available
                    else "The `docker` command is not available on this machine yet."
                ),
                capabilities=[
                    "backend staging",
                    "image profile",
                    "explicit arm",
                    "preflight",
                    "control lane reuse",
                    "workspace mount" if docker_mount_workspace else "isolated workspace defaults",
                ],
            ),
        ]
        executor_specs = (
            ("ssh", "SSH Backend", "ssh"),
            ("modal", "Modal Backend", "modal"),
            ("daytona", "Daytona Backend", "daytona"),
            ("singularity", "Singularity Backend", "singularity"),
        )
        for key, label, command in executor_specs:
            available = _which(command)
            items.append(
                HermesCapabilityItemView(
                    key=key,
                    label=label,
                    status=("partial" if available else "missing"),  # type: ignore[arg-type]
                    summary=(
                        f"The `{command}` command is available locally, so this backend "
                        "can be wired next."
                        if available
                        else f"The `{command}` command is not available on this machine yet."
                    ),
                    capabilities=["executor discovery", "future lane backend import"],
                )
            )
        preferred_key = _pick_preferred_key(
            items,
            str(profile.get("preferred_executor") or ""),
            fallback="codex_desktop",
        )
        items = [
            item.model_copy(update={"recommended": item.key == preferred_key}) for item in items
        ]
        return _build_deck(
            headline="Executor backend profiles are staged",
            summary=f"Preferred executor is {_label_for_key(items, preferred_key)}.",
            items=items,
        )

    def _build_executor_profile_states(
        self,
        profile: dict[str, Any],
        instances: list[InstanceView],
    ) -> list[HermesExecutorProfileStateView]:
        executor_profiles = _executor_profiles_payload(profile)
        instances_by_id = {instance.id: instance for instance in instances}
        states: list[HermesExecutorProfileStateView] = []

        docker_profile = executor_profiles.get("docker", {})
        docker_cwd = _normalize_cwd(docker_profile.get("cwd"))
        docker_image = _normalize_cwd(docker_profile.get("image"))
        if docker_cwd or docker_image:
            control_instance_id = (
                int(docker_profile.get("control_instance_id"))
                if str(docker_profile.get("control_instance_id") or "").strip()
                else None
            )
            control_instance = (
                instances_by_id.get(control_instance_id) if control_instance_id is not None else None
            )
            states.append(
                HermesExecutorProfileStateView(
                    key="docker",
                    label="Docker Backend",
                    armed=bool(docker_cwd and docker_image),
                    cwd=docker_cwd,
                    image=docker_image,
                    mount_workspace=bool(docker_profile.get("mount_workspace")),
                    control_instance_id=control_instance_id,
                    control_instance_name=control_instance.name if control_instance else None,
                    derived_from=(
                        str(docker_profile.get("derived_from") or "").strip() or None
                    ),
                    armed_at=str(docker_profile.get("armed_at") or "").strip() or None,
                    last_checked_at=(
                        str(docker_profile.get("last_checked_at") or "").strip() or None
                    ),
                    last_preflight_status=(
                        str(docker_profile.get("last_preflight_status") or "").strip() or None
                    ),
                    last_preflight_summary=(
                        str(docker_profile.get("last_preflight_summary") or "").strip() or None
                    ),
                    command_path=(
                        str(docker_profile.get("command_path") or "").strip() or None
                    ),
                    docker_version=(
                        str(docker_profile.get("docker_version") or "").strip() or None
                    ),
                    daemon_version=(
                        str(docker_profile.get("daemon_version") or "").strip() or None
                    ),
                    image_present=(
                        bool(docker_profile.get("image_present"))
                        if docker_profile.get("image_present") is not None
                        else None
                    ),
                    summary=(
                        str(docker_profile.get("last_preflight_summary") or "").strip()
                        or (
                            f"Docker staging is pinned to `{docker_image}` for `{docker_cwd}`."
                            if docker_cwd and docker_image
                            else "Docker staging is only partially configured."
                        )
                    ),
                )
            )
        return states

    def _build_plugin_deck(
        self,
        profile: dict[str, Any],
        instances: list[InstanceView],
    ) -> HermesCapabilityDeckView:
        live_app_count = sum(len(instance.apps) for instance in instances if instance.connected)
        live_plugin_count = sum(
            len(instance.plugins) for instance in instances if instance.connected
        )
        live_mcp_count = sum(
            len(instance.mcp_servers) for instance in instances if instance.connected
        )
        items = [
            HermesCapabilityItemView(
                key="codex_apps",
                label="Live Codex Apps",
                status=("ready" if live_app_count else "partial" if instances else "missing"),  # type: ignore[arg-type]
                summary=(
                    f"Connected lanes currently expose {live_app_count} app surface(s)."
                    if live_app_count
                    else "No live app surfaces are published from connected lanes yet."
                ),
                capabilities=["app inventory", "connector posture"],
            ),
            HermesCapabilityItemView(
                key="codex_plugins",
                label="Live Codex Plugins",
                status=("ready" if live_plugin_count else "partial" if instances else "missing"),  # type: ignore[arg-type]
                summary=(
                    f"Connected lanes currently expose {live_plugin_count} plugin surface(s)."
                    if live_plugin_count
                    else "No live plugin surfaces are published from connected lanes yet."
                ),
                capabilities=["plugin inventory", "lane-published capabilities"],
            ),
            HermesCapabilityItemView(
                key="codex_mcp",
                label="Live MCP Servers",
                status=("ready" if live_mcp_count else "partial" if instances else "missing"),  # type: ignore[arg-type]
                summary=(
                    f"Connected lanes currently expose {live_mcp_count} MCP server(s)."
                    if live_mcp_count
                    else "No live MCP servers are published from connected lanes yet."
                ),
                capabilities=["MCP inventory", "tool catalogs"],
            ),
        ]
        if profile.get("plugin_discovery_enabled", True):
            plugin_root = (
                self.settings.hermes_source_path / "plugins"
                if self.settings.hermes_source_path is not None
                else None
            )
            for plugin_name in _discover_child_directories(plugin_root):
                items.append(
                    HermesCapabilityItemView(
                        key=f"hermes_plugin:{plugin_name}",
                        label=f"Hermes Plugin: {_titleize_slug(plugin_name)}",
                        status="advisory",
                        summary=(
                            "The Hermes source tree includes this plugin family. OpenZues now "
                            "tracks it as importable plugin architecture inventory."
                        ),
                        capabilities=["plugin discovery", "future activation/config"],
                    )
                )
        return _build_deck(
            headline="Plugin and app architecture is mapped",
            summary=(
                "OpenZues inventories both live Codex plugin surfaces and Hermes plugin "
                "families."
            ),
            items=items,
        )

    async def _build_delivery_deck(self, profile: dict[str, Any]) -> HermesCapabilityDeckView:
        items: list[HermesCapabilityItemView] = []
        route_count = len(await self.database.list_notification_routes())
        platform_root = (
            self.settings.hermes_source_path / "gateway" / "platforms"
            if self.settings.hermes_source_path is not None
            else None
        )
        platforms = set(_discover_platform_modules(platform_root))
        if profile.get("channel_inventory_enabled", True):
            for key, label, members in _DELIVERY_PLATFORM_GROUPS:
                present = [member for member in members if member in platforms]
                if key == "gateway_api":
                    status = "ready" if route_count else "partial" if present else "missing"
                    present_labels = ", ".join(_titleize_slug(item) for item in present)
                    summary = (
                        f"OpenZues already has {route_count} notification route(s), and "
                        "Hermes source inventory exposes "
                        f"{present_labels or 'gateway delivery scaffolds'}."
                    )
                    if route_count:
                        summary = (
                            f"OpenZues already has {route_count} notification route(s), and "
                            "operators can now fire direct webhook delivery tests from the "
                            "control plane."
                        )
                else:
                    status = "advisory" if present else "missing"
                    present_labels = ", ".join(_titleize_slug(item) for item in present)
                    summary = (
                        f"Hermes source inventory exposes {present_labels}."
                        if present
                        else "No Hermes channel adapters from this category were discovered "
                        "in the source tree."
                    )
                items.append(
                    HermesCapabilityItemView(
                        key=key,
                        label=label,
                        status=status,  # type: ignore[arg-type]
                        summary=summary,
                        capabilities=[_titleize_slug(item) for item in present],
                    )
                )
        return _build_deck(
            headline=(
                "Gateway delivery seams are active"
                if route_count
                else "Gateway and channel delivery seams are inventoried"
            ),
            summary=(
                "OpenZues inventories Hermes delivery surfaces and can actively test webhook "
                "delivery."
                if route_count
                else "OpenZues now tracks Hermes delivery surfaces even where runtime parity is "
                "still advisory."
            ),
            items=items,
        )

    def _build_acp_deck(
        self,
        profile: dict[str, Any],
        instances: list[InstanceView],
    ) -> HermesCapabilityDeckView:
        items: list[HermesCapabilityItemView] = []
        if any(instance.connected for instance in instances):
            items.append(
                HermesCapabilityItemView(
                    key="openzues_codex_bridge",
                    label="OpenZues Codex Bridge",
                    status="partial",
                    summary=(
                        "Connected Codex lanes already give OpenZues a practical "
                        "editor/runtime bridge, "
                        "even though it is not a standalone ACP server yet."
                    ),
                    capabilities=["editor bridge", "repo execution", "delegation"],
                )
            )
        acp_root = (
            self.settings.hermes_source_path / "acp_adapter"
            if self.settings.hermes_source_path is not None
            else None
        )
        acp_files = []
        if (
            acp_root is not None
            and acp_root.exists()
            and profile.get("acp_inventory_enabled", True)
        ):
            for name in ("server.py", "tools.py", "session.py", "permissions.py", "events.py"):
                if (acp_root / name).exists():
                    acp_files.append(name)
            items.append(
                HermesCapabilityItemView(
                    key="hermes_acp_adapter",
                    label="Hermes ACP Adapter",
                    status="advisory",
                    summary=(
                        "Hermes ACP adapter source is present and now tracked as a "
                        "first-class import seam."
                    ),
                    capabilities=acp_files,
                )
            )
        return _build_deck(
            headline="ACP and editor bridge posture is visible",
            summary=(
                "OpenZues can now distinguish its live Codex bridge from Hermes ACP "
                "server scaffolds."
            ),
            items=items,
        )

    def _build_extra_deck(self) -> HermesCapabilityDeckView:
        items: list[HermesCapabilityItemView] = []
        if self.settings.hermes_source_path is not None:
            hermes_cli_root = self.settings.hermes_source_path / "hermes_cli"
            if (hermes_cli_root / "curses_ui.py").exists():
                items.append(
                    HermesCapabilityItemView(
                        key="hermes_tui",
                        label="Hermes TUI Shell",
                        status="advisory",
                        summary=(
                            "Hermes curses UI source is present and tracked as the next "
                            "terminal polish seam."
                        ),
                        capabilities=[
                            "terminal chat UX",
                            "operator shell",
                            "slash-command posture",
                        ],
                    )
                )
            environments_root = self.settings.hermes_source_path / "environments"
            if environments_root.exists():
                items.append(
                    HermesCapabilityItemView(
                        key="hermes_research_envs",
                        label="Hermes Research Environments",
                        status="advisory",
                        summary=(
                            "Hermes research and benchmark environment scaffolds are "
                            "present for future import."
                        ),
                        capabilities=["benchmark envs", "eval posture"],
                    )
                )
            if (self.settings.hermes_source_path / "trajectory_compressor.py").exists() or (
                self.settings.hermes_source_path / "batch_runner.py"
            ).exists():
                items.append(
                    HermesCapabilityItemView(
                        key="hermes_trajectory_tools",
                        label="Trajectory + Batch Tooling",
                        status="advisory",
                        summary=(
                            "Hermes trajectory compression and batch tooling are now "
                            "tracked as research extras."
                        ),
                        capabilities=["trajectory compression", "batch runs"],
                    )
                )
        return _build_deck(
            headline="Terminal polish and research extras are inventoried",
            summary=(
                "Lower-priority Hermes extras are now visible so they can be imported "
                "intentionally later."
            ),
            items=items,
        )

    async def _load_profile_payload(self) -> dict[str, Any]:
        row = await self.database.get_hermes_runtime_profile()
        payload = dict(_PROFILE_DEFAULTS)
        if row is not None:
            stored = row.get("profile")
            if isinstance(stored, dict):
                payload.update(stored)
        payload["executor_profiles"] = _executor_profiles_payload(payload)
        history = payload.get("promotion_history")
        payload["promotion_history"] = history if isinstance(history, dict) else {}
        return payload
