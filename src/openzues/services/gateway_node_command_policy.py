from __future__ import annotations

from collections.abc import Iterable

_CANVAS_COMMANDS = (
    "canvas.present",
    "canvas.hide",
    "canvas.navigate",
    "canvas.eval",
    "canvas.snapshot",
    "canvas.a2ui.push",
    "canvas.a2ui.pushJSONL",
    "canvas.a2ui.reset",
)
_CAMERA_COMMANDS = ("camera.list",)
_IOS_CAMERA_COMMANDS = (*_CAMERA_COMMANDS, "camera.snap", "camera.clip")
_ANDROID_CAMERA_COMMANDS = _IOS_CAMERA_COMMANDS
_MACOS_CAMERA_COMMANDS = _IOS_CAMERA_COMMANDS
_LOCATION_COMMANDS = ("location.get",)
_NOTIFICATION_COMMANDS = ("notifications.list",)
_ANDROID_NOTIFICATION_COMMANDS = (*_NOTIFICATION_COMMANDS, "notifications.actions")
_DEVICE_COMMANDS = ("device.info", "device.status")
_ANDROID_DEVICE_COMMANDS = (*_DEVICE_COMMANDS, "device.permissions", "device.health")
_CONTACTS_COMMANDS = ("contacts.search",)
_IOS_CONTACTS_COMMANDS = (*_CONTACTS_COMMANDS, "contacts.add")
_ANDROID_CONTACTS_COMMANDS = _IOS_CONTACTS_COMMANDS
_CALENDAR_COMMANDS = ("calendar.events",)
_IOS_CALENDAR_COMMANDS = (*_CALENDAR_COMMANDS, "calendar.add")
_ANDROID_CALENDAR_COMMANDS = _IOS_CALENDAR_COMMANDS
_CALL_LOG_COMMANDS = ("callLog.search",)
_SMS_COMMANDS = ("sms.send", "sms.search")
_REMINDERS_COMMANDS = ("reminders.list",)
_IOS_REMINDERS_COMMANDS = (*_REMINDERS_COMMANDS, "reminders.add")
_PHOTOS_COMMANDS = ("photos.latest",)
_MOTION_COMMANDS = ("motion.activity", "motion.pedometer")
_CHAT_COMMANDS = ("chat.push",)
_IOS_TALK_COMMANDS = (
    "talk.ptt.start",
    "talk.ptt.stop",
    "talk.ptt.cancel",
    "talk.ptt.once",
)
_IOS_WATCH_COMMANDS = ("watch.status", "watch.notify")
_SCREEN_COMMANDS = ("screen.snapshot",)
_IOS_SCREEN_COMMANDS = ("screen.record",)
_IOS_SYSTEM_COMMANDS = ("system.notify",)
_SYSTEM_COMMANDS = (
    "system.run.prepare",
    "system.run",
    "system.which",
    "system.notify",
    "browser.proxy",
)
_MACOS_SYSTEM_COMMANDS = (
    *_SYSTEM_COMMANDS,
    "system.execApprovals.get",
    "system.execApprovals.set",
)
_UNKNOWN_PLATFORM_COMMANDS = (
    *_CANVAS_COMMANDS,
    *_CAMERA_COMMANDS,
    *_LOCATION_COMMANDS,
    "system.notify",
)

