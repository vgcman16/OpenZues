from __future__ import annotations

from openzues.schemas import GatewayBootstrapView, GatewayCapabilityView
from openzues.services.browser_posture import build_browser_posture


def _browser_runtime(*, status: str, recommended_action: str) -> dict[str, object]:
    return {
        "headline": f"Browser runtime is {status}",
        "summary": f"Runtime status is {status}.",
        "status": status,
        "lane_count": 1,
        "connected_lane_count": 1,
        "ready_lane_count": 1 if status == "ready" else 0,
        "method_count": 1,
        "service_count": 1,
        "plugin_count": 1,
        "server_count": 1,
        "methods": ["browser.request"],
        "services": ["browser-control"],
        "plugins": ["browser"],
        "servers": ["browser-runtime"],
        "recommended_action": recommended_action,
        "lanes": [],
    }


def _gateway_bootstrap(
    runtime: dict[str, object] | None = None,
) -> GatewayBootstrapView:
    return GatewayBootstrapView.model_validate(
        {
            "status": "ready",
            "headline": "Gateway bootstrap is launch-ready",
            "summary": "Saved launch lane is aligned.",
            "launch_defaults_summary": "Saved launch defaults are configured.",
            "runtime_inventory": (
                {
                    "headline": "Bootstrap runtime inventory",
                    "summary": "Saved launch runtime inventory is available.",
                    "browser_runtime": runtime,
                }
                if runtime is not None
                else None
            ),
        }
    )


def _gateway_capability(
    runtime: dict[str, object] | None = None,
) -> GatewayCapabilityView:
    return GatewayCapabilityView.model_validate(
        {
            "level": "ready",
            "headline": "Gateway capability is operator-ready",
            "summary": "Control plane is aligned.",
            "connected_lane_health": {
                "headline": "Connected lane health is stable",
                "summary": "Connected lanes are healthy.",
            },
            "inventory": {
                "headline": "Inventory is visible",
                "summary": "Observed runtime inventory is available.",
                "browser_runtime": runtime,
            },
            "approval_posture": {
                "headline": "Approval posture is stable",
                "summary": "Approval posture is nominal.",
            },
            "launch_policy": {
                "headline": "Launch policy is stable",
                "summary": "Launch defaults are aligned.",
            },
            "diagnostics": {
                "headline": "Diagnostics are clean",
                "summary": "No blocking diagnostics were found.",
            },
            "checked_at": "2026-04-21T00:00:00Z",
        }
    )


def test_build_browser_posture_names_live_gateway_runtime_when_it_is_the_only_degraded_source() -> (
    None
):
    posture = build_browser_posture(
        control_plane_url="http://127.0.0.1:8884",
        gateway_bootstrap=None,
        gateway_capability=_gateway_capability(
            _browser_runtime(
                status="warn",
                recommended_action="Refresh the live browser lane.",
            )
        ),
        agent_browser_command="agent-browser.cmd",
    )

    assert posture.status == "warn"
    assert posture.summary == (
        "Local agent-browser is available, but the live gateway browser runtime still "
        "needs attention."
    )
    assert posture.recommended_action == "Refresh the live browser lane."


def test_build_browser_posture_keeps_saved_launch_wording_for_saved_runtime_only() -> None:
    posture = build_browser_posture(
        control_plane_url="http://127.0.0.1:8884",
        gateway_bootstrap=_gateway_bootstrap(
            _browser_runtime(
                status="warn",
                recommended_action="Repair the saved launch browser lane.",
            )
        ),
        gateway_capability=None,
        agent_browser_command="agent-browser.cmd",
    )

    assert posture.status == "warn"
    assert posture.summary == (
        "Local agent-browser is available, but the saved launch browser runtime still "
        "needs attention."
    )


def test_build_browser_posture_uses_plural_ready_summary_when_both_runtimes_are_ready() -> None:
    runtime = _browser_runtime(
        status="ready",
        recommended_action="Keep the browser runtime warm.",
    )

    posture = build_browser_posture(
        control_plane_url="http://127.0.0.1:8884",
        gateway_bootstrap=_gateway_bootstrap(runtime),
        gateway_capability=_gateway_capability(runtime),
        agent_browser_command="agent-browser.cmd",
    )

    assert posture.status == "ready"
    assert posture.summary == (
        "Local agent-browser is available and the saved launch and live gateway browser "
        "runtimes are ready for browser-led verification."
    )


def test_build_browser_posture_names_ready_live_gateway_runtime_when_local_tool_is_missing() -> (
    None
):
    posture = build_browser_posture(
        control_plane_url="http://127.0.0.1:8884",
        gateway_bootstrap=None,
        gateway_capability=_gateway_capability(
            _browser_runtime(
                status="ready",
                recommended_action="Keep the live browser lane connected.",
            )
        ),
        agent_browser_command=None,
    )

    assert posture.status == "warn"
    assert posture.summary == (
        "The live gateway browser runtime is ready, but local agent-browser tooling is "
        "missing on this host."
    )
