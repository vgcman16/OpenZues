from __future__ import annotations

import asyncio
import json
import logging
import os
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


RuntimeUpdateCommandRunner = Callable[
    [list[str], Path, int | None],
    Awaitable[dict[str, object]],
]


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


def _collect_package_dist_inventory(package_root: Path) -> list[str]:
    dist_root = package_root / "dist"
    if not _path_exists(dist_root):
        return []
    files: list[str] = []
    for path in dist_root.rglob("*"):
        try:
            if not path.is_file() or path.is_symlink():
                continue
        except OSError:
            continue
        relative_path = path.relative_to(package_root).as_posix()
        if relative_path == _PACKAGE_DIST_INVENTORY_RELATIVE_PATH.as_posix():
            continue
        files.append(relative_path)
    return sorted(set(files))


def _collect_package_dist_inventory_file_errors(
    package_root: Path,
    inventory_files: Sequence[str],
) -> list[str]:
    actual_files = _collect_package_dist_inventory(package_root)
    actual_set = set(actual_files)
    inventory_set = set(inventory_files)
    errors: list[str] = []
    for relative_path in inventory_files:
        if relative_path not in actual_set:
            errors.append(f"missing packaged dist file {relative_path}")
    for relative_path in actual_files:
        if relative_path not in inventory_set:
            errors.append(f"unexpected packaged dist file {relative_path}")
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
    elif inventory_files is not None:
        errors.extend(
            _collect_package_dist_inventory_file_errors(package_root, inventory_files)
        )
    elif (
        _should_require_packaged_dist_inventory(installed_version)
        or _should_require_packaged_dist_inventory(expected_version)
    ):
        errors.append(
            "missing package dist inventory "
            f"{_PACKAGE_DIST_INVENTORY_RELATIVE_PATH.as_posix()}"
        )
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
    ) -> None:
        self.database = database
        self.poll_interval_seconds = max(5, int(poll_interval_seconds))
        self._restart_callback = restart_callback
        self._revision_resolver = revision_resolver
        self._update_command_runner = update_command_runner or _default_update_command_runner
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

    async def run_update(self, *, timeout_ms: int | None = None) -> dict[str, object]:
        started_at = time.monotonic()
        steps: list[dict[str, object]] = []
        root = self.repo_root
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
            ["git", "status", "--porcelain"],
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

        for name, argv, reason in (
            ("git fetch", ["git", "fetch", "--all", "--prune", "--tags"], "fetch-failed"),
            ("git pull", ["git", "pull", "--ff-only"], "pull-failed"),
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
