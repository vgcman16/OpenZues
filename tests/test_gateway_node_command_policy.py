from openzues.services.gateway_node_command_policy import (
    normalize_declared_node_commands,
    resolve_node_command_allowlist,
)


def test_macos_allowlist_includes_screen_snapshot_but_not_screen_record() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="macOS 26.3.1",
        device_family="Mac",
    )

    assert "screen.snapshot" in allowlist
    assert "screen.record" not in allowlist


def test_windows_allowlist_matches_openclaw_companion_defaults() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="Windows 11",
        device_family="Windows PC",
    )

    assert "canvas.present" in allowlist
    assert "camera.list" in allowlist
    assert "location.get" in allowlist
    assert "device.info" in allowlist
    assert "device.status" in allowlist
    assert "system.run" in allowlist
    assert "screen.snapshot" in allowlist
    assert "screen.record" not in allowlist


def test_ios_allowlist_includes_openclaw_screen_record_default() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="iOS 18",
        device_family="iPhone",
    )

    assert "screen.record" in allowlist
    assert normalize_declared_node_commands(
        ("screen.record",),
        allowlist=allowlist,
    ) == ("screen.record",)


def test_explicit_allow_commands_can_enable_screen_record() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="ios",
        device_family="iPhone",
        allow_commands=("screen.record",),
    )

    assert "screen.record" in allowlist
