from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from openzues.schemas import HermesToolPolicyView, SetupMode


@dataclass(frozen=True, slots=True)
class HermesToolsetSpec:
    name: str
    capability_family: str
    summary: str
    posture: str = "native"
    warning: str | None = None
    expands_to: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()


_SPECS: tuple[HermesToolsetSpec, ...] = (
    HermesToolsetSpec(
        name="safe",
        capability_family="guardrails",
        summary="Use the safest available lane behavior and keep approval edges explicit.",
    ),
    HermesToolsetSpec(
        name="skills",
        capability_family="skill orchestration",
        summary="Auto-attach matching local and Hermes skillbooks before broadening scope.",
    ),
    HermesToolsetSpec(
        name="file",
        capability_family="workspace execution",
        summary="Inspect and edit repo files directly inside the saved workspace.",
    ),
    HermesToolsetSpec(
        name="terminal",
        capability_family="workspace execution",
        summary="Run shell commands and verification directly on the connected coding lane.",
        aliases=("bash", "shell"),
    ),
    HermesToolsetSpec(
        name="search",
        capability_family="research",
        summary="Bias the run toward repo and evidence gathering before edits.",
    ),
    HermesToolsetSpec(
        name="vision",
        capability_family="ui observation",
        summary="Use screenshots and visual checks when the surface is UI-heavy.",
    ),
    HermesToolsetSpec(
        name="image_gen",
        capability_family="creative generation",
        summary="Permit bitmap generation when the task needs net-new visual assets.",
    ),
    HermesToolsetSpec(
        name="browser",
        capability_family="browser verification",
        summary="Use browser-driven verification for web flows, dashboards, and UI regressions.",
    ),
    HermesToolsetSpec(
        name="cronjob",
        capability_family="automation",
        summary="Treat the objective as recurring work that should relaunch on schedule.",
        aliases=("cron", "scheduler"),
    ),
    HermesToolsetSpec(
        name="messaging",
        capability_family="gateway orchestration",
        summary="Plan for remote/operator or channel-facing delivery surfaces.",
        posture="partial",
        warning=(
            "Messaging and channel toolsets are persisted as launch intent and prompt guidance, "
            "but OpenZues does not yet provide Hermes-level live channel runtime parity."
        ),
    ),
    HermesToolsetSpec(
        name="tts",
        capability_family="voice",
        summary="Prepare for voice or spoken output surfaces.",
        posture="advisory",
        warning=(
            "Voice/TTS toolsets are advisory today; OpenZues does not yet ship Hermes-style "
            "voice runtime parity."
        ),
    ),
    HermesToolsetSpec(
        name="todo",
        capability_family="planning",
        summary="Bias the run toward explicit checklists, next steps, and scoped execution.",
    ),
    HermesToolsetSpec(
        name="memory",
        capability_family="memory",
        summary="Use durable memory and checkpoint recall when the mission benefits from it.",
        posture="partial",
        warning=(
            "Memory toolsets are partially mapped through checkpoints and MemPalace seams, but "
            "Hermes memory-provider parity is not complete yet."
        ),
    ),
    HermesToolsetSpec(
        name="session_search",
        capability_family="memory",
        summary=(
            "Search saved missions, checkpoints, and proof handoffs before "
            "restating the same uncertainty."
        ),
        posture="partial",
        warning=(
            "Session-search recall is live through the OpenZues recall deck, API, and CLI, but "
            "full Hermes transcript-memory parity is not complete yet."
        ),
    ),
    HermesToolsetSpec(
        name="clarify",
        capability_family="operator alignment",
        summary=(
            "Ask for the exact missing operator decision instead of guessing "
            "through ambiguity."
        ),
    ),
    HermesToolsetSpec(
        name="code_execution",
        capability_family="workspace execution",
        summary="Treat the lane as an execution environment for builds, tests, and scripts.",
        aliases=("exec",),
    ),
    HermesToolsetSpec(
        name="delegation",
        capability_family="multi-agent delegation",
        summary=(
            "Use Codex built-in agents when the mission posture says parallel "
            "helper roles are worth it."
        ),
    ),
    HermesToolsetSpec(
        name="homeassistant",
        capability_family="device integration",
        summary="Plan against Home Assistant or device automations.",
        posture="advisory",
        warning=(
            "Home Assistant toolsets are advisory today; OpenZues does not yet ship Hermes-style "
            "device-control parity."
        ),
    ),
    HermesToolsetSpec(
        name="debugging",
        capability_family="verification",
        summary="Prefer proofs, failing tests, and repair loops over speculative refactors.",
    ),
    HermesToolsetSpec(
        name="hermes-acp",
        capability_family="editor bridge",
        summary=(
            "Shape the run like a local coding/editor bridge with repo "
            "execution and delegation."
        ),
        expands_to=("safe", "skills", "file", "terminal", "delegation", "debugging"),
        posture="partial",
        warning=(
            "ACP/editor posture is modeled in OpenZues mission control, but full Hermes ACP "
            "editor integration is not complete yet."
        ),
    ),
    HermesToolsetSpec(
        name="hermes-api-server",
        capability_family="gateway orchestration",
        summary="Shape the run like a remote API control plane with memory and delegation seams.",
        expands_to=("safe", "skills", "memory", "session_search", "delegation", "clarify"),
        posture="partial",
        warning=(
            "Hermes API-server posture is modeled as a launch policy, not a full drop-in Hermes "
            "gateway/runtime replacement yet."
        ),
    ),
    HermesToolsetSpec(
        name="hermes-cli",
        capability_family="operator workflow",
        summary=(
            "Bias the run toward terminal-first control, repo inspection, and "
            "iterative coding loops."
        ),
        expands_to=("safe", "skills", "file", "terminal", "search", "delegation", "debugging"),
    ),
    HermesToolsetSpec(
        name="hermes-gateway",
        capability_family="gateway orchestration",
        summary=(
            "Bias the run toward remote ingress, schedules, memory upkeep, and "
            "operator delivery."
        ),
        expands_to=(
            "safe",
            "skills",
            "messaging",
            "cronjob",
            "memory",
            "session_search",
            "clarify",
        ),
        posture="partial",
        warning=(
            "Gateway/channel parity is still incomplete, so this toolset currently guides launch "
            "policy and prompts more than transport execution."
        ),
    ),
    HermesToolsetSpec(
        name="hermes-telegram",
        capability_family="channel delivery",
        summary="Bias the run toward Telegram-oriented channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Telegram parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-discord",
        capability_family="channel delivery",
        summary="Bias the run toward Discord-oriented channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Discord parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-whatsapp",
        capability_family="channel delivery",
        summary="Bias the run toward WhatsApp-oriented channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="WhatsApp parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-slack",
        capability_family="channel delivery",
        summary="Bias the run toward Slack-oriented channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Slack parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-signal",
        capability_family="channel delivery",
        summary="Bias the run toward Signal-oriented channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Signal parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-bluebubbles",
        capability_family="channel delivery",
        summary="Bias the run toward BlueBubbles/iMessage channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="BlueBubbles parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-homeassistant",
        capability_family="device integration",
        summary="Bias the run toward Home Assistant automations and device delivery.",
        expands_to=("homeassistant", "safe", "clarify"),
        posture="advisory",
        warning="Home Assistant parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-email",
        capability_family="channel delivery",
        summary="Bias the run toward email-triggered or email-delivered workflows.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Email channel parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-mattermost",
        capability_family="channel delivery",
        summary="Bias the run toward Mattermost channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Mattermost parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-matrix",
        capability_family="channel delivery",
        summary="Bias the run toward Matrix channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Matrix parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-dingtalk",
        capability_family="channel delivery",
        summary="Bias the run toward DingTalk channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="DingTalk parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-feishu",
        capability_family="channel delivery",
        summary="Bias the run toward Feishu channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Feishu parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-weixin",
        capability_family="channel delivery",
        summary="Bias the run toward Weixin channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="Weixin parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-wecom",
        capability_family="channel delivery",
        summary="Bias the run toward WeCom channel handling.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="WeCom parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-sms",
        capability_family="channel delivery",
        summary="Bias the run toward SMS-triggered or SMS-delivered workflows.",
        expands_to=("messaging", "safe", "clarify"),
        posture="advisory",
        warning="SMS parity is not implemented end to end in OpenZues yet.",
    ),
    HermesToolsetSpec(
        name="hermes-webhook",
        capability_family="gateway orchestration",
        summary="Bias the run toward webhook-delivered ingress and event triggers.",
        expands_to=("messaging", "cronjob", "safe", "clarify"),
        posture="partial",
        warning=(
            "Webhook posture maps well onto OpenZues notification and remote-ingress seams, but "
            "full Hermes webhook parity is still in progress."
        ),
    ),
)

