from __future__ import annotations

import shutil

from openzues.schemas import (
    BrowserPostureView,
    BrowserSurfaceSummaryView,
    BrowserToolStatusView,
    GatewayBootstrapView,
    GatewayCapabilityBrowserRuntimeView,
    GatewayCapabilityView,
    SignalLevel,
)


def find_agent_browser_command() -> str | None:
    return shutil.which("agent-browser.cmd") or shutil.which("agent-browser")


def _local_browser_tool_view(command: str | None) -> BrowserToolStatusView:
    if command:
        return BrowserToolStatusView(
            available=True,
            command=command,
            summary=f"agent-browser is available at {command}.",
        )
    return BrowserToolStatusView(
        available=False,
        command=None,
        summary="agent-browser is not installed or not on PATH.",
    )


def _surface_summary(
    *,
    status: str,
    headline: str,
    summary: str,
) -> BrowserSurfaceSummaryView:
    return BrowserSurfaceSummaryView(status=status, headline=headline, summary=summary)


def _pick_browser_runtime(
    gateway_bootstrap: GatewayBootstrapView | None,
    gateway_capability: GatewayCapabilityView | None,
) -> tuple[
    GatewayCapabilityBrowserRuntimeView | None,
    GatewayCapabilityBrowserRuntimeView | None,
]:
    saved_launch_runtime = (
        gateway_bootstrap.runtime_inventory.browser_runtime
        if gateway_bootstrap is not None and gateway_bootstrap.runtime_inventory is not None
        else None
    )
    live_gateway_runtime = (
        gateway_capability.inventory.browser_runtime
        if gateway_capability is not None and gateway_capability.inventory is not None
        else None
    )
    return saved_launch_runtime, live_gateway_runtime


def _runtime_subject(
    *,
    saved_launch_runtime: GatewayCapabilityBrowserRuntimeView | None,
    live_gateway_runtime: GatewayCapabilityBrowserRuntimeView | None,
    ready_only: bool = False,
) -> tuple[str, bool]:
    labels: list[str] = []
    if saved_launch_runtime is not None and (
        not ready_only or saved_launch_runtime.status == "ready"
    ):
        labels.append("saved launch browser runtime")
    if live_gateway_runtime is not None and (
        not ready_only or live_gateway_runtime.status == "ready"
    ):
        labels.append("live gateway browser runtime")
    if len(labels) == 2:
        return "saved launch and live gateway browser runtimes", True
    if labels:
        return labels[0], False
    return "browser runtime", False


def build_browser_posture(
    *,
    control_plane_url: str,
    gateway_bootstrap: GatewayBootstrapView | None,
    gateway_capability: GatewayCapabilityView | None,
    agent_browser_command: str | None = None,
) -> BrowserPostureView:
    local_tool = _local_browser_tool_view(
        find_agent_browser_command() if agent_browser_command is None else agent_browser_command
    )
    saved_launch_runtime, live_gateway_runtime = _pick_browser_runtime(
        gateway_bootstrap,
        gateway_capability,
    )

    ready_runtime = next(
        (
            runtime
            for runtime in (saved_launch_runtime, live_gateway_runtime)
            if runtime is not None and runtime.status == "ready"
        ),
        None,
    )
    known_runtime = next(
        (
            runtime
            for runtime in (saved_launch_runtime, live_gateway_runtime)
            if runtime is not None
        ),
        None,
    )

    recommended_action = local_tool.summary
    if ready_runtime is not None and ready_runtime.recommended_action:
        recommended_action = ready_runtime.recommended_action
    elif live_gateway_runtime is not None and live_gateway_runtime.recommended_action:
        recommended_action = live_gateway_runtime.recommended_action
    elif saved_launch_runtime is not None and saved_launch_runtime.recommended_action:
        recommended_action = saved_launch_runtime.recommended_action
    elif known_runtime is not None and known_runtime.recommended_action:
        recommended_action = known_runtime.recommended_action

    status: SignalLevel
    if local_tool.available and ready_runtime is not None:
        ready_subject, ready_plural = _runtime_subject(
            saved_launch_runtime=saved_launch_runtime,
            live_gateway_runtime=live_gateway_runtime,
            ready_only=True,
        )
        status = "ready"
        headline = "Browser control is operator-ready"
        summary = (
            f"Local agent-browser is available and the {ready_subject} "
            f"{'are' if ready_plural else 'is'} ready for browser-led verification."
        )
    elif local_tool.available and known_runtime is not None:
        known_subject, known_plural = _runtime_subject(
            saved_launch_runtime=saved_launch_runtime,
            live_gateway_runtime=live_gateway_runtime,
        )
        status = "warn"
        headline = "Browser runtime needs repair"
        summary = (
            f"Local agent-browser is available, but the {known_subject} still "
            f"{'need' if known_plural else 'needs'} attention."
        )
    elif local_tool.available:
        status = "info"
        headline = "Browser verification is available"
        summary = (
            "Local agent-browser is available, but no saved launch lane is publishing a browser "
            "runtime yet."
        )
    elif ready_runtime is not None:
        ready_subject, ready_plural = _runtime_subject(
            saved_launch_runtime=saved_launch_runtime,
            live_gateway_runtime=live_gateway_runtime,
            ready_only=True,
        )
        status = "warn"
        headline = "Browser runtime is staged, but local verification is missing"
        summary = (
            f"The {ready_subject} {'are' if ready_plural else 'is'} ready, but local "
            "agent-browser tooling is missing on this host."
        )
    else:
        status = "warn"
        headline = "Browser tooling needs repair"
        summary = (
            "agent-browser is not available locally, so browser-led parity verification cannot "
            "run cleanly yet."
        )

    return BrowserPostureView(
        status=status,
        headline=headline,
        summary=summary,
        control_plane_url=control_plane_url,
        local_agent_browser=local_tool,
        saved_launch=(
            _surface_summary(
                status=gateway_bootstrap.status,
                headline=gateway_bootstrap.headline,
                summary=gateway_bootstrap.summary,
            )
            if gateway_bootstrap is not None
            else None
        ),
        saved_launch_browser_runtime=saved_launch_runtime,
        live_gateway=(
            _surface_summary(
                status=gateway_capability.level,
                headline=gateway_capability.headline,
                summary=gateway_capability.summary,
            )
            if gateway_capability is not None
            else None
        ),
        live_gateway_browser_runtime=live_gateway_runtime,
        recommended_action=recommended_action,
    )
