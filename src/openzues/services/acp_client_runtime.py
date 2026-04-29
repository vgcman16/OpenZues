from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

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
        default_server_args=effective_server_args,
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
