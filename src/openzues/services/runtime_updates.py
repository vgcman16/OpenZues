from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from openzues.database import Database

logger = logging.getLogger(__name__)
_UPDATE_LOG_TAIL_CHARS = 8000
_LOW_DISK_SPACE_WARNING_THRESHOLD_BYTES = 1024 * 1024 * 1024
_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE_ENV = (
    "OPENCLAW_UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE"
)
_NPM_GLOBAL_INSTALL_QUIET_FLAGS = ("--no-fund", "--no-audit", "--loglevel=error")
_NPM_GLOBAL_INSTALL_OMIT_OPTIONAL_FLAGS = (
    "--omit=optional",
    *_NPM_GLOBAL_INSTALL_QUIET_FLAGS,
)
_PACKAGE_DIST_INVENTORY_RELATIVE_PATH = Path("dist") / "postinstall-inventory.json"
_FIRST_PACKAGED_DIST_INVENTORY_VERSION = (2026, 4, 15)
_UPDATE_PREFLIGHT_MAX_COMMITS = 10
_STARTUP_AUTO_UPDATE_COMMAND_TIMEOUT_MS = 45 * 60 * 1000
_UPDATE_CHANNELS = {"stable", "beta", "dev"}
_UPDATE_DEV_BRANCH = "main"
_UPDATE_BETA_TAG_PATTERN = re.compile(r"(?:^|[.-])beta(?:[.-]|$)", re.IGNORECASE)
_UPDATE_LEGACY_DOT_BETA_PATTERN = re.compile(
    r"^([vV]?[0-9]+\.[0-9]+\.[0-9]+)\.beta(?:\.([0-9A-Za-z.-]+))?$"
)
_UPDATE_SEMVER_PATTERN = re.compile(
    r"^v?([0-9]+)\.([0-9]+)\.([0-9]+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$"
)
_PACKAGE_DIST_LOCAL_BUILD_METADATA_PATHS = {
    "dist/.buildstamp",
    "dist/.runtime-postbuildstamp",
}
_PACKAGE_DIST_OMITTED_QA_EXTENSION_PREFIXES = (
    "dist/extensions/qa-channel/",
    "dist/extensions/qa-lab/",
    "dist/extensions/qa-matrix/",
)
_PACKAGE_DIST_OMITTED_PRIVATE_QA_PLUGIN_SDK_PREFIXES = (
    "dist/plugin-sdk/extensions/qa-channel/",
    "dist/plugin-sdk/extensions/qa-lab/",
)
_PACKAGE_DIST_OMITTED_PRIVATE_QA_PLUGIN_SDK_FILES = {
    "dist/plugin-sdk/qa-channel.d.ts",
    "dist/plugin-sdk/qa-channel.js",
    "dist/plugin-sdk/qa-channel-protocol.d.ts",
    "dist/plugin-sdk/qa-channel-protocol.js",
    "dist/plugin-sdk/qa-lab.d.ts",
    "dist/plugin-sdk/qa-lab.js",
    "dist/plugin-sdk/qa-runtime.d.ts",
    "dist/plugin-sdk/qa-runtime.js",
    "dist/plugin-sdk/src/plugin-sdk/qa-channel.d.ts",
    "dist/plugin-sdk/src/plugin-sdk/qa-channel-protocol.d.ts",
    "dist/plugin-sdk/src/plugin-sdk/qa-lab.d.ts",
    "dist/plugin-sdk/src/plugin-sdk/qa-runtime.d.ts",
}
_PACKAGE_DIST_OMITTED_PRIVATE_QA_DIST_PREFIXES = ("dist/qa-runtime-",)
_PACKAGE_DIST_OMITTED_PRIVATE_QA_BUNDLED_PLUGIN_ROOTS = {
    "dist/extensions/qa-channel",
    "dist/extensions/qa-lab",
    "dist/extensions/qa-matrix",
}
_PACKAGE_DIST_BUNDLED_RUNTIME_SIDECAR_PATHS = (
    "dist/extensions/acpx/runtime-api.js",
    "dist/extensions/bluebubbles/runtime-api.js",
    "dist/extensions/browser/runtime-api.js",
    "dist/extensions/copilot-proxy/runtime-api.js",
    "dist/extensions/diffs/runtime-api.js",
    "dist/extensions/discord/runtime-api.js",
    "dist/extensions/discord/runtime-setter-api.js",
    "dist/extensions/feishu/runtime-api.js",
    "dist/extensions/google/runtime-api.js",
    "dist/extensions/googlechat/runtime-api.js",
    "dist/extensions/imessage/runtime-api.js",
    "dist/extensions/irc/runtime-api.js",
    "dist/extensions/line/runtime-api.js",
    "dist/extensions/lmstudio/runtime-api.js",
    "dist/extensions/lobster/runtime-api.js",
    "dist/extensions/matrix/helper-api.js",
    "dist/extensions/matrix/runtime-api.js",
    "dist/extensions/matrix/runtime-setter-api.js",
    "dist/extensions/matrix/thread-bindings-runtime.js",
    "dist/extensions/mattermost/runtime-api.js",
    "dist/extensions/memory-core/runtime-api.js",
    "dist/extensions/msteams/runtime-api.js",
    "dist/extensions/nextcloud-talk/runtime-api.js",
    "dist/extensions/nostr/runtime-api.js",
    "dist/extensions/ollama/runtime-api.js",
    "dist/extensions/open-prose/runtime-api.js",
    "dist/extensions/qqbot/runtime-api.js",
    "dist/extensions/signal/runtime-api.js",
    "dist/extensions/slack/runtime-api.js",
    "dist/extensions/slack/runtime-setter-api.js",
    "dist/extensions/telegram/runtime-api.js",
    "dist/extensions/telegram/runtime-setter-api.js",
    "dist/extensions/tlon/runtime-api.js",
    "dist/extensions/tokenjuice/runtime-api.js",
    "dist/extensions/twitch/runtime-api.js",
    "dist/extensions/voice-call/runtime-api.js",
    "dist/extensions/webhooks/runtime-api.js",
    "dist/extensions/whatsapp/light-runtime-api.js",
    "dist/extensions/whatsapp/runtime-api.js",
    "dist/extensions/zai/runtime-api.js",
    "dist/extensions/zalo/runtime-api.js",
    "dist/extensions/zalouser/runtime-api.js",
)


RuntimeUpdateCommandRunner = Callable[
    [list[str], Path, int | None],
    Awaitable[dict[str, object]],
]
RuntimeConfigSnapshotLoader = Callable[[], Mapping[str, object]]
RuntimePackageVersionResolver = Callable[[str, str, int | None], Awaitable[str | None]]


@dataclass(slots=True)
class _NpmGlobalPrefixLayout:
    prefix: Path
    global_root: Path
    bin_dir: Path


@dataclass(slots=True)
class _StagedNpmInstall:
    prefix: Path
    layout: _NpmGlobalPrefixLayout
    package_root: Path


@dataclass(slots=True)
class _DiskSpaceSnapshot:
    target_path: Path
    checked_path: Path
    available_bytes: int
    total_bytes: int | None


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _find_repo_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _default_repo_root() -> Path | None:
    return _find_repo_root(Path(__file__).resolve())


def _default_package_root() -> Path:
    try:
        return Path(__file__).resolve(strict=False).parents[2]
    except IndexError:  # pragma: no cover - defensive fallback for unusual loaders
        return Path.cwd()