_PLATFORM_DEFAULTS: dict[str, tuple[str, ...]] = {
    "ios": (
        *_CANVAS_COMMANDS,
        *_IOS_CAMERA_COMMANDS,
        *_LOCATION_COMMANDS,
        *_DEVICE_COMMANDS,
        *_IOS_CONTACTS_COMMANDS,
        *_IOS_CALENDAR_COMMANDS,
        *_IOS_REMINDERS_COMMANDS,
        *_PHOTOS_COMMANDS,
        *_MOTION_COMMANDS,
        *_CHAT_COMMANDS,
        *_IOS_TALK_COMMANDS,
        *_IOS_WATCH_COMMANDS,
        *_IOS_SCREEN_COMMANDS,
        *_IOS_SYSTEM_COMMANDS,
    ),
    "android": (
        *_CANVAS_COMMANDS,
        *_ANDROID_CAMERA_COMMANDS,
        *_LOCATION_COMMANDS,
        *_ANDROID_NOTIFICATION_COMMANDS,
        "system.notify",
        *_ANDROID_DEVICE_COMMANDS,
        *_ANDROID_CONTACTS_COMMANDS,
        *_ANDROID_CALENDAR_COMMANDS,
        *_CALL_LOG_COMMANDS,
        *_SMS_COMMANDS,
        *_REMINDERS_COMMANDS,
        *_PHOTOS_COMMANDS,
        *_MOTION_COMMANDS,
    ),
    "macos": (
        *_CANVAS_COMMANDS,
        *_MACOS_CAMERA_COMMANDS,
        *_LOCATION_COMMANDS,
        *_DEVICE_COMMANDS,
        *_CONTACTS_COMMANDS,
        *_CALENDAR_COMMANDS,
        *_REMINDERS_COMMANDS,
        *_PHOTOS_COMMANDS,
        *_MOTION_COMMANDS,
        *_MACOS_SYSTEM_COMMANDS,
        *_SCREEN_COMMANDS,
    ),
    "desktop": _SYSTEM_COMMANDS,
    "linux": _SYSTEM_COMMANDS,
    "windows": (
        *_CANVAS_COMMANDS,
        *_CAMERA_COMMANDS,
        *_LOCATION_COMMANDS,
        *_DEVICE_COMMANDS,
        *_SYSTEM_COMMANDS,
        *_SCREEN_COMMANDS,
    ),
    "unknown": _UNKNOWN_PLATFORM_COMMANDS,
}

_PLATFORM_PREFIX_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ios", ("ios",)),
    ("android", ("android",)),
    ("macos", ("mac", "darwin")),
    ("desktop", ("desktop",)),
    ("windows", ("win",)),
    ("linux", ("linux",)),
)

_DEVICE_FAMILY_TOKEN_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ios", ("iphone", "ipad", "ios")),
    ("android", ("android",)),
    ("macos", ("mac",)),
    ("windows", ("windows",)),
    ("linux", ("linux",)),
)


def _normalize_device_metadata(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def resolve_node_platform_id(platform: str | None, device_family: str | None = None) -> str:
    raw_platform = _normalize_device_metadata(platform)
    for platform_id, prefixes in _PLATFORM_PREFIX_RULES:
        if any(raw_platform.startswith(prefix) for prefix in prefixes):
            return platform_id

    raw_family = _normalize_device_metadata(device_family)
    for platform_id, tokens in _DEVICE_FAMILY_TOKEN_RULES:
        if any(token in raw_family for token in tokens):
            return platform_id
    return "unknown"


def resolve_node_command_allowlist(
    *,
    platform: str | None,
    device_family: str | None = None,
    allow_commands: Iterable[str] = (),
    deny_commands: Iterable[str] = (),
) -> set[str]:
    platform_id = resolve_node_platform_id(platform, device_family)
    allowed = {
        command.strip()
        for command in _PLATFORM_DEFAULTS.get(platform_id, _PLATFORM_DEFAULTS["unknown"])
        if command.strip()
    }
    for command in allow_commands:
        trimmed = command.strip()
        if trimmed:
            allowed.add(trimmed)
    for command in deny_commands:
        trimmed = command.strip()
        if trimmed:
            allowed.discard(trimmed)
    return allowed


def normalize_declared_node_commands(
    declared_commands: Iterable[str] | None,
    *,
    allowlist: set[str],
) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for command in declared_commands or ():
        trimmed = command.strip()
        if not trimmed or trimmed in seen or trimmed not in allowlist:
            continue
        seen.add(trimmed)
        normalized.append(trimmed)
    return tuple(normalized)


def is_node_command_allowed(
    *,
    command: str,
    declared_commands: Iterable[str] | None,
    allowlist: set[str],
) -> tuple[bool, str | None]:
    trimmed = command.strip()
    if not trimmed:
        return False, "command required"
    if trimmed not in allowlist:
        return False, "command not allowlisted"
    normalized_declared = normalize_declared_node_commands(
        declared_commands,
        allowlist=allowlist,
    )
    if not normalized_declared:
        return False, "node did not declare commands"
    if trimmed not in normalized_declared:
        return False, "command not declared by node"
    return True, None
