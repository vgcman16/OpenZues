from __future__ import annotations

from collections.abc import Iterable

BOOTSTRAP_HANDOFF_OPERATOR_SCOPES = (
    "operator.approvals",
    "operator.read",
    "operator.talk.secrets",
    "operator.write",
)

_BOOTSTRAP_HANDOFF_OPERATOR_SCOPE_SET = set(BOOTSTRAP_HANDOFF_OPERATOR_SCOPES)
_PAIRING_SETUP_BOOTSTRAP_ROLES = ("node", "operator")


def normalize_device_auth_role(role: str | None) -> str:
    return str(role or "").strip()


def normalize_device_auth_scopes(scopes: Iterable[str] | None) -> list[str]:
    if scopes is None:
        return []
    out: set[str] = set()
    for scope in scopes:
        trimmed = str(scope).strip()
        if trimmed:
            out.add(trimmed)
    if "operator.admin" in out:
        out.add("operator.read")
        out.add("operator.write")
    elif "operator.write" in out:
        out.add("operator.read")
    return sorted(out)


def resolve_bootstrap_profile_scopes_for_role(
    role: str,
    scopes: Iterable[str],
) -> list[str]:
    normalized_role = normalize_device_auth_role(role)
    normalized_scopes = normalize_device_auth_scopes(scopes)
    if normalized_role == "operator":
        return [
            scope
            for scope in normalized_scopes
            if scope in _BOOTSTRAP_HANDOFF_OPERATOR_SCOPE_SET
        ]
    return []


def normalize_device_bootstrap_roles(roles: Iterable[str] | None) -> list[str]:
    if roles is None:
        return []
    out: set[str] = set()
    for role in roles:
        normalized = normalize_device_auth_role(role)
        if normalized:
            out.add(normalized)
    return sorted(out)


def default_device_bootstrap_profile() -> tuple[list[str], list[str]]:
    return (list(_PAIRING_SETUP_BOOTSTRAP_ROLES), list(BOOTSTRAP_HANDOFF_OPERATOR_SCOPES))


def normalize_device_bootstrap_profile(
    roles: Iterable[str] | None,
    scopes: Iterable[str] | None,
) -> tuple[list[str], list[str]]:
    normalized_roles = normalize_device_bootstrap_roles(roles)
    normalized_scopes = normalize_device_auth_scopes(scopes)
    return normalized_roles, normalized_scopes