def _resolve_git_revision(repo_root: Path) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [git, "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    revision = completed.stdout.strip()
    return revision or None


def _trim_update_log_tail(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value[-_UPDATE_LOG_TAIL_CHARS:]


def _update_command_exit_code(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _update_step_log(step: dict[str, object]) -> dict[str, object]:
    log = step.get("log")
    return log if isinstance(log, dict) else {}


def _update_step_exit_code(step: dict[str, object]) -> int | None:
    return _update_command_exit_code(_update_step_log(step).get("exitCode"))


def _update_step_stdout_tail(step: dict[str, object]) -> str | None:
    stdout_tail = _update_step_log(step).get("stdoutTail")
    if not isinstance(stdout_tail, str):
        return None
    return stdout_tail.strip() or None


def _normalize_dev_target_ref(value: str | None) -> str | None:
    if value is None:
        return None
    target_ref = value.strip()
    return target_ref or None


def _normalize_update_channel(value: str | None) -> str | None:
    if value is None:
        return None
    channel = value.strip().lower()
    return channel if channel in _UPDATE_CHANNELS else None


def _is_truthy_env_value(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _update_mapping(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        update = value.get("update")
        if isinstance(update, Mapping):
            return update
    return {}


def _update_auto_mapping(value: object) -> Mapping[str, object]:
    auto = _update_mapping(value).get("auto")
    return auto if isinstance(auto, Mapping) else {}


def _startup_auto_update_enabled(value: object) -> bool:
    return _update_auto_mapping(value).get("enabled") is True


def _startup_update_channel(value: object) -> str:
    channel = _normalize_update_channel(str(_update_mapping(value).get("channel") or ""))
    return channel or "stable"


def _channel_to_package_tag(channel: str) -> str:
    if channel == "beta":
        return "beta"
    if channel == "dev":
        return "dev"
    return "latest"


def _is_update_beta_tag(value: str) -> bool:
    return _UPDATE_BETA_TAG_PATTERN.search(value) is not None


def _is_update_stable_tag(value: str) -> bool:
    return not _is_update_beta_tag(value)


def _normalize_legacy_dot_beta_version(value: str) -> str:
    match = _UPDATE_LEGACY_DOT_BETA_PATTERN.match(value.strip())
    if match is None:
        return value.strip()
    base = match.group(1)
    suffix = match.group(2)
    return f"{base}-beta.{suffix}" if suffix else f"{base}-beta"


def _parse_update_comparable_semver(
    value: str | None,
) -> tuple[int, int, int, tuple[str, ...] | None] | None:
    if not value:
        return None
    normalized = _normalize_legacy_dot_beta_version(value)
    match = _UPDATE_SEMVER_PATTERN.match(normalized)
    if match is None:
        return None
    major, minor, patch, prerelease_raw = match.groups()
    prerelease = (
        tuple(part for part in prerelease_raw.split(".") if part)
        if prerelease_raw
        else None
    )
    return int(major), int(minor), int(patch), prerelease


def _compare_update_prerelease_identifiers(
    left: tuple[str, ...] | None,
    right: tuple[str, ...] | None,
) -> int:
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1
    for index in range(max(len(left), len(right))):
        left_item = left[index] if index < len(left) else None
        right_item = right[index] if index < len(right) else None
        if left_item is None and right_item is None:
            return 0
        if left_item is None:
            return -1
        if right_item is None:
            return 1
        if left_item == right_item:
            continue
        left_numeric = left_item.isdigit()
        right_numeric = right_item.isdigit()
        if left_numeric and right_numeric:
            return -1 if int(left_item) < int(right_item) else 1
        if left_numeric and not right_numeric:
            return -1
        if not left_numeric and right_numeric:
            return 1
        return -1 if left_item < right_item else 1
    return 0


def _compare_update_semver_strings(left: str | None, right: str | None) -> int | None:
    left_semver = _parse_update_comparable_semver(left)
    right_semver = _parse_update_comparable_semver(right)
    if left_semver is None or right_semver is None:
        return None
    for left_part, right_part in zip(left_semver[:3], right_semver[:3], strict=True):
        if left_part != right_part:
            return -1 if left_part < right_part else 1
    return _compare_update_prerelease_identifiers(left_semver[3], right_semver[3])


def _resolve_update_channel_tag(tags: Sequence[str], channel: str) -> str | None:
    if channel == "beta":
        beta_tag = next((tag for tag in tags if _is_update_beta_tag(tag)), None)
        stable_tag = next((tag for tag in tags if _is_update_stable_tag(tag)), None)
        if beta_tag is None:
            return stable_tag
        if stable_tag is None:
            return beta_tag
        comparison = _compare_update_semver_strings(beta_tag, stable_tag)
        if comparison is not None and comparison < 0:
            return stable_tag
        return beta_tag
    return next((tag for tag in tags if _is_update_stable_tag(tag)), None)


def _looks_like_full_commit_sha(value: str) -> bool:
    target = value.strip()
    return len(target) == 40 and all(char in "0123456789abcdefABCDEF" for char in target)


def _dev_target_ref_resolution_candidates(dev_target_ref: str) -> list[str]:
    target_ref = dev_target_ref.strip()
    candidates: list[str] = []

    def add_candidate(candidate: str | None) -> None:
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    if _looks_like_full_commit_sha(target_ref):
        add_candidate(target_ref)
        return candidates
    if target_ref.startswith("refs/remotes/"):
        add_candidate(target_ref)
        return candidates
    if target_ref.startswith("refs/heads/"):
        add_candidate(f"refs/remotes/origin/{target_ref[len('refs/heads/'):]}")
        return candidates
    if target_ref.startswith("origin/"):
        add_candidate(f"refs/remotes/{target_ref}")
        return candidates
    if target_ref.startswith("refs/tags/"):
        add_candidate(f"{target_ref}^{{}}")
        add_candidate(target_ref)
        return candidates

    add_candidate(f"refs/remotes/origin/{target_ref}")
    add_candidate(f"refs/tags/{target_ref}^{{}}")
    add_candidate(f"refs/tags/{target_ref}")
    return candidates


def _first_failed_update_step(steps: list[dict[str, object]]) -> dict[str, object] | None:
    for step in steps:
        exit_code = _update_step_exit_code(step)
        if exit_code is not None and exit_code != 0:
            return step
    return None


def _read_package_version(package_root: Path) -> str | None:
    package_json = package_root / "package.json"
    try:
        parsed = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    version = parsed.get("version")
    return version.strip() if isinstance(version, str) and version.strip() else None


def _read_package_name(package_root: Path) -> str:
    package_json = package_root / "package.json"
    try:
        parsed = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return package_root.name
    if not isinstance(parsed, dict):
        return package_root.name
    name = parsed.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else package_root.name


def _detect_package_manager(package_root: Path) -> str:
    package_json = package_root / "package.json"
    if _path_exists(package_json):
        try:
            parsed = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, Mapping):
            raw_manager = str(parsed.get("packageManager") or "").strip()
            manager = raw_manager.split("@", maxsplit=1)[0].strip().lower()
            if manager in {"pnpm", "bun", "npm"}:
                return manager
    for filename, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("bun.lock", "bun"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
    ):
        if _path_exists(package_root / filename):
            return manager
    return "unknown"


def _find_existing_disk_space_path(target_path: Path) -> Path | None:
    current = target_path.resolve(strict=False)
    while True:
        try:
            if current.is_dir():
                return current
            if current.exists():
                return current.parent
        except OSError:
            pass
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _try_read_disk_space(target_path: Path) -> _DiskSpaceSnapshot | None:
    checked_path = _find_existing_disk_space_path(target_path)
    if checked_path is None:
        return None
    try:
        usage = shutil.disk_usage(checked_path)
    except OSError:
        return None
    available_bytes = getattr(usage, "free", None)
    total_bytes = getattr(usage, "total", None)
    if (
        isinstance(available_bytes, bool)
        or not isinstance(available_bytes, int)
        or available_bytes < 0
    ):
        return None
    if isinstance(total_bytes, bool) or not isinstance(total_bytes, int) or total_bytes < 0:
        total_bytes = None
    return _DiskSpaceSnapshot(
        target_path=target_path,
        checked_path=checked_path,
        available_bytes=available_bytes,
        total_bytes=total_bytes,
    )


def _format_disk_space_bytes(bytes_value: int) -> str:
    mib = bytes_value / (1024 * 1024)
    if mib < 1024:
        return f"{max(0, round(mib))} MiB"
    gib = mib / 1024
    precision = 1 if gib < 10 else 0
    return f"{gib:.{precision}f} GiB"


def _create_low_disk_space_warning(
    *,
    target_path: Path,
    purpose: str,
    threshold_bytes: int = _LOW_DISK_SPACE_WARNING_THRESHOLD_BYTES,
) -> str | None:
    snapshot = _try_read_disk_space(target_path)
    if snapshot is None or snapshot.available_bytes >= threshold_bytes:
        return None
    target_resolved = snapshot.target_path.resolve(strict=False)
    checked_resolved = snapshot.checked_path.resolve(strict=False)
    if target_resolved == checked_resolved:
        location = str(snapshot.checked_path)
    else:
        location = f"{snapshot.target_path} (volume checked at {snapshot.checked_path})"
    available = _format_disk_space_bytes(snapshot.available_bytes)
    return f"Low disk space near {location}: {available} available; {purpose} may fail."


def _package_name_parts(package_name: str) -> tuple[str, ...]:
    return tuple(part for part in package_name.strip().split("/") if part)


def _package_root_for_name(global_root: Path, package_name: str) -> Path:
    parts = _package_name_parts(package_name)
    if not parts:
        return global_root / "openzues"
    return global_root.joinpath(*parts)


def _global_root_from_package_root(package_root: Path, package_name: str) -> Path:
    root = package_root
    for _part in _package_name_parts(package_name) or (package_root.name,):
        root = root.parent
    return root


def _npm_prefix_layout_from_global_root(global_root: Path) -> _NpmGlobalPrefixLayout | None:
    resolved = global_root.resolve()
    if resolved.name != "node_modules":
        return None
    parent = resolved.parent
    if parent.name == "lib":
        prefix = parent.parent
        return _NpmGlobalPrefixLayout(
            prefix=prefix,
            global_root=resolved,
            bin_dir=prefix / "bin",
        )
    if os.name == "nt":
        return _NpmGlobalPrefixLayout(
            prefix=parent,
            global_root=resolved,
            bin_dir=parent,
        )
    return None


def _npm_prefix_layout_from_prefix(prefix: Path) -> _NpmGlobalPrefixLayout:
    resolved = prefix.resolve()
    if os.name == "nt":
        return _NpmGlobalPrefixLayout(
            prefix=resolved,
            global_root=resolved / "node_modules",
            bin_dir=resolved,
        )
    return _NpmGlobalPrefixLayout(
        prefix=resolved,
        global_root=resolved / "lib" / "node_modules",
        bin_dir=resolved / "bin",
    )


def _create_staged_npm_install(
    package_root: Path,
    package_name: str,
) -> tuple[_StagedNpmInstall | None, dict[str, object] | None]:
    started_at = time.monotonic()
    global_root = _global_root_from_package_root(package_root, package_name)
    target_layout = _npm_prefix_layout_from_global_root(global_root)
    if target_layout is None:
        return None, {
            "name": "global install stage",
            "command": "prepare staged npm install",
            "cwd": str(global_root),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": None,
                "stderrTail": "cannot resolve npm global prefix layout",
                "exitCode": 1,
            },
        }
    try:
        target_layout.global_root.mkdir(parents=True, exist_ok=True)
        stage_prefix = Path(
            tempfile.mkdtemp(
                prefix=".openzues-update-stage-",
                dir=str(target_layout.global_root),
            ),
        )
    except OSError as exc:
        return None, {
            "name": "global install stage",
            "command": "prepare staged npm install",
            "cwd": str(target_layout.global_root),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": None,
                "stderrTail": str(exc),
                "exitCode": 1,
            },
        }
    stage_layout = _npm_prefix_layout_from_prefix(stage_prefix)
    return _StagedNpmInstall(
        prefix=stage_prefix,
        layout=stage_layout,
        package_root=_package_root_for_name(stage_layout.global_root, package_name),
    ), None


def _cleanup_staged_npm_install(stage: _StagedNpmInstall | None) -> None:
    if stage is None:
        return
    shutil.rmtree(stage.prefix, ignore_errors=True)


def _cleanup_global_rename_dirs(package_root: Path, package_name: str) -> list[str]:
    cleaned_name = package_name.strip()
    if not cleaned_name:
        return []
    global_root = _global_root_from_package_root(package_root, cleaned_name)
    prefix = f".{cleaned_name}-"
    try:
        entries = list(global_root.iterdir())
    except OSError:
        return []
    removed: list[str] = []
    for entry in entries:
        if not entry.name.startswith(prefix):
            continue
        try:
            if not stat.S_ISDIR(entry.lstat().st_mode):
                continue
            shutil.rmtree(entry)
        except OSError:
            continue
        removed.append(entry.name)
    return removed


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _copy_path_entry(source: Path, destination: Path) -> None:
    if destination.exists() or destination.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        destination.symlink_to(source.readlink())
        return
    if source.is_dir():
        shutil.copytree(source, destination, symlinks=True)
        return
    shutil.copy2(source, destination)


def _restore_npm_bin_shim_backup(
    *,
    backup_dir: Path,
    target_bin_dir: Path,
    entries: list[tuple[str, bool]],
) -> None:
    target_bin_dir.mkdir(parents=True, exist_ok=True)
    for entry, had_existing in entries:
        destination = target_bin_dir / entry
        if destination.exists() or destination.is_symlink():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if had_existing:
            _copy_path_entry(backup_dir / entry, destination)


def _replace_npm_bin_shims(
    *,
    stage_layout: _NpmGlobalPrefixLayout,
    target_layout: _NpmGlobalPrefixLayout,
    package_name: str,
) -> None:
    try:
        entries = list(stage_layout.bin_dir.iterdir())
    except OSError:
        return
    package_last_name = _package_name_parts(package_name)[-1:] or (package_name,)
    names = {package_name, *package_last_name, "openzues"}
    shim_entries = [
        entry.name
        for entry in entries
        if entry.name in names or entry.stem in names
    ]
    if not shim_entries:
        return
    backup_dir = Path(
        tempfile.mkdtemp(
            prefix=".openzues-shim-backup-",
            dir=str(target_layout.global_root),
        ),
    )
    backups: list[tuple[str, bool]] = []
    try:
        target_layout.bin_dir.mkdir(parents=True, exist_ok=True)
        for entry in shim_entries:
            destination = target_layout.bin_dir / entry
            had_existing = _path_exists(destination)
            backups.append((entry, had_existing))
            if had_existing:
                _copy_path_entry(destination, backup_dir / entry)
        for entry in shim_entries:
            _copy_path_entry(stage_layout.bin_dir / entry, target_layout.bin_dir / entry)
    except OSError:
        _restore_npm_bin_shim_backup(
            backup_dir=backup_dir,
            target_bin_dir=target_layout.bin_dir,
            entries=backups,
        )
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)


def _swap_staged_npm_install(
    *,
    stage: _StagedNpmInstall,
    package_root: Path,
    package_name: str,
) -> dict[str, object]:
    started_at = time.monotonic()
    global_root = _global_root_from_package_root(package_root, package_name)
    target_layout = _npm_prefix_layout_from_global_root(global_root)
    if target_layout is None:
        return {
            "name": "global install swap",
            "command": "swap staged npm install",
            "cwd": str(stage.prefix),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": None,
                "stderrTail": "cannot resolve npm global prefix layout",
                "exitCode": 1,
            },
        }
    backup_root = target_layout.global_root / f".openzues-{os.getpid()}-{int(time.time() * 1000)}"
    moved_existing = False
    moved_staged = False
    command = f"swap {stage.package_root} -> {package_root}"
    try:
        package_root.parent.mkdir(parents=True, exist_ok=True)
        if _path_exists(package_root):
            package_root.rename(backup_root)
            moved_existing = True
        stage.package_root.rename(package_root)
        moved_staged = True
        _replace_npm_bin_shims(
            stage_layout=stage.layout,
            target_layout=target_layout,
            package_name=package_name,
        )
        if moved_existing:
            shutil.rmtree(backup_root, ignore_errors=True)
        stdout_tail = f"replaced {package_name}" if moved_existing else f"installed {package_name}"
        return {
            "name": "global install swap",
            "command": command,
            "cwd": str(target_layout.global_root),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": stdout_tail,
                "stderrTail": None,
                "exitCode": 0,
            },
        }
    except OSError as exc:
        if moved_staged:
            shutil.rmtree(package_root, ignore_errors=True)
        if moved_existing:
            try:
                backup_root.rename(package_root)
            except OSError:
                pass
        return {
            "name": "global install swap",
            "command": command,
            "cwd": str(target_layout.global_root),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": None,
                "stderrTail": str(exc),
                "exitCode": 1,
            },
        }


