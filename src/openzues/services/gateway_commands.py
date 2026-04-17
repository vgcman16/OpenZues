from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

_SUPPORTED_AGENT_ID = "openzues"


@dataclass(frozen=True, slots=True)
class GatewayCommandArgSpec:
    name: str
    description: str
    type: Literal["boolean", "integer", "string"]
    required: bool = False

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "type": self.type,
        }
        if self.required:
            payload["required"] = True
        return payload


@dataclass(frozen=True, slots=True)
class GatewayCommandSpec:
    name: str
    description: str
    category: str
    accepts_args: bool = False
    args: tuple[GatewayCommandArgSpec, ...] = ()
    source: Literal["native", "plugin", "skill"] = "native"
    scope: Literal["native", "text", "both"] = "native"

    def as_payload(self, *, include_args: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": self.name,
            "nativeName": self.name,
            "description": self.description,
            "category": self.category,
            "source": self.source,
            "scope": self.scope,
            "acceptsArgs": self.accepts_args,
        }
        if include_args and self.args:
            payload["args"] = [argument.as_payload() for argument in self.args]
        return payload


def _bool_arg(name: str, description: str) -> GatewayCommandArgSpec:
    return GatewayCommandArgSpec(name=name, description=description, type="boolean")


def _int_arg(
    name: str,
    description: str,
    *,
    required: bool = False,
) -> GatewayCommandArgSpec:
    return GatewayCommandArgSpec(
        name=name,
        description=description,
        type="integer",
        required=required,
    )


def _str_arg(
    name: str,
    description: str,
    *,
    required: bool = False,
) -> GatewayCommandArgSpec:
    return GatewayCommandArgSpec(
        name=name,
        description=description,
        type="string",
        required=required,
    )


_COMMAND_SPECS: tuple[GatewayCommandSpec, ...] = (
    GatewayCommandSpec(
        name="serve",
        description="Run the local OpenZues control plane server.",
        category="operator",
        accepts_args=True,
        args=(
            _str_arg("host", "Host to bind."),
            _int_arg("port", "Port to bind."),
            _bool_arg("reload", "Enable hot reload."),
        ),
    ),
    GatewayCommandSpec(
        name="recall",
        description="Browse durable recall or search for saved mission context.",
        category="operator",
        accepts_args=True,
        args=(
            _str_arg("query", "Optional search query."),
            _int_arg("project-id", "Optional project filter."),
            _int_arg("limit", "Maximum recall items to return."),
            _bool_arg("json", "Emit the recall results as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="learn",
        description="Review learned cortex/doctrine posture from recent missions.",
        category="operator",
        accepts_args=True,
        args=(_bool_arg("json", "Emit the learning review payload as JSON."),),
    ),
    GatewayCommandSpec(
        name="status",
        description="Emit the operator status summary as JSON.",
        category="operator",
        accepts_args=True,
        args=(_bool_arg("json", "Emit the operator status summary as JSON."),),
    ),
    GatewayCommandSpec(
        name="watch",
        description="Watch the live parity lane and keep the next bounded move moving.",
        category="operator",
        accepts_args=True,
        args=(
            _str_arg("host", "Host for the live OpenZues server."),
            _int_arg("port", "Port for the live OpenZues server."),
            _str_arg("url", "Explicit base URL for the live OpenZues server."),
            _int_arg("mission-id", "Watch a specific mission id."),
            _str_arg("task-name", "Mission or task label to watch."),
            _bool_arg("json", "Emit the watch result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="launch",
        description="Launch a named opportunity from the current launchpad.",
        category="operator",
        accepts_args=True,
        args=(
            _str_arg("opportunity-id", "Launchpad opportunity id.", required=True),
            _bool_arg("swarm", "Launch the selected draft through the swarm pipeline."),
            _bool_arg("plan", "Preview the targeted launchpad move without executing it."),
            _bool_arg("json", "Emit the launch result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="continue",
        description="Run the next gateway-aware continue move.",
        category="operator",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="recover",
        description="Run the next gateway-aware recovery move.",
        category="operator",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="harden",
        description="Run the next gateway-aware hardening move.",
        category="operator",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="queue",
        description="Plan or execute one bounded attention-queue move.",
        category="operator",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="doctor",
        description="Inspect the Hermes parity doctor posture.",
        category="operator",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="browser.status",
        description="Inspect the browser runtime/operator posture.",
        category="browser",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="browser.doctor",
        description="Inspect browser posture and optionally verify the live control-plane URL.",
        category="browser",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="browser.verify",
        description="Run a bounded browser verification against the control plane.",
        category="browser",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="browser.open",
        description="Open a URL in the agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("target", "URL to open in the agent-browser session.", required=True),
            _str_arg("session", "agent-browser session name for the browser tab."),
            _bool_arg("json", "Emit the browser open result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.snapshot",
        description="Capture a DOM/browser snapshot from the agent-browser session.",
        category="browser",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="browser.console",
        description="Read console output from the agent-browser session.",
        category="browser",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="browser.errors",
        description="Read page errors from the agent-browser session.",
        category="browser",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="routes.test",
        description="Send a synthetic delivery through one saved notification route.",
        category="routes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="routes.list",
        description="List saved notification routes.",
        category="routes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="routes.deliveries",
        description="List saved outbound deliveries.",
        category="routes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="routes.replay",
        description="Replay saved outbound deliveries through the route mesh.",
        category="routes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="hermes.arm-shell",
        description="Arm a shell-backed Hermes lane for the current workspace.",
        category="hermes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="hermes.arm-docker",
        description="Stage a Docker-backed Hermes runtime profile.",
        category="hermes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="hermes.preflight-docker",
        description="Run a bounded Docker preflight for the staged Hermes backend.",
        category="hermes",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="update.status",
        description="Inspect runtime update posture and repo state.",
        category="update",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="setup",
        description="Inspect the saved setup posture.",
        category="setup",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="setup.wizard",
        description="Inspect the saved setup wizard session.",
        category="setup",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="setup.wizard.update",
        description="Update the saved setup wizard session.",
        category="setup",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="setup.launch",
        description="Inspect the saved launch handoff payload.",
        category="setup",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="gateway.show",
        description="Inspect the saved gateway bootstrap profile.",
        category="gateway",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="gateway.doctor",
        description="Inspect the gateway capability summary.",
        category="gateway",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="gateway.memory-prove",
        description="Launch a direct MemPalace proof mission through the gateway.",
        category="gateway",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="gateway.bootstrap",
        description="Stage the gateway bootstrap resources for one workspace.",
        category="gateway",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="setup.bootstrap",
        description="Stage the full setup bootstrap posture for one workspace.",
        category="setup",
        accepts_args=True,
    ),
    GatewayCommandSpec(
        name="setup.reset",
        description="Reset saved setup posture and related managed state.",
        category="setup",
        accepts_args=True,
    ),
)


class GatewayCommandsService:
    def build_catalog(
        self,
        *,
        agent_id: str | None = None,
        include_args: bool = True,
        provider: str | None = None,
        scope: Literal["both", "native", "text"] = "both",
    ) -> dict[str, Any]:
        del provider
        if agent_id is not None and agent_id != _SUPPORTED_AGENT_ID:
            raise ValueError(f'unknown agent id "{agent_id}"')
        if scope == "text":
            return {"commands": []}
        return {
            "commands": [
                spec.as_payload(include_args=include_args)
                for spec in _COMMAND_SPECS
                if spec.scope in {"native", "both"}
            ]
        }
