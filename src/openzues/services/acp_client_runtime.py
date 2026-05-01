from __future__ import annotations

import inspect
import os
import re
import shutil
import sys
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlparse

DEFAULT_ACP_SERVER_COMMAND = "openzues"
DEFAULT_ACP_SERVER_ARGS = ("acp",)
ACP_CLIENT_SHELL = "acp-client"
KNOWN_PROVIDER_AUTH_ENV_KEYS = (
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "HF_TOKEN",
)
_SAFE_SEARCH_TOOL_IDS = {"search", "web_search", "memory_search"}
_TRUSTED_SAFE_TOOL_ALIASES = {"search"}
_EXEC_CAPABLE_TOOL_IDS = {
    "exec",
    "spawn",
    "shell",
    "bash",
    "process",
    "code_execution",
}
_CONTROL_PLANE_TOOL_IDS = {"sessions_spawn", "sessions_send", "session_status"}
AcpApprovalClass = Literal[
    "readonly_scoped",
    "readonly_search",
    "mutating",
    "exec_capable",
    "control_plane",
    "interactive",
    "other",
    "unknown",
]
_OWNER_ONLY_TOOL_APPROVAL_CLASSES: dict[str, AcpApprovalClass] = {
    "whatsapp_login": "interactive",
    "cron": "control_plane",
    "gateway": "control_plane",
    "nodes": "exec_capable",
}
_KNOWN_CORE_TOOL_IDS = {
    "read",
    "write",
    "edit",
    "apply_patch",
    "exec",
    "process",
    "code_execution",
    "web_search",
    "web_fetch",
    "x_search",
    "memory_search",
    "memory_get",
    "sessions_list",
    "sessions_history",
    "sessions_send",
    "sessions_spawn",
    "sessions_yield",
    "session_status",
    "update_plan",
    "cron",
    "gateway",
    "canvas",
    "nodes",
}
_READ_ONLY_ACTIONS = {
    "get",
    "list",
    "read",
    "status",
    "show",
    "fetch",
    "search",
    "query",
    "view",
    "poll",
    "log",
    "inspect",
    "check",
    "probe",
}
_PROCESS_MUTATING_ACTIONS = {"write", "send_keys", "submit", "paste", "kill"}
_MESSAGE_MUTATING_ACTIONS = {
    "send",
    "reply",
    "thread_reply",
    "threadreply",
    "edit",
    "delete",
    "react",
    "pin",
    "unpin",
}
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
AcpPermissionPrompt = Callable[[str | None, str], Awaitable[bool] | bool]
AcpPermissionLogger = Callable[[str], object]


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


@dataclass(frozen=True, slots=True)
class AcpPermissionClassification:
    tool_name: str | None
    approval_class: AcpApprovalClass
    auto_approve: bool


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _optional_object_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_lowercase_string(value: object) -> str:
    return str(value).strip().lower()


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _read_first_string_value(
    source: Mapping[str, object] | None,
    keys: Sequence[str],
) -> str | None:
    if source is None:
        return None
    for key in keys:
        value = _optional_object_string(source.get(key))
        if value is not None:
            return value
    return None


def _normalize_tool_name(value: str) -> str | None:
    normalized = value.strip().lower()
    if not normalized or len(normalized) > 128:
        return None
    return normalized if re.fullmatch(r"[a-z0-9._-]+", normalized) else None


def _parse_tool_name_from_title(title: object) -> str | None:
    if not isinstance(title, str) or not title:
        return None
    head = title.split(":", 1)[0].strip()
    return _normalize_tool_name(head) if head else None


def _resolve_tool_name_for_permission(tool_call: Mapping[str, object] | None) -> str | None:
    tool_meta = _as_mapping(tool_call.get("_meta")) if tool_call is not None else None
    raw_input = _as_mapping(tool_call.get("rawInput")) if tool_call is not None else None
    from_meta = _read_first_string_value(tool_meta, ("toolName", "tool_name", "name"))
    from_raw_input = _read_first_string_value(raw_input, ("tool", "toolName", "tool_name", "name"))
    from_title = _parse_tool_name_from_title(tool_call.get("title") if tool_call else None)
    meta_name = _normalize_tool_name(from_meta) if from_meta else None
    raw_input_name = _normalize_tool_name(from_raw_input) if from_raw_input else None
    title_name = from_title
    if (from_meta and meta_name is None) or (from_raw_input and raw_input_name is None):
        return None
    if meta_name and title_name and meta_name != title_name:
        return None
    if raw_input_name and meta_name and raw_input_name != meta_name:
        return None
    if raw_input_name and title_name and raw_input_name != title_name:
        return None
    return meta_name or title_name or raw_input_name