def _global_package_update_args(
    package_manager: str,
    package_spec: str,
    *,
    install_prefix: Path | None = None,
    package_root: Path | None = None,
    package_name: str | None = None,
) -> list[str] | None:
    manager = package_manager.strip().lower()
    spec = package_spec.strip()
    if not spec:
        return None
    if manager == "pnpm":
        return ["pnpm", "add", "-g", spec]
    if manager == "bun":
        return ["bun", "add", "-g", spec]
    if manager == "npm":
        npm_command = _preferred_npm_command(package_root, package_name)
        prefix_args = ["--prefix", str(install_prefix)] if install_prefix is not None else []
        return [npm_command, "i", "-g", *prefix_args, spec, *_NPM_GLOBAL_INSTALL_QUIET_FLAGS]
    return None


def _global_package_update_fallback_args(
    package_manager: str,
    package_spec: str,
    *,
    install_prefix: Path | None = None,
    package_root: Path | None = None,
    package_name: str | None = None,
) -> list[str] | None:
    manager = package_manager.strip().lower()
    spec = package_spec.strip()
    if manager != "npm" or not spec:
        return None
    npm_command = _preferred_npm_command(package_root, package_name)
    prefix_args = ["--prefix", str(install_prefix)] if install_prefix is not None else []
    return [npm_command, "i", "-g", *prefix_args, spec, *_NPM_GLOBAL_INSTALL_OMIT_OPTIONAL_FLAGS]


def _preferred_npm_command(package_root: Path | None, package_name: str | None) -> str:
    if package_root is None or not package_name:
        return "npm"
    global_root = _global_root_from_package_root(package_root, package_name)
    layout = _npm_prefix_layout_from_global_root(global_root)
    if layout is None:
        return "npm"
    candidate = layout.prefix / "npm.cmd" if os.name == "nt" else layout.prefix / "bin" / "npm"
    return str(candidate) if candidate.exists() else "npm"


