from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any, Iterable

MEMPALACE_DEFAULT_NAME = "MemPalace"
MEMPALACE_DEFAULT_KIND = "mempalace"
MEMPALACE_DEFAULT_BASE_URL = "python -m mempalace.mcp_server"
MEMPALACE_DEFAULT_AUTH_SCHEME = "none"
MEMPALACE_DEFAULT_NOTES = (
    "Local MCP memory recall. Query it before answering historical questions, and write back "
    "durable context after meaningful sessions."
)
MEMPALACE_MEMORY_TASK_NAME = "MemPalace Memory Loop"
MEMPALACE_MEMORY_TASK_SUMMARY = (
    "Refresh durable project memory through MemPalace without defaulting to lossy compression."
)
MEMPALACE_MEMORY_TASK_MARKER = "MemPalace automatic maintenance contract:"
MEMPALACE_DIRECT_PROOF_MISSION_NAME = "MemPalace Direct Proof"
MEMPALACE_DIRECT_PROOF_MARKER = "MemPalace control-plane proof contract:"
MEMPALACE_STATUS_TOOL = "mempalace_status"
MEMPALACE_SEARCH_TOOL = "mempalace_search"
MEMPALACE_DIARY_WRITE_TOOL = "mempalace_diary_write"
MEMPALACE_DIARY_READ_TOOL = "mempalace_diary_read"
MEMPALACE_REQUIRED_TOOLS = (
    MEMPALACE_STATUS_TOOL,
    MEMPALACE_SEARCH_TOOL,
    MEMPALACE_DIARY_WRITE_TOOL,
)
MEMPALACE_OPTIONAL_TOOLS = (MEMPALACE_DIARY_READ_TOOL,)
MEMPALACE_WRITEBACK_STATUS_PREFIX = "Writeback status:"
MEMPALACE_WRITEBACK_AT_PREFIX = "Writeback at:"
MEMPALACE_WRITEBACK_SCOPE_PREFIX = "Writeback scope:"
MEMPALACE_WRITEBACK_STATUS_WROTE = "wrote"
MEMPALACE_WRITEBACK_STATUS_CORRECTED = "corrected"
MEMPALACE_WRITEBACK_STATUS_DEFERRED = "deferred"
MEMPALACE_WRITEBACK_STATUS_UNAVAILABLE = "unavailable"
MEMPALACE_WRITEBACK_STATUS_NONE = "none"
MEMPALACE_SUCCESSFUL_WRITEBACK_STATUSES = (
    MEMPALACE_WRITEBACK_STATUS_WROTE,
    MEMPALACE_WRITEBACK_STATUS_CORRECTED,
)
MEMPALACE_ROUNDTRIP_STATUS_PREFIX = "Roundtrip status:"
MEMPALACE_ROUNDTRIP_AT_PREFIX = "Roundtrip at:"
MEMPALACE_ROUNDTRIP_SCOPE_PREFIX = "Roundtrip scope:"
MEMPALACE_ROUNDTRIP_DETAIL_PREFIX = "Roundtrip detail:"
MEMPALACE_ROUNDTRIP_STATUS_VERIFIED = "verified"
MEMPALACE_ROUNDTRIP_STATUS_FAILED = "failed"
MEMPALACE_ROUNDTRIP_STATUS_DEFERRED = "deferred"
MEMPALACE_ROUNDTRIP_STATUS_UNAVAILABLE = "unavailable"
MEMPALACE_ROUNDTRIP_STATUS_NONE = "none"
MEMPALACE_SUCCESSFUL_ROUNDTRIP_STATUSES = (MEMPALACE_ROUNDTRIP_STATUS_VERIFIED,)
MEMPALACE_CONTROL_PLANE_PROOF_STATUS_PREFIX = "Control-plane proof status:"
MEMPALACE_CONTROL_PLANE_PROOF_AT_PREFIX = "Control-plane proof at:"
MEMPALACE_CONTROL_PLANE_PROOF_SCOPE_PREFIX = "Control-plane proof scope:"
MEMPALACE_CONTROL_PLANE_PROOF_DETAIL_PREFIX = "Control-plane proof detail:"
MEMPALACE_CONTROL_PLANE_PROOF_STATUS_VERIFIED = "verified"
MEMPALACE_CONTROL_PLANE_PROOF_STATUS_FAILED = "failed"
MEMPALACE_CONTROL_PLANE_PROOF_STATUS_UNAVAILABLE = "unavailable"
MEMPALACE_CONTROL_PLANE_PROOF_STATUS_NONE = "none"
MEMPALACE_SUCCESSFUL_CONTROL_PLANE_PROOF_STATUSES = (
    MEMPALACE_CONTROL_PLANE_PROOF_STATUS_VERIFIED,
)
MEMPALACE_WRITEBACK_ACTION = (
    "Review the checkpoint, then write durable decisions, recovered history, and the next-start "
    "handoff back through MemPalace before you resume or stop."
)
WRITEBACK_LINE_RE = re.compile(r"^(?P<label>Writeback (?:status|at|scope)):\s*(?P<value>.+?)\s*$", re.IGNORECASE)
ROUNDTRIP_LINE_RE = re.compile(
    r"^(?P<label>Roundtrip (?:status|at|scope|detail)):\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
CONTROL_PLANE_PROOF_LINE_RE = re.compile(
    r"^(?P<label>Control-plane proof (?:status|at|scope|detail)):\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)


def _integration_value(integration: Any, field: str) -> Any:
    if isinstance(integration, dict):
        return integration.get(field)
    return getattr(integration, field, None)


def is_mempalace_integration(integration: Any) -> bool:
    name = str(_integration_value(integration, "name") or "").strip().lower()
    kind = str(_integration_value(integration, "kind") or "").strip().lower()
    base_url = str(_integration_value(integration, "base_url") or "").strip().lower()
    notes = str(_integration_value(integration, "notes") or "").strip().lower()
    haystacks = (name, kind, base_url, notes)
    return any("mempalace" in value for value in haystacks if value)


def mempalace_bootstrap_defaults() -> dict[str, str]:
    return {
        "integration_name": MEMPALACE_DEFAULT_NAME,
        "integration_kind": MEMPALACE_DEFAULT_KIND,
        "integration_base_url": MEMPALACE_DEFAULT_BASE_URL,
        "integration_auth_scheme": MEMPALACE_DEFAULT_AUTH_SCHEME,
        "integration_notes": MEMPALACE_DEFAULT_NOTES,
    }


def has_mempalace_integration(
    integrations: Iterable[Any],
    *,
    project_id: int | None = None,
) -> bool:
    for integration in integrations:
        if not is_mempalace_integration(integration):
            continue
        enabled = _integration_value(integration, "enabled")
        if enabled is False:
            continue
        integration_project_id = _integration_value(integration, "project_id")
        if integration_project_id is None or integration_project_id == project_id:
            return True
    return False


def mempalace_maintenance_cadence_minutes(primary_cadence_minutes: int | None) -> int:
    baseline = primary_cadence_minutes or 180
    return max(360, min(baseline * 4, 720))


def build_mempalace_writeback_signal(
    *,
    status: str,
    at: str | None,
    scope: str | None,
) -> str:
    return "\n".join(
        [
            f"{MEMPALACE_WRITEBACK_STATUS_PREFIX} {status}",
            f"{MEMPALACE_WRITEBACK_AT_PREFIX} {at or 'n/a'}",
            f"{MEMPALACE_WRITEBACK_SCOPE_PREFIX} {scope or 'n/a'}",
        ]
    )


def build_mempalace_roundtrip_signal(
    *,
    status: str,
    at: str | None,
    scope: str | None,
    detail: str | None,
) -> str:
    return "\n".join(
        [
            f"{MEMPALACE_ROUNDTRIP_STATUS_PREFIX} {status}",
            f"{MEMPALACE_ROUNDTRIP_AT_PREFIX} {at or 'n/a'}",
            f"{MEMPALACE_ROUNDTRIP_SCOPE_PREFIX} {scope or 'n/a'}",
            f"{MEMPALACE_ROUNDTRIP_DETAIL_PREFIX} {detail or 'n/a'}",
        ]
    )


def build_mempalace_control_plane_proof_signal(
    *,
    status: str,
    at: str | None,
    scope: str | None,
    detail: str | None,
) -> str:
    return "\n".join(
        [
            f"{MEMPALACE_CONTROL_PLANE_PROOF_STATUS_PREFIX} {status}",
            f"{MEMPALACE_CONTROL_PLANE_PROOF_AT_PREFIX} {at or 'n/a'}",
            f"{MEMPALACE_CONTROL_PLANE_PROOF_SCOPE_PREFIX} {scope or 'n/a'}",
            f"{MEMPALACE_CONTROL_PLANE_PROOF_DETAIL_PREFIX} {detail or 'n/a'}",
        ]
    )


def _parse_signal_values(
    text: str | None,
    *,
    pattern: re.Pattern[str],
) -> dict[str, str]:
    if not text:
        return {}
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = pattern.match(raw_line.strip())
        if not match:
            continue
        label = match.group("label").strip().lower()
        value = match.group("value").strip()
        values[label] = value
    return values


def parse_mempalace_writeback_signal(text: str | None) -> dict[str, Any] | None:
    values = _parse_signal_values(text, pattern=WRITEBACK_LINE_RE)
    if not values:
        return None

    status = values.get("writeback status", "").strip().lower()
    at_text = values.get("writeback at", "").strip()
    scope = values.get("writeback scope", "").strip() or None
    at = None
    if at_text and at_text.lower() not in {"n/a", "na", "none", "unknown"}:
        try:
            at = datetime.fromisoformat(at_text.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            at = None
    return {
        "status": status,
        "at": at,
        "at_text": at_text,
        "scope": scope,
        "successful": status in MEMPALACE_SUCCESSFUL_WRITEBACK_STATUSES and at is not None,
    }


def parse_mempalace_roundtrip_signal(text: str | None) -> dict[str, Any] | None:
    values = _parse_signal_values(text, pattern=ROUNDTRIP_LINE_RE)
    if not values:
        return None

    status = values.get("roundtrip status", "").strip().lower()
    at_text = values.get("roundtrip at", "").strip()
    scope = values.get("roundtrip scope", "").strip() or None
    detail = values.get("roundtrip detail", "").strip() or None
    if detail and detail.lower() in {"n/a", "na", "none", "unknown"}:
        detail = None
    at = None
    if at_text and at_text.lower() not in {"n/a", "na", "none", "unknown"}:
        try:
            at = datetime.fromisoformat(at_text.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            at = None
    return {
        "status": status,
        "at": at,
        "at_text": at_text,
        "scope": scope,
        "detail": detail,
        "successful": status in MEMPALACE_SUCCESSFUL_ROUNDTRIP_STATUSES and at is not None,
    }


def parse_mempalace_control_plane_proof_signal(text: str | None) -> dict[str, Any] | None:
    values = _parse_signal_values(text, pattern=CONTROL_PLANE_PROOF_LINE_RE)
    if not values:
        return None

    status = values.get("control-plane proof status", "").strip().lower()
    at_text = values.get("control-plane proof at", "").strip()
    scope = values.get("control-plane proof scope", "").strip() or None
    detail = values.get("control-plane proof detail", "").strip() or None
    if detail and detail.lower() in {"n/a", "na", "none", "unknown"}:
        detail = None
    at = None
    if at_text and at_text.lower() not in {"n/a", "na", "none", "unknown"}:
        try:
            at = datetime.fromisoformat(at_text.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError:
            at = None
    return {
        "status": status,
        "at": at,
        "at_text": at_text,
        "scope": scope,
        "detail": detail,
        "successful": status in MEMPALACE_SUCCESSFUL_CONTROL_PLANE_PROOF_STATUSES and at is not None,
    }


def build_mempalace_maintenance_objective(
    *,
    project_label: str | None,
    project_path: str | None,
) -> str:
    label = str(project_label or "Current workspace").strip() or "Current workspace"
    path = str(project_path or "current workspace").strip() or "current workspace"
    return "\n".join(
        [
            "# MemPalace Memory Maintenance",
            "",
            f"Project: {label}",
            f"Workspace: {path}",
            "",
            "Maintain durable project memory for this workspace using the existing MemPalace integration.",
            "",
            MEMPALACE_MEMORY_TASK_MARKER,
            "- Start by confirming whether MemPalace tools are actually available on this lane.",
            "- If the lane exposes MemPalace status or search tools, use them before relying on "
            "thread memory for historical claims.",
            "- Review the strongest recent local signal before writing anything new: latest "
            "checkpoint docs, mission handoffs, and meaningful repo changes.",
            "- Preserve only stable truths future missions will need: accepted decisions, live "
            "constraints, active launch rules, drift signatures, and next-start handoffs.",
            "- When a fact changed, record the correction with absolute dates and retire the stale "
            "assumption instead of leaving both versions implied as current.",
            "- Write durable updates back through MemPalace when the tools are available. Prefer "
            "diary or equivalent save tools for new verified context.",
            "- After any durable writeback, immediately verify recall on the same lane through "
            "`mempalace_search` or `mempalace_diary_read`, and report what the readback proved "
            "or why it could not be completed.",
            "- If MemPalace is unavailable on this lane, say that plainly in the checkpoint, capture "
            "the exact restore step, and do not pretend memory was refreshed.",
            "- Do not default to `mempalace compress` or lossy AAAK compaction. Raw recall is the "
            "default; only recommend compression as a deliberate operator follow-up when the evidence "
            "clearly justifies it.",
            "",
            "Start the handoff with exactly these lines:",
            f"- {MEMPALACE_WRITEBACK_STATUS_PREFIX} one of wrote, corrected, deferred, unavailable, or none",
            f"- {MEMPALACE_WRITEBACK_AT_PREFIX} an absolute ISO-8601 UTC timestamp when a MemPalace write happened, otherwise n/a",
            f"- {MEMPALACE_WRITEBACK_SCOPE_PREFIX} {label}",
            f"- {MEMPALACE_ROUNDTRIP_STATUS_PREFIX} one of verified, failed, deferred, unavailable, or none",
            f"- {MEMPALACE_ROUNDTRIP_AT_PREFIX} an absolute ISO-8601 UTC timestamp when post-write recall was tested, otherwise n/a",
            f"- {MEMPALACE_ROUNDTRIP_SCOPE_PREFIX} {label}",
            f"- {MEMPALACE_ROUNDTRIP_DETAIL_PREFIX} a concise search/read proof or failure mode",
            "",
            "Then return a concise handoff with:",
            "- memory status on this lane",
            "- sources reviewed",
            "- durable truths written or corrected",
            "- unresolved gaps or restore steps",
            "- next watchpoints for the next maintenance pass",
        ]
    )


def is_mempalace_automation_task(task: Any) -> bool:
    name = str(_integration_value(task, "name") or "").strip().lower()
    summary = str(_integration_value(task, "summary") or "").strip().lower()
    objective_template = str(_integration_value(task, "objective_template") or "").strip().lower()
    marker = MEMPALACE_MEMORY_TASK_MARKER.lower()
    return (
        name == MEMPALACE_MEMORY_TASK_NAME.lower()
        or marker in summary
        or marker in objective_template
    )


def build_mempalace_control_plane_proof_objective(
    *,
    project_label: str | None,
    project_path: str | None,
) -> str:
    label = str(project_label or "Current workspace").strip() or "Current workspace"
    path = str(project_path or "current workspace").strip() or "current workspace"
    return "\n".join(
        [
            "# MemPalace Direct Proof",
            "",
            f"Project: {label}",
            f"Workspace: {path}",
            "",
            "Run a backend-triggered, read-only proof that this connected lane can actively use "
            "MemPalace right now.",
            "",
            MEMPALACE_DIRECT_PROOF_MARKER,
            "- Start by calling `mempalace_status` on this lane so the proof is anchored to live "
            "MemPalace availability.",
            "- This is a read-only proof. Do not write, compact, or mutate MemPalace state in this "
            "mission.",
            "- Use `mempalace_search` for the current project label or workspace path to prove live "
            "recall.",
            "- If search is inconclusive but diary recall is available, use `mempalace_diary_read` "
            "to confirm recent durable memory without writing anything new.",
            "- If the required tools are unavailable, say that plainly and stop rather than "
            "guessing.",
            "",
            "End the final checkpoint with exactly these lines:",
            f"- {MEMPALACE_CONTROL_PLANE_PROOF_STATUS_PREFIX} one of verified, failed, unavailable, or none",
            f"- {MEMPALACE_CONTROL_PLANE_PROOF_AT_PREFIX} an absolute ISO-8601 UTC timestamp when the live proof ran, otherwise n/a",
            f"- {MEMPALACE_CONTROL_PLANE_PROOF_SCOPE_PREFIX} {label}",
            f"- {MEMPALACE_CONTROL_PLANE_PROOF_DETAIL_PREFIX} concise live proof detail from mempalace_status/search/diary_read",
            "",
            "Then summarize:",
            "- lane memory tool status",
            "- read-only proof steps taken",
            "- exact proof result or failure mode",
            "- next operator follow-up only if the proof failed",
        ]
    )


def is_mempalace_direct_proof_mission(mission: Any) -> bool:
    name = str(_integration_value(mission, "name") or "").strip().lower()
    objective = str(_integration_value(mission, "objective") or "").strip().lower()
    marker = MEMPALACE_DIRECT_PROOF_MARKER.lower()
    return name.startswith(MEMPALACE_DIRECT_PROOF_MISSION_NAME.lower()) or marker in objective


def build_mempalace_protocol_lines(integrations: Iterable[Any]) -> list[str]:
    memory_sources = [integration for integration in integrations if is_mempalace_integration(integration)]
    if not memory_sources:
        return []

    lines = [
        "MemPalace memory protocol:",
        *[
            f"- {str(_integration_value(integration, 'name') or 'MemPalace')} "
            f"({str(_integration_value(integration, 'kind') or 'memory')})"
            + (
                f" at {str(_integration_value(integration, 'base_url') or '').strip()}"
                if str(_integration_value(integration, "base_url") or "").strip()
                else ""
            )
            + (
                f". Notes: {str(_integration_value(integration, 'notes') or '').strip()}"
                if str(_integration_value(integration, "notes") or "").strip()
                else ""
            )
            for integration in memory_sources
        ],
        "- Before answering questions about prior decisions, people, projects, or earlier runs, "
        "query MemPalace first instead of guessing from thread memory.",
        "- Prefer verbatim recall when you need to explain why a decision was made or what tradeoff "
        "was accepted.",
        "- If this run produces durable context the next operator or mission will need, write it back "
        "through MemPalace before you stop when the lane exposes the save/diary tools.",
        "- If a fact changes, update or invalidate the stale memory record instead of leaving both "
        "versions implied as current.",
        "- If MemPalace is unavailable on this lane, say that plainly and continue without pretending "
        "you verified historical context.",
    ]
    return lines
