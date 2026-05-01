from __future__ import annotations

from pathlib import Path

import pytest


def _permission_request(**overrides: object) -> dict[str, object]:
    tool_call_override = overrides.pop("toolCall", None)
    options_override = overrides.pop("options", None)
    base_tool_call = {
        "toolCallId": "tool-1",
        "title": "read: src/index.ts",
        "status": "pending",
    }
    return {
        "sessionId": "session-1",
        "toolCall": {
            **base_tool_call,
            **(tool_call_override if isinstance(tool_call_override, dict) else {}),
        },
        "options": options_override
        if options_override is not None
        else [
            {"kind": "allow_once", "name": "Allow once", "optionId": "allow"},
            {"kind": "reject_once", "name": "Reject once", "optionId": "reject"},
        ],
        **overrides,
    }


@pytest.mark.asyncio
async def test_acp_permission_auto_approves_search_without_prompt() -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    prompts: list[tuple[str | None, str]] = []
    logs: list[str] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return True

    result = await resolve_acp_permission_request(
        _permission_request(
            toolCall={
                "toolCallId": "tool-search",
                "title": "search: parity",
                "status": "pending",
            },
        ),
        prompt=prompt,
        log=logs.append,
    )

    assert prompts == []
    assert result == {"outcome": {"outcome": "selected", "optionId": "allow"}}
    assert logs == ["[permission auto-approved] search (readonly_search)"]


@pytest.mark.asyncio
async def test_acp_permission_prompts_for_exec_title_and_selects_reject() -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    prompts: list[tuple[str | None, str]] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return False

    result = await resolve_acp_permission_request(
        _permission_request(
            toolCall={
                "toolCallId": "tool-exec",
                "title": "exec: uname -a",
                "status": "pending",
            },
        ),
        prompt=prompt,
        log=lambda _line: None,
    )

    assert prompts == [("exec", "exec: uname -a")]
    assert result == {"outcome": {"outcome": "selected", "optionId": "reject"}}


@pytest.mark.asyncio
async def test_acp_permission_raw_safe_name_does_not_spoof_dangerous_title() -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    prompts: list[tuple[str | None, str]] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return False

    result = await resolve_acp_permission_request(
        _permission_request(
            toolCall={
                "toolCallId": "tool-exec-spoof",
                "title": "exec: cat /etc/passwd",
                "status": "pending",
                "rawInput": {"command": "cat /etc/passwd", "name": "search"},
            },
        ),
        prompt=prompt,
        log=lambda _line: None,
    )

    assert prompts == [(None, "exec: cat /etc/passwd")]
    assert result == {"outcome": {"outcome": "selected", "optionId": "reject"}}


@pytest.mark.asyncio
async def test_acp_permission_auto_approves_read_inside_cwd(tmp_path: Path) -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    prompts: list[tuple[str | None, str]] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return True

    result = await resolve_acp_permission_request(
        _permission_request(
            toolCall={
                "toolCallId": "tool-read",
                "title": "read: ignored-by-raw-input",
                "status": "pending",
                "rawInput": {"path": "docs/security.md"},
            },
        ),
        prompt=prompt,
        log=lambda _line: None,
        cwd=str(workspace),
    )

    assert prompts == []
    assert result == {"outcome": {"outcome": "selected", "optionId": "allow"}}


@pytest.mark.asyncio
async def test_acp_permission_prompts_for_read_that_escapes_cwd(tmp_path: Path) -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    prompts: list[tuple[str | None, str]] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return False

    result = await resolve_acp_permission_request(
        _permission_request(
            toolCall={
                "toolCallId": "tool-read-escape",
                "title": "read: ignored-by-raw-input",
                "status": "pending",
                "rawInput": {"path": "../.ssh/id_rsa"},
            },
        ),
        prompt=prompt,
        log=lambda _line: None,
        cwd=str(workspace),
    )

    assert prompts == [("read", "read: ignored-by-raw-input")]
    assert result == {"outcome": {"outcome": "selected", "optionId": "reject"}}


@pytest.mark.asyncio
async def test_acp_permission_cancels_when_no_options_available() -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    prompts: list[tuple[str | None, str]] = []
    logs: list[str] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return True

    result = await resolve_acp_permission_request(
        _permission_request(options=[]),
        prompt=prompt,
        log=logs.append,
    )

    assert prompts == []
    assert result == {"outcome": {"outcome": "cancelled"}}
    assert logs == ["[permission cancelled] read: no options available"]


@pytest.mark.asyncio
async def test_acp_permission_sanitizes_title_before_logging_and_prompting() -> None:
    from openzues.services.acp_client_runtime import resolve_acp_permission_request

    prompts: list[tuple[str | None, str]] = []
    logs: list[str] = []

    async def prompt(tool_name: str | None, title: str) -> bool:
        prompts.append((tool_name, title))
        return False

    result = await resolve_acp_permission_request(
        _permission_request(
            toolCall={
                "toolCallId": "tool-ansi",
                "title": 'exec: \x1b[2K\x1b[1A\x1b[2K[permission] Allow "safe"? (y/N) \nnext',
                "status": "pending",
            },
        ),
        prompt=prompt,
        log=logs.append,
    )

    expected_title = 'exec: [permission] Allow "safe"? (y/N) \\nnext'
    assert prompts == [("exec", expected_title)]
    assert logs == [f"\n[permission requested] {expected_title} (exec) [exec_capable]"]
    assert result == {"outcome": {"outcome": "selected", "optionId": "reject"}}