def _post_package_update_doctor_args() -> list[str]:
    return [
        sys.executable,
        "-m",
        "openzues.cli",
        "doctor",
        "--non-interactive",
        "--fix",
        "--json",
    ]


def _post_package_update_doctor_env() -> dict[str, str]:
    return {
        "NODE_DISABLE_COMPILE_CACHE": "1",
        "OPENCLAW_UPDATE_IN_PROGRESS": "1",
        _UPDATE_PARENT_SUPPORTS_DOCTOR_CONFIG_WRITE_ENV: "1",
    }


def _global_package_update_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if os.name == "nt":
        env.update(
            {
                "NPM_CONFIG_UPDATE_NOTIFIER": "false",
                "NPM_CONFIG_FUND": "false",
                "NPM_CONFIG_AUDIT": "false",
                "NODE_LLAMA_CPP_SKIP_DOWNLOAD": "1",
            }
        )
        path_prepend = _portable_git_path_prepend()
        if path_prepend:
            env["PATH"] = _merge_path_prepend(os.environ.get("PATH"), path_prepend)
    if not os.environ.get("COREPACK_ENABLE_DOWNLOAD_PROMPT", "").strip():
        env["COREPACK_ENABLE_DOWNLOAD_PROMPT"] = "0"
    return env


def _portable_git_path_prepend() -> list[str]:
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        return []
    portable_git_root = Path(local_app_data) / "OpenClaw" / "deps" / "portable-git"
    candidates = (
        portable_git_root / "mingw64" / "bin",
        portable_git_root / "usr" / "bin",
        portable_git_root / "cmd",
        portable_git_root / "bin",
    )
    return [str(candidate) for candidate in candidates if candidate.exists()]


def _merge_path_prepend(existing: str | None, prepend: Sequence[str]) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for entry in [*prepend, *(existing or "").split(os.pathsep)]:
        normalized = entry.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(normalized)
    return os.pathsep.join(merged)


def _apply_command_env(env: Mapping[str, str] | None) -> dict[str, str | None]:
    if not env:
        return {}
    previous: dict[str, str | None] = {}
    for key, value in env.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    return previous


