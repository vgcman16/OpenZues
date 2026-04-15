from __future__ import annotations

import re
from pathlib import Path

import pytest

from openzues.services.device_bootstrap_profile import (
    BOOTSTRAP_HANDOFF_OPERATOR_SCOPES,
    default_device_bootstrap_profile,
    normalize_device_bootstrap_profile,
    resolve_bootstrap_profile_scopes_for_role,
)

_OPENCLAW_MAIN_ROOT = Path(__file__).resolve().parents[2] / "openclaw-main"
_BOOTSTRAP_OPERATOR_SCOPES_PATTERN = re.compile(
    r"export const BOOTSTRAP_HANDOFF_OPERATOR_SCOPES = \[(.*?)\] as const;",
    re.DOTALL,
)
_PAIRING_BOOTSTRAP_PROFILE_PATTERN = re.compile(
    r"export const PAIRING_SETUP_BOOTSTRAP_PROFILE: DeviceBootstrapProfile = \{\s*"
    r'roles: \[(.*?)\],\s*scopes: \[\.\.\.BOOTSTRAP_HANDOFF_OPERATOR_SCOPES\],\s*\};',
    re.DOTALL,
)


def _read_openclaw_bootstrap_profile_source() -> str:
    source_path = _OPENCLAW_MAIN_ROOT / "src" / "shared" / "device-bootstrap-profile.ts"
    if not source_path.exists():
        pytest.skip(f"OpenClaw source file is unavailable: {source_path}")
    return source_path.read_text(encoding="utf-8")


def _extract_openclaw_operator_scopes() -> list[str]:
    source_text = _read_openclaw_bootstrap_profile_source()
    match = _BOOTSTRAP_OPERATOR_SCOPES_PATTERN.search(source_text)
    if match is None:
        pytest.fail("Could not parse OpenClaw bootstrap operator scopes.")
    return re.findall(r'"([^"]+)"', match.group(1))


def _extract_openclaw_pairing_roles() -> list[str]:
    source_text = _read_openclaw_bootstrap_profile_source()
    match = _PAIRING_BOOTSTRAP_PROFILE_PATTERN.search(source_text)
    if match is None:
        pytest.fail("Could not parse OpenClaw pairing bootstrap roles.")
    return re.findall(r'"([^"]+)"', match.group(1))


def test_resolve_bootstrap_profile_scopes_for_role_bounds_operator_handoff() -> None:
    openclaw_handoff_scopes = _extract_openclaw_operator_scopes()
    assert resolve_bootstrap_profile_scopes_for_role(
        "operator",
        [
            "node.exec",
            "operator.admin",
            "operator.approvals",
            "operator.pairing",
            "operator.read",
            "operator.write",
        ],
    ) == [scope for scope in openclaw_handoff_scopes if scope != "operator.talk.secrets"]
    assert resolve_bootstrap_profile_scopes_for_role(
        "node",
        ["node.exec", "operator.approvals"],
    ) == []


def test_default_device_bootstrap_profile_matches_openclaw_pairing_profile() -> None:
    roles, scopes = default_device_bootstrap_profile()
    assert roles == _extract_openclaw_pairing_roles()
    assert scopes == _extract_openclaw_operator_scopes()
    assert scopes == list(BOOTSTRAP_HANDOFF_OPERATOR_SCOPES)


def test_normalize_device_bootstrap_profile_matches_openclaw_normalization_rules() -> None:
    roles, scopes = normalize_device_bootstrap_profile(None, None)
    assert roles == []
    assert scopes == []

    roles, scopes = normalize_device_bootstrap_profile(
        [" operator ", "node", "", "operator"],
        [" operator.write ", "operator.admin", "", "operator.approvals"],
    )
    assert roles == ["node", "operator"]
    assert scopes == [
        "operator.admin",
        "operator.approvals",
        "operator.read",
        "operator.write",
    ]