def _extract_path_from_tool_title(
    tool_title: object,
    tool_name: str | None,
) -> str | None:
    if not isinstance(tool_title, str):
        return None
    separator = tool_title.find(":")
    if separator < 0:
        return None
    tail = tool_title[separator + 1 :].strip()
    if not tail:
        return None
    keyed_match = re.search(r"(?:^|,\s*)(?:path|file_path|filePath)\s*:\s*([^,]+)", tail)
    if keyed_match is not None:
        return keyed_match.group(1).strip()
    return tail if tool_name == "read" else None


def _resolve_tool_path_candidate(
    tool_call: Mapping[str, object] | None,
    tool_name: str | None,
    tool_title: object,
) -> str | None:
    raw_input = _as_mapping(tool_call.get("rawInput")) if tool_call is not None else None
    return _read_first_string_value(raw_input, ("path", "file_path", "filePath")) or (
        _extract_path_from_tool_title(tool_title, tool_name)
    )


def _resolve_absolute_scoped_path(value: str, cwd: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    if candidate.startswith("file://"):
        try:
            parsed = urlparse(candidate)
            candidate = unquote(parsed.path or "")
            if os.name == "nt" and re.match(r"^/[A-Za-z]:", candidate):
                candidate = candidate[1:]
        except ValueError:
            return None
    if candidate == "~" or candidate.startswith("~/"):
        candidate = os.path.expanduser(candidate)
    if not os.path.isabs(candidate):
        candidate = os.path.join(cwd, candidate)
    return os.path.abspath(os.path.normpath(candidate))


def _is_read_tool_call_scoped_to_cwd(
    tool_call: Mapping[str, object] | None,
    tool_name: str | None,
    tool_title: object,
    cwd: str,
) -> bool:
    if tool_name != "read":
        return False
    raw_path = _resolve_tool_path_candidate(tool_call, tool_name, tool_title)
    if raw_path is None:
        return False
    absolute_path = _resolve_absolute_scoped_path(raw_path, cwd)
    if absolute_path is None:
        return False
    root = os.path.normcase(os.path.abspath(os.path.normpath(cwd)))
    candidate = os.path.normcase(absolute_path)
    try:
        return os.path.commonpath([root, candidate]) == root
    except ValueError:
        return False


def _normalize_action_name(value: object) -> str | None:
    normalized = _optional_object_string(value)
    if normalized is None:
        return None
    action = re.sub(r"[\s-]+", "_", normalized.lower())
    return action or None


def _is_mutating_tool_call(tool_name: str, raw_input: object) -> bool:
    normalized = tool_name.strip().lower()
    record = _as_mapping(raw_input)
    action = _normalize_action_name(record.get("action")) if record is not None else None
    if normalized in {"write", "edit", "apply_patch", "exec", "bash", "sessions_send"}:
        return True
    if normalized == "process":
        return action is not None and action in _PROCESS_MUTATING_ACTIONS
    if normalized == "message":
        return (
            (action is not None and action in _MESSAGE_MUTATING_ACTIONS)
            or isinstance(record.get("content") if record else None, str)
            or isinstance(record.get("message") if record else None, str)
        )
    if normalized == "subagents":
        return action in {"kill", "steer"}
    if normalized == "session_status":
        model = record.get("model") if record is not None else None
        return isinstance(model, str) and bool(model.strip())
    if normalized in {"cron", "gateway", "canvas"}:
        return action is None or action not in _READ_ONLY_ACTIONS
    if normalized == "nodes":
        return action is None or action != "list"
    if normalized.endswith("_actions"):
        return action is None or action not in _READ_ONLY_ACTIONS
    if normalized.startswith("message_") or "send" in normalized:
        return True
    return False


def classify_acp_tool_approval(
    *,
    tool_call: Mapping[str, object] | None,
    cwd: str,
) -> AcpPermissionClassification:
    tool_name = _resolve_tool_name_for_permission(tool_call)
    if tool_name is None:
        return AcpPermissionClassification(None, "unknown", False)
    trusted = tool_name in _KNOWN_CORE_TOOL_IDS or tool_name in _TRUSTED_SAFE_TOOL_ALIASES
    if tool_name == "read" and trusted:
        auto_approve = _is_read_tool_call_scoped_to_cwd(
            tool_call,
            tool_name,
            tool_call.get("title") if tool_call else None,
            cwd,
        )
        return AcpPermissionClassification(
            tool_name,
            "readonly_scoped" if auto_approve else "other",
            auto_approve,
        )
    if tool_name in _SAFE_SEARCH_TOOL_IDS and trusted:
        return AcpPermissionClassification(tool_name, "readonly_search", True)
    owner_only_class = _OWNER_ONLY_TOOL_APPROVAL_CLASSES.get(tool_name)
    if owner_only_class is not None:
        return AcpPermissionClassification(tool_name, owner_only_class, False)
    if tool_name in _EXEC_CAPABLE_TOOL_IDS:
        return AcpPermissionClassification(tool_name, "exec_capable", False)
    if tool_name in _CONTROL_PLANE_TOOL_IDS:
        return AcpPermissionClassification(tool_name, "control_plane", False)
    raw_input = tool_call.get("rawInput") if tool_call else None
    if _is_mutating_tool_call(tool_name, raw_input):
        return AcpPermissionClassification(tool_name, "mutating", False)
    return AcpPermissionClassification(tool_name, "other", False)


def _resolve_tool_kind_for_permission(
    tool_name: str | None,
    approval_class: AcpApprovalClass,
) -> str | None:
    if tool_name is None and approval_class == "unknown":
        return None
    if approval_class in {"readonly_scoped", "readonly_search"}:
        return approval_class
    return approval_class


def _sanitize_terminal_text(input_text: str) -> str:
    normalized = (
        _ANSI_ESCAPE_RE.sub("", input_text)
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return "".join(
        char
        for char in normalized
        if not (0x00 <= ord(char) <= 0x1F or 0x7F <= ord(char) <= 0x9F)
    )


def _permission_options(params: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw_options = params.get("options")
    if not isinstance(raw_options, list):
        return []
    return [option for option in raw_options if isinstance(option, Mapping)]


def _pick_permission_option(
    options: Sequence[Mapping[str, object]],
    kinds: Sequence[str],
) -> Mapping[str, object] | None:
    for kind in kinds:
        for option in options:
            if option.get("kind") == kind:
                return option
    return None


def _selected_permission(option_id: object) -> dict[str, dict[str, object]]:
    return {"outcome": {"outcome": "selected", "optionId": str(option_id)}}


def _cancelled_permission() -> dict[str, dict[str, object]]:
    return {"outcome": {"outcome": "cancelled"}}


async def _default_permission_prompt(tool_name: str | None, _tool_title: str) -> bool:
    return False


async def _call_permission_prompt(
    prompt: AcpPermissionPrompt,
    tool_name: str | None,
    tool_title: str,
) -> bool:
    result = prompt(tool_name, tool_title)
    if inspect.isawaitable(result):
        result = await result
    return bool(result)


async def resolve_acp_permission_request(
    params: Mapping[str, object],
    *,
    prompt: AcpPermissionPrompt | None = None,
    log: AcpPermissionLogger | None = None,
    cwd: str | None = None,
) -> dict[str, dict[str, object]]:
    logger = log or (lambda _line: None)
    permission_prompt = prompt or _default_permission_prompt
    resolved_cwd = cwd or os.getcwd()
    options = _permission_options(params)
    tool_call = _as_mapping(params.get("toolCall"))
    raw_title = tool_call.get("title") if tool_call else None
    tool_title = _sanitize_terminal_text(raw_title if isinstance(raw_title, str) else "tool")
    classification = classify_acp_tool_approval(tool_call=tool_call, cwd=resolved_cwd)
    tool_name = classification.tool_name
    tool_kind = _resolve_tool_kind_for_permission(tool_name, classification.approval_class)

    if not options:
        logger(f"[permission cancelled] {tool_name or 'unknown'}: no options available")
        return _cancelled_permission()

    allow_option = _pick_permission_option(options, ("allow_once", "allow_always"))
    reject_option = _pick_permission_option(options, ("reject_once", "reject_always"))
    if classification.auto_approve:
        option = allow_option or options[0]
        option_id = option.get("optionId")
        if option_id is None:
            logger(f"[permission cancelled] {tool_name or 'unknown'}: no selectable options")
            return _cancelled_permission()
        logger(f"[permission auto-approved] {tool_name} ({tool_kind or 'unknown'})")
        return _selected_permission(option_id)

    detail = f"\n[permission requested] {tool_title}"
    if tool_name is not None:
        detail += f" ({tool_name})"
    if tool_kind is not None:
        detail += f" [{tool_kind}]"
    logger(detail)
    approved = await _call_permission_prompt(permission_prompt, tool_name, tool_title)
    if approved and allow_option is not None:
        return _selected_permission(allow_option.get("optionId"))
    if not approved and reject_option is not None:
        return _selected_permission(reject_option.get("optionId"))
    logger(
        "[permission cancelled] "
        f"{tool_name or 'unknown'}: missing {'allow' if approved else 'reject'} option"
    )
    return _cancelled_permission()


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