def _restore_command_env(previous: Mapping[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _expected_package_version_from_spec(package_spec: str) -> str | None:
    spec = package_spec.strip()
    if "@" not in spec:
        return None
    candidate = spec.rsplit("@", maxsplit=1)[-1].strip()
    if not candidate or not candidate[0].isdigit() or "." not in candidate:
        return None
    return candidate


def _parse_package_semver(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    pieces = value.strip().split(".")
    if len(pieces) < 3:
        return None
    parsed: list[int] = []
    for piece in pieces[:3]:
        digits = []
        for char in piece:
            if not char.isdigit():
                break
            digits.append(char)
        if not digits:
            return None
        parsed.append(int("".join(digits)))
    return (parsed[0], parsed[1], parsed[2])


def _should_require_packaged_dist_inventory(version: str | None) -> bool:
    parsed = _parse_package_semver(version)
    if parsed is None:
        return False
    return parsed >= _FIRST_PACKAGED_DIST_INVENTORY_VERSION


def _read_package_dist_inventory_if_present(
    package_root: Path,
) -> tuple[list[str] | None, str | None]:
    inventory_path = package_root / _PACKAGE_DIST_INVENTORY_RELATIVE_PATH
    if not _path_exists(inventory_path):
        return None, None
    invalid_message = (
        "invalid package dist inventory "
        f"{_PACKAGE_DIST_INVENTORY_RELATIVE_PATH.as_posix()}"
    )
    try:
        parsed = json.loads(inventory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, invalid_message
    if not isinstance(parsed, list) or any(not isinstance(entry, str) for entry in parsed):
        return None, invalid_message
    inventory_files = sorted({entry.replace("\\", "/") for entry in parsed})
    return inventory_files, None


def _collect_package_dist_inventory(package_root: Path) -> tuple[list[str], list[str]]:
    dist_root = package_root / "dist"
    if not _path_exists(dist_root):
        return [], []
    (
        externalized_extension_ids,
        externalized_manifest_errors,
    ) = _collect_externalized_bundled_extension_ids(package_root)
    files: list[str] = []
    errors: list[str] = [*externalized_manifest_errors]
    for path in dist_root.rglob("*"):
        try:
            relative_path = path.relative_to(package_root).as_posix()
            if _is_omitted_package_dist_subtree(relative_path, externalized_extension_ids):
                continue
            if path.is_symlink():
                errors.append(f"Unsafe package dist path: {relative_path}")
                continue
            if not path.is_file():
                continue
        except OSError:
            continue
        if not _is_packaged_dist_file(relative_path, externalized_extension_ids):
            continue
        files.append(relative_path)
    return sorted(set(files)), sorted(set(errors))


def _is_legacy_plugin_dependency_dir_path(relative_path: str) -> bool:
    parts = relative_path.split("/")
    if len(parts) < 3 or parts[0].lower() != "dist" or parts[1].lower() != "extensions":
        return False
    if parts[2].lower() == "node_modules":
        return True
    return len(parts) >= 4 and parts[3].lower() == "node_modules"


def _collect_externalized_bundled_extension_ids(package_root: Path) -> tuple[set[str], list[str]]:
    extensions_path = package_root / "extensions"
    if not _path_exists(extensions_path):
        return set(), []
    extension_ids: set[str] = set()
    errors: list[str] = []
    try:
        extension_entries = list(extensions_path.iterdir())
    except OSError:
        return extension_ids, []
    for extension_entry in extension_entries:
        manifest_path = extension_entry / "package.json"
        try:
            if not extension_entry.is_dir() or extension_entry.is_symlink():
                continue
            raw_manifest = manifest_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except OSError:
            errors.append(
                "invalid bundled extension manifest "
                f"{manifest_path.relative_to(package_root).as_posix()}"
            )
            continue
        try:
            parsed = json.loads(raw_manifest)
        except json.JSONDecodeError:
            errors.append(
                "invalid bundled extension manifest "
                f"{manifest_path.relative_to(package_root).as_posix()}"
            )
            continue
        if _is_publishable_externalized_manifest(parsed):
            extension_ids.add(extension_entry.name)
    return extension_ids, sorted(set(errors))


def _is_publishable_externalized_manifest(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    openclaw = value.get("openclaw")
    if not isinstance(openclaw, Mapping):
        return False
    release = openclaw.get("release")
    if not isinstance(release, Mapping):
        return False
    bundle = openclaw.get("bundle")
    if isinstance(bundle, Mapping) and bundle.get("includeInCore") is True:
        return False
    return release.get("publishToNpm") is True or release.get("publishToClawHub") is True


def _is_externalized_bundled_extension_dist_path(
    relative_path: str,
    externalized_extension_ids: set[str],
) -> bool:
    parts = relative_path.split("/")
    return (
        len(parts) >= 3
        and parts[0] == "dist"
        and parts[1] == "extensions"
        and parts[2] in externalized_extension_ids
    )


def _is_omitted_package_dist_subtree(
    relative_path: str,
    externalized_extension_ids: set[str],
) -> bool:
    return (
        _is_externalized_bundled_extension_dist_path(relative_path, externalized_extension_ids)
        or _is_legacy_plugin_dependency_dir_path(relative_path)
        or relative_path.startswith(_PACKAGE_DIST_OMITTED_QA_EXTENSION_PREFIXES)
        or relative_path.startswith(_PACKAGE_DIST_OMITTED_PRIVATE_QA_PLUGIN_SDK_PREFIXES)
        or relative_path.startswith(_PACKAGE_DIST_OMITTED_PRIVATE_QA_DIST_PREFIXES)
    )


def _is_packaged_dist_file(
    relative_path: str,
    externalized_extension_ids: set[str],
) -> bool:
    if not relative_path.startswith("dist/"):
        return False
    if _is_externalized_bundled_extension_dist_path(relative_path, externalized_extension_ids):
        return False
    if relative_path == _PACKAGE_DIST_INVENTORY_RELATIVE_PATH.as_posix():
        return False
    if relative_path in _PACKAGE_DIST_LOCAL_BUILD_METADATA_PATHS:
        return False
    if relative_path.endswith(".map"):
        return False
    if relative_path == "dist/plugin-sdk/.tsbuildinfo":
        return False
    if _is_legacy_plugin_dependency_dir_path(relative_path):
        return False
    if relative_path.startswith(_PACKAGE_DIST_OMITTED_QA_EXTENSION_PREFIXES):
        return False
    if relative_path.startswith(_PACKAGE_DIST_OMITTED_PRIVATE_QA_PLUGIN_SDK_PREFIXES):
        return False
    if relative_path in _PACKAGE_DIST_OMITTED_PRIVATE_QA_PLUGIN_SDK_FILES:
        return False
    return not relative_path.startswith(_PACKAGE_DIST_OMITTED_PRIVATE_QA_DIST_PREFIXES)


def _collect_package_dist_inventory_file_errors(
    package_root: Path,
    inventory_files: Sequence[str],
) -> list[str]:
    actual_files, unsafe_errors = _collect_package_dist_inventory(package_root)
    actual_set = set(actual_files)
    inventory_set = set(inventory_files)
    errors: list[str] = [*unsafe_errors]
    for relative_path in inventory_files:
        if relative_path not in actual_set:
            errors.append(f"missing packaged dist file {relative_path}")
    for relative_path in actual_files:
        if relative_path not in inventory_set:
            errors.append(f"unexpected packaged dist file {relative_path}")
    return errors


def _package_dist_plugin_root(relative_path: str) -> str | None:
    parts = relative_path.split("/")
    if len(parts) < 3 or parts[0] != "dist" or parts[1] != "extensions":
        return None
    return "/".join(parts[:3])


def _collect_critical_bundled_runtime_sidecars(package_root: Path) -> list[str]:
    expected: list[str] = []
    for relative_path in _PACKAGE_DIST_BUNDLED_RUNTIME_SIDECAR_PATHS:
        plugin_root = _package_dist_plugin_root(relative_path)
        if plugin_root is None:
            continue
        if plugin_root in _PACKAGE_DIST_OMITTED_PRIVATE_QA_BUNDLED_PLUGIN_ROOTS:
            continue
        plugin_path = package_root / Path(plugin_root)
        if _path_exists(plugin_path / "package.json") or _path_exists(
            plugin_path / "openclaw.plugin.json"
        ):
            expected.append(relative_path)
    return sorted(set(expected))


def _collect_missing_bundled_runtime_sidecar_errors(
    package_root: Path,
    inventory_files: Sequence[str] | None,
) -> list[str]:
    expected = _collect_critical_bundled_runtime_sidecars(package_root)
    if inventory_files is not None:
        inventory_set = set(inventory_files)
        expected = [path for path in expected if path not in inventory_set]
    errors: list[str] = []
    for relative_path in expected:
        if not _path_exists(package_root / Path(relative_path)):
            errors.append(f"missing bundled runtime sidecar {relative_path}")
    return errors


def _collect_package_update_verify_errors(
    package_root: Path,
    *,
    expected_version: str | None,
) -> list[str]:
    errors: list[str] = []
    resolved_root = package_root.resolve(strict=False)
    has_source_marker = _path_exists(resolved_root / ".git") or _path_exists(
        resolved_root / "pnpm-workspace.yaml"
    )
    if has_source_marker and _path_exists(resolved_root / "src") and _path_exists(
        resolved_root / "extensions"
    ):
        errors.append(f"global package root resolves to source checkout: {resolved_root}")
    installed_version = _read_package_version(package_root)
    if expected_version is not None and installed_version != expected_version:
        found = installed_version or "<missing>"
        errors.append(f"expected installed version {expected_version}, found {found}")
    inventory_files, inventory_error = _read_package_dist_inventory_if_present(package_root)
    if inventory_error is not None:
        errors.append(inventory_error)
        errors.extend(_collect_missing_bundled_runtime_sidecar_errors(package_root, None))
    elif inventory_files is not None:
        errors.extend(
            _collect_package_dist_inventory_file_errors(package_root, inventory_files)
        )
        errors.extend(
            _collect_missing_bundled_runtime_sidecar_errors(
                package_root,
                inventory_files,
            )
        )
    elif (
        _should_require_packaged_dist_inventory(installed_version)
        or _should_require_packaged_dist_inventory(expected_version)
    ):
        errors.append(
            "missing package dist inventory "
            f"{_PACKAGE_DIST_INVENTORY_RELATIVE_PATH.as_posix()}"
        )
        errors.extend(_collect_missing_bundled_runtime_sidecar_errors(package_root, None))
    else:
        errors.extend(_collect_missing_bundled_runtime_sidecar_errors(package_root, None))
    return errors


async def _default_update_command_runner(
    argv: list[str],
    cwd: Path,
    timeout_ms: int | None,
) -> dict[str, object]:
    timeout_seconds = timeout_ms / 1000 if timeout_ms is not None else None

    def run() -> dict[str, object]:
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode(errors="replace")
                if isinstance(exc.stdout, bytes)
                else exc.stdout
            )
            stderr = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr
            )
            return {
                "stdout": stdout or "",
                "stderr": stderr or "command timed out",
                "exitCode": None,
            }
        except OSError as exc:
            return {"stdout": "", "stderr": str(exc), "exitCode": 1}
        return {
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "exitCode": completed.returncode,
        }

    return await asyncio.to_thread(run)


@dataclass(slots=True)
class RuntimeUpdateSnapshot:
    enabled: bool
    repo_root: str | None
    startup_revision: str | None
    current_revision: str | None
    pending_revision: str | None
    pending_restart: bool
    restart_in_progress: bool
    safe_to_restart: bool
    last_checked_at: str | None
    last_restart_at: str | None
    last_error: str | None
    auto_restart: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RuntimeUpdateService:
    def __init__(
        self,
        database: Database,
        *,
        enabled: bool,
        poll_interval_seconds: int = 20,
        restart_callback: Callable[[], Awaitable[None]],
        repo_root: Path | None = None,
        revision_resolver: Callable[[Path], str | None] = _resolve_git_revision,
        update_command_runner: RuntimeUpdateCommandRunner | None = None,
        config_snapshot_loader: RuntimeConfigSnapshotLoader | None = None,
        package_root: Path | None = None,
        package_version_resolver: RuntimePackageVersionResolver | None = None,
    ) -> None:
        self.database = database
        self.poll_interval_seconds = max(5, int(poll_interval_seconds))
        self._restart_callback = restart_callback
        self._revision_resolver = revision_resolver
        self._update_command_runner = update_command_runner or _default_update_command_runner
        self._config_snapshot_loader = config_snapshot_loader
        self._package_root = package_root or _default_package_root()
        self._package_version_resolver = package_version_resolver
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self.repo_root = repo_root or _default_repo_root()
        self.startup_revision = (
            revision_resolver(self.repo_root) if self.repo_root is not None else None
        )
        active = enabled and self.repo_root is not None and self.startup_revision is not None
        self._snapshot = RuntimeUpdateSnapshot(
            enabled=active,
            repo_root=str(self.repo_root) if self.repo_root is not None else None,
            startup_revision=self.startup_revision,
            current_revision=self.startup_revision,
            pending_revision=None,
            pending_restart=False,
            restart_in_progress=False,
            safe_to_restart=False,
            last_checked_at=None,
            last_restart_at=None,
            last_error=None,
            auto_restart=enabled,
        )

    def snapshot(self) -> dict[str, object]:
        return self._snapshot.to_dict()

    async def run_startup_auto_update_check(
        self,
        *,
        timeout_ms: int | None = None,
    ) -> dict[str, object]:
        config_loader = self._config_snapshot_loader
        if config_loader is None:
            return {"status": "skipped", "reason": "config-unavailable"}
        try:
            config_snapshot = config_loader()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Startup auto-update config load failed.")
            return {"status": "error", "reason": "config-load-failed", "error": str(exc)}
        if not _startup_auto_update_enabled(config_snapshot):
            return {"status": "skipped", "reason": "auto-disabled"}
        if _is_truthy_env_value(os.environ.get("OPENCLAW_NO_AUTO_UPDATE")):
            return {"status": "skipped", "reason": "auto-disabled-by-env"}

        channel = _startup_update_channel(config_snapshot)
        if channel not in {"stable", "beta"}:
            return {
                "status": "skipped",
                "reason": "auto-channel-unsupported",
                "channel": channel,
            }
        package_root = self._package_root
        if _path_exists(package_root / ".git"):
            return {"status": "skipped", "reason": "not-package-install"}
        package_name = _read_package_name(package_root)
        current_version = _read_package_version(package_root)
        if not current_version:
            return {"status": "skipped", "reason": "current-version-unavailable"}

        resolved = await self._resolve_startup_package_channel(
            package_name=package_name,
            channel=channel,
            timeout_ms=timeout_ms,
        )
        target_version = resolved.get("version")
        target_tag = resolved.get("tag")
        if not isinstance(target_version, str) or not target_version.strip():
            return {
                "status": "skipped",
                "reason": "target-version-unavailable",
                "channel": channel,
            }
        comparison = _compare_update_semver_strings(current_version, target_version)
        if comparison is not None and comparison >= 0:
            return {
                "status": "skipped",
                "reason": "up-to-date",
                "channel": channel,
                "targetVersion": target_version,
            }
        package_manager = _detect_package_manager(package_root)
        if package_manager == "unknown":
            return {"status": "error", "reason": "package-manager-unavailable"}
        effective_timeout_ms = (
            timeout_ms if timeout_ms is not None else _STARTUP_AUTO_UPDATE_COMMAND_TIMEOUT_MS
        )
        payload = await self.run_package_update(
            package_root=package_root,
            package_manager=package_manager,
            package_spec=f"{package_name}@{target_tag}",
            timeout_ms=effective_timeout_ms,
        )
        result = dict(payload)
        result["autoUpdate"] = {
            "channel": channel,
            "tag": target_tag,
            "targetVersion": target_version,
        }
        return result

    async def _resolve_startup_package_channel(
        self,
        *,
        package_name: str,
        channel: str,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        channel_tag = _channel_to_package_tag(channel)
        channel_version = await self._fetch_package_version(
            package_name,
            channel_tag,
            timeout_ms,
        )
        if channel != "beta":
            return {"tag": channel_tag, "version": channel_version}
        latest_version = await self._fetch_package_version(package_name, "latest", timeout_ms)
        if not latest_version:
            return {"tag": channel_tag, "version": channel_version}
        if not channel_version:
            return {"tag": "latest", "version": latest_version}
        comparison = _compare_update_semver_strings(channel_version, latest_version)
        if comparison is not None and comparison < 0:
            return {"tag": "latest", "version": latest_version}
        return {"tag": channel_tag, "version": channel_version}

    async def _fetch_package_version(
        self,
        package_name: str,
        tag: str,
        timeout_ms: int | None,
    ) -> str | None:
        if self._package_version_resolver is not None:
            return await self._package_version_resolver(package_name, tag, timeout_ms)
        try:
            result = await self._update_command_runner(
                ["npm", "view", f"{package_name}@{tag}", "version", "--json"],
                self._package_root,
                timeout_ms,
            )
        except Exception:
            logger.debug("Could not resolve package update version.", exc_info=True)
            return None
        if _update_command_exit_code(result.get("exitCode")) != 0:
            return None
        stdout = result.get("stdout")
        if not isinstance(stdout, str) or not stdout.strip():
            return None
        raw = stdout.strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw.strip('"')
        return parsed.strip() if isinstance(parsed, str) and parsed.strip() else None

    async def run_update(
        self,
        *,
        timeout_ms: int | None = None,
        dev_target_ref: str | None = None,
        channel: str | None = None,
    ) -> dict[str, object]:
        started_at = time.monotonic()
        steps: list[dict[str, object]] = []
        root = self.repo_root
        normalized_dev_target_ref = _normalize_dev_target_ref(dev_target_ref)
        normalized_channel = _normalize_update_channel(channel)
        if root is None:
            return {
                "status": "error",
                "mode": "unknown",
                "reason": "repo-root-unavailable",
                "steps": steps,
                "durationMs": 0,
            }
        before_sha = self._snapshot.current_revision or self.startup_revision
        before = {"sha": before_sha, "version": None}

        status_step = await self._run_update_command_step(
            "git status",
            ["git", "status", "--porcelain", "--", ":!dist/control-ui/"],
            timeout_ms=timeout_ms,
        )
        steps.append(status_step)
        if _update_step_exit_code(status_step) != 0:
            return self._build_update_command_result(
                status="error",
                reason="git-status-failed",
                root=root,
                before=before,
                after=None,
                steps=steps,
                started_at=started_at,
            )
        status_stdout = _update_step_stdout_tail(status_step)
        if status_stdout:
            return self._build_update_command_result(
                status="skipped",
                reason="dirty",
                root=root,
                before=before,
                after=before,
                steps=steps,
                started_at=started_at,
            )

        if normalized_channel == "dev" and normalized_dev_target_ref is None:
            branch = await self._read_update_branch_name(root=root, timeout_ms=timeout_ms)
            if branch != _UPDATE_DEV_BRANCH:
                checkout_main_step = await self._run_update_command_step(
                    f"git checkout {_UPDATE_DEV_BRANCH}",
                    ["git", "checkout", _UPDATE_DEV_BRANCH],
                    timeout_ms=timeout_ms,
                )
                steps.append(checkout_main_step)
                if _update_step_exit_code(checkout_main_step) != 0:
                    return self._build_update_command_result(
                        status="error",
                        reason="checkout-failed",
                        root=root,
                        before=before,
                        after=None,
                        steps=steps,
                        started_at=started_at,
                    )

        fetch_step = await self._run_update_command_step(
            "git fetch",
            ["git", "fetch", "--all", "--prune", "--tags"],
            timeout_ms=timeout_ms,
        )
        steps.append(fetch_step)
        if _update_step_exit_code(fetch_step) != 0:
            return self._build_update_command_result(
                status="error",
                reason="fetch-failed",
                root=root,
                before=before,
                after=None,
                steps=steps,
                started_at=started_at,
            )

        if normalized_channel in {"stable", "beta"}:
            release_tags = await self._read_update_tags(root=root, timeout_ms=timeout_ms)
            release_tag = _resolve_update_channel_tag(release_tags, normalized_channel)
            if release_tag is None:
                return self._build_update_command_result(
                    status="error",
                    reason="no-release-tag",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )
            checkout_step = await self._run_update_command_step(
                f"git checkout {release_tag}",
                ["git", "checkout", "--detach", release_tag],
                timeout_ms=timeout_ms,
            )
            steps.append(checkout_step)
            if _update_step_exit_code(checkout_step) != 0:
                return self._build_update_command_result(
                    status="error",
                    reason="checkout-failed",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )
            return await self._complete_git_update_after_checkout(
                root=root,
                before=before,
                steps=steps,
                timeout_ms=timeout_ms,
                started_at=started_at,
            )

        preflight_base_sha: str | None = None
        candidates: list[str]
        if normalized_dev_target_ref is not None:
            target_sha: str | None = None
            for target_ref_candidate in _dev_target_ref_resolution_candidates(
                normalized_dev_target_ref
            ):
                target_sha_step = await self._run_update_command_step(
                    f"git rev-parse {target_ref_candidate}",
                    ["git", "rev-parse", target_ref_candidate],
                    timeout_ms=timeout_ms,
                )
                steps.append(target_sha_step)
                resolved_target_sha = (
                    _update_step_stdout_tail(target_sha_step) or ""
                ).strip()
                if _update_step_exit_code(target_sha_step) == 0 and resolved_target_sha:
                    target_sha = resolved_target_sha
                    break
            if target_sha is None:
                return self._build_update_command_result(
                    status="error",
                    reason="no-target-sha",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )
            preflight_base_sha = target_sha
            candidates = [target_sha]
        else:
            upstream_step = await self._run_update_command_step(
                "upstream check",
                [
                    "git",
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}",
                ],
                timeout_ms=timeout_ms,
            )
            steps.append(upstream_step)
            if _update_step_exit_code(upstream_step) != 0:
                return self._build_update_command_result(
                    status="skipped",
                    reason="no-upstream",
                    root=root,
                    before=before,
                    after=before,
                    steps=steps,
                    started_at=started_at,
                )

            upstream_sha_step = await self._run_update_command_step(
                "git rev-parse @{upstream}",
                ["git", "rev-parse", "@{upstream}"],
                timeout_ms=timeout_ms,
            )
            steps.append(upstream_sha_step)
            upstream_sha = (_update_step_stdout_tail(upstream_sha_step) or "").strip()
            if _update_step_exit_code(upstream_sha_step) != 0 or not upstream_sha:
                return self._build_update_command_result(
                    status="error",
                    reason="no-upstream-sha",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )

            rev_list_step = await self._run_update_command_step(
                "git rev-list",
                [
                    "git",
                    "rev-list",
                    f"--max-count={_UPDATE_PREFLIGHT_MAX_COMMITS}",
                    upstream_sha,
                ],
                timeout_ms=timeout_ms,
            )
            steps.append(rev_list_step)
            if _update_step_exit_code(rev_list_step) != 0:
                return self._build_update_command_result(
                    status="error",
                    reason="preflight-revlist-failed",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )
            candidates = [
                line.strip()
                for line in (_update_step_stdout_tail(rev_list_step) or "").splitlines()
                if line.strip()
            ]
            if not candidates:
                return self._build_update_command_result(
                    status="error",
                    reason="preflight-no-candidates",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )
            preflight_base_sha = upstream_sha

        if preflight_base_sha is None:
            return self._build_update_command_result(
                status="error",
                reason="preflight-base-unavailable",
                root=root,
                before=before,
                after=None,
                steps=steps,
                started_at=started_at,
            )
        preflight_root = Path(tempfile.mkdtemp(prefix="openzues-update-preflight-"))
        worktree_dir = preflight_root / ("wt" if os.name == "nt" else "worktree")
        worktree_step = await self._run_update_command_step(
            "preflight worktree",
            ["git", "worktree", "add", "--detach", str(worktree_dir), preflight_base_sha],
            timeout_ms=timeout_ms,
        )
        steps.append(worktree_step)
        if _update_step_exit_code(worktree_step) != 0:
            shutil.rmtree(preflight_root, ignore_errors=True)
            return self._build_update_command_result(
                status="error",
                reason="preflight-worktree-failed",
                root=root,
                before=before,
                after=None,
                steps=steps,
                started_at=started_at,
            )

        selected_sha: str | None = None
        try:
            for candidate_sha in candidates:
                short_sha = candidate_sha[:8]
                checkout_step = await self._run_update_command_step_at(
                    f"preflight checkout ({short_sha})",
                    ["git", "checkout", "--detach", candidate_sha],
                    cwd=worktree_dir,
                    timeout_ms=timeout_ms,
                )
                steps.append(checkout_step)
                if _update_step_exit_code(checkout_step) != 0:
                    continue

                deps_step = await self._run_update_command_step_at(
                    f"preflight deps install ({short_sha})",
                    [sys.executable, "-m", "pip", "install", "-e", "."],
                    cwd=worktree_dir,
                    timeout_ms=timeout_ms,
                )
                steps.append(deps_step)
                if _update_step_exit_code(deps_step) != 0:
                    continue

                build_step = await self._run_update_command_step_at(
                    f"preflight build ({short_sha})",
                    [sys.executable, "-m", "compileall", "-q", "src"],
                    cwd=worktree_dir,
                    timeout_ms=timeout_ms,
                )
                steps.append(build_step)
                if _update_step_exit_code(build_step) != 0:
                    continue

                selected_sha = candidate_sha
                break
        finally:
            cleanup_step = await self._run_update_command_step(
                "preflight cleanup",
                ["git", "worktree", "remove", "--force", str(worktree_dir)],
                timeout_ms=timeout_ms,
            )
            steps.append(cleanup_step)
            shutil.rmtree(preflight_root, ignore_errors=True)
            if _update_step_exit_code(cleanup_step) != 0 and not preflight_root.exists():
                cleanup_log = cleanup_step.get("log")
                if isinstance(cleanup_log, dict):
                    cleanup_log["exitCode"] = 0
                    fallback_message = (
                        "windows fallback cleanup removed preflight tree"
                        if os.name == "nt"
                        else "fallback cleanup removed preflight tree"
                    )
                    stderr_tail = cleanup_log.get("stderrTail")
                    cleanup_log["stderrTail"] = _trim_update_log_tail(
                        "\n".join(
                            str(part)
                            for part in (stderr_tail, fallback_message)
                            if part
                        )
                    )

        if selected_sha is None:
            return self._build_update_command_result(
                status="error",
                reason="preflight-no-good-commit",
                root=root,
                before=before,
                after=None,
                steps=steps,
                started_at=started_at,
            )

        if normalized_dev_target_ref is not None:
            checkout_step = await self._run_update_command_step(
                f"git checkout {selected_sha}",
                ["git", "checkout", "--detach", selected_sha],
                timeout_ms=timeout_ms,
            )
            steps.append(checkout_step)
            if _update_step_exit_code(checkout_step) != 0:
                return self._build_update_command_result(
                    status="error",
                    reason="checkout-failed",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )
        else:
            rebase_step = await self._run_update_command_step(
                "git rebase",
                ["git", "rebase", selected_sha],
                timeout_ms=timeout_ms,
            )
            steps.append(rebase_step)
            if _update_step_exit_code(rebase_step) != 0:
                abort_step = await self._run_update_command_step(
                    "git rebase --abort",
                    ["git", "rebase", "--abort"],
                    timeout_ms=timeout_ms,
                )
                steps.append(abort_step)
                return self._build_update_command_result(
                    status="error",
                    reason="rebase-failed",
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )

        return await self._complete_git_update_after_checkout(
            root=root,
            before=before,
            steps=steps,
            timeout_ms=timeout_ms,
            started_at=started_at,
        )

    async def _complete_git_update_after_checkout(
        self,
        *,
        root: Path,
        before: dict[str, str | None],
        steps: list[dict[str, object]],
        timeout_ms: int | None,
        started_at: float,
    ) -> dict[str, object]:
        for name, argv, reason in (
            (
                "deps install",
                [sys.executable, "-m", "pip", "install", "-e", "."],
                "deps-install-failed",
            ),
            ("build", [sys.executable, "-m", "compileall", "-q", "src"], "build-failed"),
        ):
            step = await self._run_update_command_step(name, argv, timeout_ms=timeout_ms)
            steps.append(step)
            if _update_step_exit_code(step) != 0:
                return self._build_update_command_result(
                    status="error",
                    reason=reason,
                    root=root,
                    before=before,
                    after=None,
                    steps=steps,
                    started_at=started_at,
                )

        after_sha = await asyncio.to_thread(self._revision_resolver, root)
        after = {"sha": after_sha, "version": None}
        self._snapshot.last_checked_at = _utcnow_iso()
        self._snapshot.current_revision = after_sha
        self._snapshot.safe_to_restart = await self._is_safe_restart_boundary()
        self._snapshot.pending_revision = (
            after_sha
            if after_sha is not None and after_sha != self.startup_revision
            else None
        )
        self._snapshot.pending_restart = self._snapshot.pending_revision is not None
        self._snapshot.last_error = None
        return self._build_update_command_result(
            status="ok",
            reason=None,
            root=root,
            before=before,
            after=after,
            steps=steps,
            started_at=started_at,
        )

    async def run_package_update(
        self,
        *,
        package_root: Path,
        package_manager: str,
        package_spec: str,
        timeout_ms: int | None = None,
    ) -> dict[str, object]:
        started_at = time.monotonic()
        steps: list[dict[str, object]] = []
        before = {"sha": None, "version": _read_package_version(package_root)}
        package_name = _read_package_name(package_root)
        _cleanup_global_rename_dirs(package_root, package_name)
        warnings: list[str] = []
        disk_warning = _create_low_disk_space_warning(
            target_path=package_root.parent,
            purpose="global package update",
        )
        if disk_warning is not None:
            warnings.append(disk_warning)
        manager = package_manager.strip().lower()
        install_env = _global_package_update_env()
        staged_install: _StagedNpmInstall | None = None
        if manager == "npm":
            staged_install, failed_stage_step = _create_staged_npm_install(
                package_root,
                package_name,
            )
            if failed_stage_step is not None:
                steps.append(failed_stage_step)
                return self._build_package_update_result(
                    status="error",
                    reason="global-install-stage-failed",
                    mode=package_manager,
                    root=package_root,
                    before=before,
                    after=None,
                    steps=steps,
                    warnings=warnings,
                    started_at=started_at,
                )
        argv = _global_package_update_args(
            package_manager,
            package_spec,
            install_prefix=staged_install.prefix if staged_install is not None else None,
            package_root=package_root,
            package_name=package_name,
        )
        if argv is None:
            _cleanup_staged_npm_install(staged_install)
            return self._build_package_update_result(
                status="error",
                reason="package-manager-unavailable",
                mode=package_manager or "unknown",
                root=package_root,
                before=before,
                after=None,
                steps=steps,
                warnings=warnings,
                started_at=started_at,
            )

        try:
            step = await self._run_update_command_step_at(
                "global update",
                argv,
                cwd=package_root,
                timeout_ms=timeout_ms,
                env=install_env,
            )
            steps.append(step)
            if _update_step_exit_code(step) != 0:
                _cleanup_staged_npm_install(staged_install)
                staged_install = None
                fallback_prefix: Path | None = None
                if manager == "npm":
                    staged_install, failed_stage_step = _create_staged_npm_install(
                        package_root,
                        package_name,
                    )
                    if failed_stage_step is not None:
                        steps.append(failed_stage_step)
                        return self._build_package_update_result(
                            status="error",
                            reason="global-install-stage-failed",
                            mode=package_manager,
                            root=package_root,
                            before=before,
                            after=None,
                            steps=steps,
                            warnings=warnings,
                            started_at=started_at,
                        )
                    assert staged_install is not None
                    fallback_prefix = staged_install.prefix
                fallback_argv = _global_package_update_fallback_args(
                    package_manager,
                    package_spec,
                    install_prefix=fallback_prefix,
                    package_root=package_root,
                    package_name=package_name,
                )
                if fallback_argv is not None:
                    fallback_step = await self._run_update_command_step_at(
                        "global update (omit optional)",
                        fallback_argv,
                        cwd=package_root,
                        timeout_ms=timeout_ms,
                        env=install_env,
                    )
                    steps.append(fallback_step)
                    step = fallback_step
            if _update_step_exit_code(step) != 0:
                return self._build_package_update_result(
                    status="error",
                    reason="global-update-failed",
                    mode=package_manager,
                    root=package_root,
                    before=before,
                    after=None,
                    steps=steps,
                    warnings=warnings,
                    started_at=started_at,
                )

            verification_root = (
                staged_install.package_root if staged_install is not None else package_root
            )
            after_version = _read_package_version(verification_root)
            after = {"sha": None, "version": after_version}
            expected_version = _expected_package_version_from_spec(package_spec)
            verification_errors = _collect_package_update_verify_errors(
                verification_root,
                expected_version=expected_version,
            )
            if verification_errors:
                verify_step = {
                    "name": "global install verify",
                    "command": f"verify {verification_root}",
                    "cwd": str(verification_root),
                    "durationMs": 0,
                    "log": {
                        "stdoutTail": None,
                        "stderrTail": "\n".join(verification_errors),
                        "exitCode": 1,
                    },
                }
                steps.append(verify_step)
                live_after = {"sha": None, "version": _read_package_version(package_root)}
                return self._build_package_update_result(
                    status="error",
                    reason="global-install-verify-failed",
                    mode=package_manager,
                    root=package_root,
                    before=before,
                    after=live_after,
                    steps=steps,
                    warnings=warnings,
                    started_at=started_at,
                )
            if staged_install is not None:
                swap_step = _swap_staged_npm_install(
                    stage=staged_install,
                    package_root=package_root,
                    package_name=package_name,
                )
                steps.append(swap_step)
                if _update_step_exit_code(swap_step) != 0:
                    live_after = {"sha": None, "version": _read_package_version(package_root)}
                    return self._build_package_update_result(
                        status="error",
                        reason="global-install-swap-failed",
                        mode=package_manager,
                        root=package_root,
                        before=before,
                        after=live_after,
                        steps=steps,
                        warnings=warnings,
                        started_at=started_at,
                    )
            doctor_step = await self._run_update_command_step_at(
                "openzues doctor",
                _post_package_update_doctor_args(),
                cwd=package_root,
                timeout_ms=timeout_ms,
                env=_post_package_update_doctor_env(),
            )
            steps.append(doctor_step)
            if _update_step_exit_code(doctor_step) != 0:
                live_after = {"sha": None, "version": _read_package_version(package_root)}
                return self._build_package_update_result(
                    status="error",
                    reason="post-update-doctor-failed",
                    mode=package_manager,
                    root=package_root,
                    before=before,
                    after=live_after,
                    steps=steps,
                    warnings=warnings,
                    started_at=started_at,
                )
            return self._build_package_update_result(
                status="ok",
                reason=None,
                mode=package_manager,
                root=package_root,
                before=before,
                after=after,
                steps=steps,
                warnings=warnings,
                started_at=started_at,
            )
        finally:
            _cleanup_staged_npm_install(staged_install)

    async def _run_update_command_step(
        self,
        name: str,
        argv: list[str],
        *,
        timeout_ms: int | None,
    ) -> dict[str, object]:
        root = self.repo_root
        if root is None:
            return {
                "name": name,
                "command": " ".join(argv),
                "cwd": "",
                "durationMs": 0,
                "log": {
                    "stdoutTail": None,
                    "stderrTail": "repo root unavailable",
                    "exitCode": 1,
                },
            }
        started_at = time.monotonic()
        return await self._run_update_command_step_at(
            name,
            argv,
            cwd=root,
            timeout_ms=timeout_ms,
            started_at=started_at,
        )

    async def _read_update_branch_name(
        self,
        *,
        root: Path,
        timeout_ms: int | None,
    ) -> str | None:
        try:
            result = await self._update_command_runner(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                root,
                timeout_ms,
            )
        except Exception:
            logger.debug("Could not read update branch.", exc_info=True)
            return None
        if _update_command_exit_code(result.get("exitCode")) != 0:
            return None
        stdout = result.get("stdout")
        if not isinstance(stdout, str):
            return None
        branch = stdout.strip()
        return branch or None

    async def _read_update_tags(
        self,
        *,
        root: Path,
        timeout_ms: int | None,
        pattern: str = "v*",
    ) -> list[str]:
        try:
            result = await self._update_command_runner(
                ["git", "tag", "--list", pattern, "--sort=-v:refname"],
                root,
                timeout_ms,
            )
        except Exception:
            logger.debug("Could not read update tags.", exc_info=True)
            return []
        if _update_command_exit_code(result.get("exitCode")) != 0:
            return []
        stdout = result.get("stdout")
        if not isinstance(stdout, str):
            return []
        return [line.strip() for line in stdout.splitlines() if line.strip()]

    async def _run_update_command_step_at(
        self,
        name: str,
        argv: list[str],
        *,
        cwd: Path,
        timeout_ms: int | None,
        started_at: float | None = None,
        env: Mapping[str, str] | None = None,
    ) -> dict[str, object]:
        started_at = time.monotonic() if started_at is None else started_at
        previous_env = _apply_command_env(env)
        try:
            result = await self._update_command_runner(argv, cwd, timeout_ms)
        finally:
            _restore_command_env(previous_env)
        return {
            "name": name,
            "command": " ".join(argv),
            "cwd": str(cwd),
            "durationMs": int((time.monotonic() - started_at) * 1000),
            "log": {
                "stdoutTail": _trim_update_log_tail(result.get("stdout")),
                "stderrTail": _trim_update_log_tail(result.get("stderr")),
                "exitCode": _update_command_exit_code(result.get("exitCode")),
            },
        }

    def _build_update_command_result(
        self,
        *,
        status: str,
        reason: str | None,
        root: Path,
        before: dict[str, str | None],
        after: dict[str, str | None] | None,
        steps: list[dict[str, object]],
        warnings: list[str] | None = None,
        started_at: float,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "status": status,
            "mode": "git",
            "root": str(root),
            "before": before,
            "after": after,
            "steps": steps,
            "durationMs": int((time.monotonic() - started_at) * 1000),
        }
        if warnings:
            result["warnings"] = list(warnings)
        if reason is not None:
            result["reason"] = reason
        if status == "error":
            failed_step = _first_failed_update_step(steps)
            if failed_step is not None:
                result["failedStep"] = failed_step
        return result

    def _build_package_update_result(
        self,
        *,
        status: str,
        reason: str | None,
        mode: str,
        root: Path,
        before: dict[str, str | None],
        after: dict[str, str | None] | None,
        steps: list[dict[str, object]],
        warnings: list[str] | None = None,
        started_at: float,
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "status": status,
            "mode": mode.strip().lower() or "unknown",
            "root": str(root),
            "before": before,
            "after": after,
            "steps": steps,
            "durationMs": int((time.monotonic() - started_at) * 1000),
        }
        if warnings:
            result["warnings"] = list(warnings)
        if reason is not None:
            result["reason"] = reason
        if status == "error":
            failed_step = _first_failed_update_step(steps)
            if failed_step is not None:
                result["failedStep"] = failed_step
        return result

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(
            self._runner_loop(),
            name="openzues-runtime-updates",
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

    async def tick(self) -> bool:
        self._snapshot.last_checked_at = _utcnow_iso()
        if not self._snapshot.enabled or self.repo_root is None or self.startup_revision is None:
            return False
        try:
            current_revision = await asyncio.to_thread(
                self._revision_resolver,
                self.repo_root,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            self._snapshot.last_error = str(exc)
            logger.exception("Runtime update poll failed.")
            return False

        self._snapshot.current_revision = current_revision
        self._snapshot.safe_to_restart = await self._is_safe_restart_boundary()
        if current_revision is None or current_revision == self.startup_revision:
            self._snapshot.pending_revision = None
            self._snapshot.pending_restart = False
            self._snapshot.restart_in_progress = False
            self._snapshot.last_error = None
            return False

        self._snapshot.pending_revision = current_revision
        self._snapshot.pending_restart = True
        if not self._snapshot.safe_to_restart or self._snapshot.restart_in_progress:
            return False

        self._snapshot.restart_in_progress = True
        self._snapshot.last_restart_at = _utcnow_iso()
        try:
            await self._restart_callback()
        except Exception as exc:  # pragma: no cover - defensive guard
            self._snapshot.last_error = str(exc)
            self._snapshot.restart_in_progress = False
            logger.exception("Runtime self-update restart failed.")
            return False
        return True

    async def _runner_loop(self) -> None:
        try:
            await self.run_startup_auto_update_check()
        except Exception:  # pragma: no cover - defensive guard
            logger.exception("Startup auto-update check failed.")
        while not self._stop_event.is_set():
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - defensive guard
                logger.exception("Runtime update loop crashed.")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                continue

    async def _is_safe_restart_boundary(self) -> bool:
        missions = await self.database.list_missions()
        return not any(bool(mission.get("in_progress")) for mission in missions)
