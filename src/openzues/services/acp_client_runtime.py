from __future__ import annotations

import os
import re
import shutil
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ACP_SERVER_COMMAND = "openzues"
DEFAULT_ACP_SERVER_ARGS = ("acp",)
ACP_CLIENT_SHELL = "acp-client"
KNOWN_PROVIDER_AUTH_ENV_KEYS = (
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "HF_TOKEN",
)


@dataclass(frozen=True, slots=True)
class AcpClientSpawnPlan:
    cwd: str | None
    server_command: str
    server_args: tuple[str, ...]
    env: dict[str, str]
    strip_provider_auth_env_vars: bool
    stripped_env_keys: tuple[str, ...]
    verbose: bool
    server_verbose: bool


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def build_acp_client_server_args(
    server_args: Sequence[str] | None = None,
    *,
    server_verbose: bool = False,
) -> tuple[str, ...]:
    args = [*DEFAULT_ACP_SERVER_ARGS]
    args.extend(str(arg) for arg in (server_args or ()))
    if server_verbose and "--verbose" not in args and "-v" not in args:
        args.append("--verbose")
    return tuple(args)


def should_strip_provider_auth_env_vars_for_acp_server(
    *,
    server_command: str | None,
    server_args: Sequence[str] | None,
    default_server_command: str = DEFAULT_ACP_SERVER_COMMAND,
    default_server_args: Sequence[str] = DEFAULT_ACP_SERVER_ARGS,
) -> bool:
    explicit_command = _optional_string(server_command)
    if explicit_command is None:
        return True
    if explicit_command != default_server_command:
        return False
    return tuple(server_args or ()) == tuple(default_server_args)


def build_acp_client_strip_keys(
    *,
    strip_provider_auth_env_vars: bool,
    active_skill_env_keys: Iterable[str] = (),
) -> tuple[str, ...]:
    keys = {key.strip() for key in active_skill_env_keys if key.strip()}
    if strip_provider_auth_env_vars:
        keys.update(KNOWN_PROVIDER_AUTH_ENV_KEYS)
    return tuple(sorted(keys))


def resolve_acp_client_spawn_env(
    base_env: Mapping[str, str] | None = None,
    *,
    strip_keys: Iterable[str] = (),
) -> dict[str, str]:
    source_env = os.environ if base_env is None else base_env
    normalized_strip_keys = {key.upper() for key in strip_keys}
    env = {
        key: value
        for key, value in source_env.items()
        if key.upper() not in normalized_strip_keys and key.upper() != "OPENCLAW_SHELL"
    }
    env["OPENCLAW_SHELL"] = ACP_CLIENT_SHELL
    return env


def _stripped_env_key_names(
    base_env: Mapping[str, str],
    strip_keys: Iterable[str],
) -> tuple[str, ...]:
    canonical_by_upper = {key.upper(): key for key in strip_keys}
    matched = {
        canonical_by_upper[key.upper()]
        for key in base_env
        if key.upper() in canonical_by_upper
    }
    return tuple(sorted(matched))


def build_acp_client_spawn_plan(
    *,
    cwd: str | None = None,
    server: str | None = None,
    server_args: Sequence[str] | None = None,
    server_verbose: bool = False,
    verbose: bool = False,
    base_env: Mapping[str, str] | None = None,
    active_skill_env_keys: Iterable[str] = (),
) -> AcpClientSpawnPlan:
    resolved_cwd = _optional_string(cwd)
    server_command = _optional_string(server) or DEFAULT_ACP_SERVER_COMMAND
    effective_server_args = build_acp_client_server_args(
        server_args,
        server_verbose=server_verbose,
    )
    strip_provider_auth_env_vars = should_strip_provider_auth_env_vars_for_acp_server(
        server_command=server,
        server_args=effective_server_args,
        default_server_command=DEFAULT_ACP_SERVER_COMMAND,
        default_server_args=DEFAULT_ACP_SERVER_ARGS,
    )
    strip_keys = build_acp_client_strip_keys(
        strip_provider_auth_env_vars=strip_provider_auth_env_vars,
        active_skill_env_keys=active_skill_env_keys,
    )
    source_env = os.environ if base_env is None else base_env
    return AcpClientSpawnPlan(
        cwd=resolved_cwd,
        server_command=server_command,
        server_args=effective_server_args,
        env=resolve_acp_client_spawn_env(source_env, strip_keys=strip_keys),
        strip_provider_auth_env_vars=strip_provider_auth_env_vars,
        stripped_env_keys=_stripped_env_key_names(source_env, strip_keys),
        verbose=verbose,
        server_verbose=server_verbose,
    )


def resolve_acp_client_spawn_invocation(
    *,
    server_command: str,
    server_args: Sequence[str],
    platform: str | None = None,
    env: Mapping[str, str] | None = None,
    executable: str | None = None,
) -> dict[str, object]:
    resolved_platform = platform or sys.platform
    args = tuple(str(arg) for arg in server_args)
    if resolved_platform != "win32":
        return {
            "command": server_command,
            "args": args,
        }
    command_path = _resolve_windows_acp_client_command_path(server_command, env or os.environ)
    if command_path is None or command_path.suffix.lower() not in {".cmd", ".bat"}:
        return {
            "command": server_command,
            "args": args,
            "shell": False,
            "windowsHide": True,
        }
    entry_path = _resolve_windows_acp_client_shim_entry(command_path)
    if entry_path is None:
        raise ValueError(
            f"Cannot resolve ACP client wrapper {command_path} without shell execution."
        )
    return {
        "command": executable or sys.executable,
        "args": (str(entry_path), *args),
        "windowsHide": True,
    }


def _resolve_windows_acp_client_command_path(
    command: str,
    env: Mapping[str, str],
) -> Path | None:
    command_path = Path(command)
    if command_path.is_absolute() or command_path.parent != Path("."):
        return command_path if command_path.exists() else None
    path_value = env.get("PATH") or env.get("Path") or ""
    pathext = env.get("PATHEXT") or ".COM;.EXE;.BAT;.CMD"
    extensions = [entry.lower() for entry in pathext.split(";") if entry]
    for directory in path_value.split(os.pathsep):
        if not directory:
            continue
        base = Path(directory) / command
        candidates = [base]
        if base.suffix.lower() not in extensions:
            candidates.extend(Path(f"{base}{extension.lower()}") for extension in extensions)
        for candidate in candidates:
            if candidate.exists():
                return candidate
    resolved = shutil.which(command, path=path_value)
    return Path(resolved) if resolved else None


def _resolve_windows_acp_client_shim_entry(shim_path: Path) -> Path | None:
    try:
        content = shim_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r'"%~dp0\\([^"]+)"\s+%[*]', content, flags=re.IGNORECASE)
    if match is None:
        match = re.search(r'"%~dp0([^"]+)"\s+%[*]', content, flags=re.IGNORECASE)
    if match is None:
        return None
    relative = match.group(1).lstrip("\\/")
    entry_path = shim_path.parent / Path(relative)
    return entry_path if entry_path.exists() else None
