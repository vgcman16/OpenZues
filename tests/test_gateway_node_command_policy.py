from openzues.services.gateway_node_command_policy import resolve_node_command_allowlist


def test_macos_allowlist_includes_screen_snapshot_but_not_screen_record() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="macOS 26.3.1",
        device_family="Mac",
    )

    assert "screen.snapshot" in allowlist
    assert "screen.record" not in allowlist


def test_explicit_allow_commands_can_enable_screen_record() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="ios",
        device_family="iPhone",
        allow_commands=("screen.record",),
    )

    assert "screen.record" in allowlist
