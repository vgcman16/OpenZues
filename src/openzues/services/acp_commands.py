from __future__ import annotations

from collections.abc import Iterable, Mapping

BASE_AVAILABLE_COMMANDS: tuple[dict[str, object], ...] = (
    {"name": "help", "description": "Show help and common commands."},
    {"name": "commands", "description": "List available commands."},
    {"name": "status", "description": "Show current status."},
    {
        "name": "context",
        "description": "Explain context usage (list|detail|json).",
        "input": {"hint": "list | detail | json"},
    },
    {"name": "whoami", "description": "Show sender id (alias: /id)."},
    {"name": "id", "description": "Alias for /whoami."},
    {"name": "subagents", "description": "List or manage sub-agents."},
    {"name": "config", "description": "Read or write config (owner-only)."},
    {"name": "debug", "description": "Set runtime-only overrides (owner-only)."},
    {"name": "usage", "description": "Toggle usage footer (off|tokens|full)."},
    {"name": "stop", "description": "Stop the current run."},
    {"name": "restart", "description": "Restart the gateway (if enabled)."},
    {"name": "activation", "description": "Set group activation (mention|always)."},
    {"name": "send", "description": "Set send mode (on|off|inherit)."},
    {"name": "reset", "description": "Reset the session (/new)."},
    {"name": "new", "description": "Reset the session (/reset)."},
    {
        "name": "think",
        "description": "Set thinking level (off|minimal|low|medium|high|xhigh).",
    },
    {"name": "verbose", "description": "Set verbose mode (on|full|off)."},
    {"name": "trace", "description": "Set plugin trace mode (on|off)."},
    {"name": "reasoning", "description": "Toggle reasoning output (on|off|stream)."},
    {"name": "elevated", "description": "Toggle elevated mode (on|off)."},
    {"name": "model", "description": "Select a model (list|status|<name>)."},
    {"name": "queue", "description": "Adjust queue mode and options."},
    {"name": "bash", "description": "Run a host command (if enabled)."},
    {"name": "compact", "description": "Compact the session history."},
)


def _normalize_extra_command(command: Mapping[str, object]) -> dict[str, object] | None:
    raw_name = command.get("name") or command.get("key")
    if not isinstance(raw_name, str):
        return None
    name = raw_name.strip().lstrip("/")
    if not name:
        return None
    description = command.get("description")
    normalized: dict[str, object] = {
        "name": name,
        "description": description if isinstance(description, str) else "",
    }
    input_value = command.get("input")
    if isinstance(input_value, Mapping):
        normalized["input"] = dict(input_value)
    return normalized


def get_available_commands(
    *,
    extra_commands: Iterable[Mapping[str, object]] = (),
) -> list[dict[str, object]]:
    commands = [dict(command) for command in BASE_AVAILABLE_COMMANDS]
    for command in extra_commands:
        normalized = _normalize_extra_command(command)
        if normalized is not None:
            commands.append(normalized)
    return commands
