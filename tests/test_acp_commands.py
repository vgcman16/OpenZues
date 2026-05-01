from __future__ import annotations


def test_acp_available_commands_match_openclaw_base_catalog() -> None:
    from openzues.services.acp_commands import get_available_commands

    commands = get_available_commands()

    assert [command["name"] for command in commands[:6]] == [
        "help",
        "commands",
        "status",
        "context",
        "whoami",
        "id",
    ]
    assert {"name": "reset", "description": "Reset the session (/new)."} in commands
    assert {"name": "new", "description": "Reset the session (/reset)."} in commands
    assert {
        "name": "context",
        "description": "Explain context usage (list|detail|json).",
        "input": {"hint": "list | detail | json"},
    } in commands
    assert commands[-1] == {"name": "compact", "description": "Compact the session history."}


def test_acp_available_commands_appends_fakeable_extra_commands() -> None:
    from openzues.services.acp_commands import get_available_commands

    commands = get_available_commands(
        extra_commands=[
            {"name": "/dock", "description": "Open dock controls."},
            {"key": "dock:status", "description": "Dock status."},
        ]
    )

    assert commands[-2:] == [
        {"name": "dock", "description": "Open dock controls."},
        {"name": "dock:status", "description": "Dock status."},
    ]