_SPEC_BY_NAME = {spec.name: spec for spec in _SPECS}
_ALIASES = {alias: spec.name for spec in _SPECS for alias in spec.aliases}


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def normalize_hermes_toolsets(toolsets: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    for raw in toolsets or ():
        value = str(raw or "").strip().lower()
        if not value:
            continue
        normalized.append(_ALIASES.get(value, value))
    return _dedupe(normalized)


def expand_hermes_toolsets(toolsets: Iterable[str] | None) -> list[str]:
    queue = list(normalize_hermes_toolsets(toolsets))
    expanded: list[str] = []
    seen: set[str] = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        expanded.append(current)
        spec = _SPEC_BY_NAME.get(current)
        if spec is not None:
            queue.extend(spec.expands_to)
    return expanded


def infer_hermes_toolsets(
    objective: str | None,
    *,
    explicit_toolsets: Iterable[str] | None = None,
    project_label: str | None = None,
    project_path: str | None = None,
    setup_mode: SetupMode = "local",
    use_builtin_agents: bool = True,
    run_verification: bool = True,
    cadence_minutes: int | None = None,
) -> list[str]:
    explicit = normalize_hermes_toolsets(explicit_toolsets)
    if explicit:
        return explicit

    context = " ".join(
        part for part in (objective or "", project_label or "", project_path or "") if part
    ).lower()

    selected = ["safe", "skills"]
    if setup_mode == "local" or project_path:
        selected.extend(["file", "terminal"])
    if use_builtin_agents:
        selected.append("delegation")
    if run_verification:
        selected.append("debugging")
    if cadence_minutes is not None:
        selected.append("cronjob")
    if any(
        keyword in context
        for keyword in (
            "browser",
            "frontend",
            "ui",
            "page",
            "dashboard",
            "website",
            "render",
            "css",
            "layout",
            "screenshot",
        )
    ):
        selected.extend(["browser", "vision"])
    if any(
        keyword in context
        for keyword in (
            "research",
            "docs",
            "readme",
            "search",
            "investigate",
            "inventory",
            "parity",
            "audit",
        )
    ):
        selected.append("search")
    if any(
        keyword in context
        for keyword in ("memory", "mempalace", "checkpoint", "recall", "continuity")
    ):
        selected.extend(["memory", "session_search"])
    if any(
        keyword in context for keyword in ("image", "mockup", "illustration", "artwork")
    ):
        selected.append("image_gen")
    if setup_mode == "remote" or any(
        keyword in context
        for keyword in (
            "remote",
            "operator",
            "notify",
            "inbox",
            "channel",
            "slack",
            "telegram",
            "discord",
            "whatsapp",
            "email",
            "message",
        )
    ):
        selected.extend(["messaging", "clarify"])
    return _dedupe(selected)


def build_hermes_tool_policy(
    toolsets: Iterable[str] | None,
    *,
    setup_mode: SetupMode = "local",
) -> HermesToolPolicyView:
    selected = normalize_hermes_toolsets(toolsets)
    expanded = expand_hermes_toolsets(selected)
    families = _dedupe(
        _SPEC_BY_NAME[item].capability_family for item in expanded if item in _SPEC_BY_NAME
    )
    warnings = _dedupe(
        _SPEC_BY_NAME[item].warning or ""
        for item in selected
        if item in _SPEC_BY_NAME and _SPEC_BY_NAME[item].warning
    )
    if not selected:
        headline = "Hermes tool policy is unstaged"
        summary = (
            "No explicit Hermes toolsets are pinned yet, so OpenZues will rely on its default "
            f"{setup_mode}-mode mission contract."
        )
    else:
        headline = "Hermes tool policy is active"
        summary = (
            "OpenZues will treat "
            + ", ".join(selected[:4])
            + (
                f", and {selected[4]}"
                if len(selected) == 5
                else f", plus {len(selected) - 4} more toolsets"
                if len(selected) > 5
                else ""
            )
            + " as the active Hermes-inspired tool posture for this run."
        )
    return HermesToolPolicyView(
        toolsets=selected,
        capability_families=families,
        headline=headline,
        summary=summary,
        enforcement="advisory",
        warnings=warnings,
    )


def build_hermes_tool_policy_lines(policy: HermesToolPolicyView | None) -> list[str]:
    if policy is None or not policy.toolsets:
        return []
    lines = [
        "Hermes tool policy:",
        f"- Active toolsets: {', '.join(policy.toolsets)}.",
    ]
    if policy.capability_families:
        lines.append(f"- Capability families: {', '.join(policy.capability_families)}.")
    lines.append(
        "- Treat this policy as the preferred tool posture before broadening scope or asking "
        "for a new runtime surface."
    )
    for warning in policy.warnings[:3]:
        lines.append(f"- Advisory gap: {warning}")
    return lines
