from openzues.services.gateway_node_command_policy import (
    normalize_declared_node_commands,
    resolve_node_command_allowlist,
)


def test_macos_allowlist_matches_openclaw_screen_defaults() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="macOS 26.3.1",
        device_family="Mac",
    )

    declared = ("screen.snapshot", "screen.record")

    assert "screen.snapshot" in allowlist
    assert "screen.record" not in allowlist
    assert normalize_declared_node_commands(
        declared,
        allowlist=allowlist,
    ) == ("screen.snapshot",)


def test_macos_allowlist_keeps_openclaw_exec_approval_commands_gated() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="macOS 26.3.1",
        device_family="Mac",
    )

    declared = (
        "system.execApprovals.get",
        "system.execApprovals.set",
    )

    for command in declared:
        assert command not in allowlist
    assert normalize_declared_node_commands(
        declared,
        allowlist=allowlist,
    ) == ()


def test_macos_allowlist_keeps_openclaw_camera_actions_gated() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="macOS 26.3.1",
        device_family="MacBook Pro",
    )

    declared = ("camera.list", "camera.snap", "camera.clip")

    assert "camera.list" in allowlist
    assert "camera.snap" not in allowlist
    assert "camera.clip" not in allowlist
    assert normalize_declared_node_commands(
        declared,
        allowlist=allowlist,
    ) == ("camera.list",)


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


def test_android_allowlist_matches_openclaw_diagnostics_defaults_and_gates_actions() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="Android 16",
        device_family="Android phone",
    )

    assert "notifications.actions" in allowlist
    assert "device.permissions" in allowlist
    assert "device.health" in allowlist
    assert "callLog.search" in allowlist
    assert "system.notify" in allowlist
    assert "camera.snap" not in allowlist
    assert "camera.clip" not in allowlist
    assert "contacts.add" not in allowlist
    assert "calendar.add" not in allowlist
    assert "sms.send" not in allowlist
    assert "sms.search" not in allowlist
    assert normalize_declared_node_commands(
        ("notifications.actions", "sms.search"),
        allowlist=allowlist,
    ) == ("notifications.actions",)


def test_ios_allowlist_matches_openclaw_service_defaults_and_gates_actions() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="iOS 18",
        device_family="iPhone",
    )

    assert "device.info" in allowlist
    assert "device.status" in allowlist
    assert "system.notify" in allowlist
    assert "contacts.search" in allowlist
    assert "calendar.events" in allowlist
    assert "reminders.list" in allowlist
    assert "photos.latest" in allowlist
    assert "motion.activity" in allowlist
    assert "screen.record" not in allowlist
    assert "camera.snap" not in allowlist
    assert "camera.clip" not in allowlist
    assert "contacts.add" not in allowlist
    assert "calendar.add" not in allowlist
    assert "reminders.add" not in allowlist
    assert "chat.push" not in allowlist
    assert "talk.ptt.start" not in allowlist
    assert "watch.status" not in allowlist
    assert normalize_declared_node_commands(
        ("device.info", "screen.record", "chat.push"),
        allowlist=allowlist,
    ) == ("device.info",)


def test_explicit_allow_commands_can_enable_screen_record() -> None:
    allowlist = resolve_node_command_allowlist(
        platform="ios",
        device_family="iPhone",
        allow_commands=("screen.record", "camera.snap", "chat.push"),
    )

    assert "screen.record" in allowlist
    assert "camera.snap" in allowlist
    assert "chat.push" in allowlist
