from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

_SUPPORTED_AGENT_ID = "openzues"


@dataclass(frozen=True, slots=True)
class GatewayCommandArgSpec:
    name: str
    description: str
    type: Literal["array", "boolean", "integer", "number", "string"]
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


def _array_arg(
    name: str,
    description: str,
    *,
    required: bool = False,
) -> GatewayCommandArgSpec:
    return GatewayCommandArgSpec(
        name=name,
        description=description,
        type="array",
        required=required,
    )


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


def _number_arg(
    name: str,
    description: str,
    *,
    required: bool = False,
) -> GatewayCommandArgSpec:
    return GatewayCommandArgSpec(
        name=name,
        description=description,
        type="number",
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
        name="agents.list",
        description="List configured agents and workspace posture.",
        category="operator",
        accepts_args=True,
        args=(_bool_arg("json", "Emit the configured agent inventory as JSON."),),
    ),
    GatewayCommandSpec(
        name="channels.status",
        description="Inspect the notification route channel inventory.",
        category="operator",
        accepts_args=True,
        args=(_bool_arg("json", "Emit the notification route inventory as JSON."),),
    ),
    GatewayCommandSpec(
        name="channels.start",
        description="Start a supported channel runtime account when a native runtime is available.",
        category="operator",
        accepts_args=True,
        args=(
            _str_arg("channel", "Channel id to start.", required=True),
            _str_arg("account-id", "Optional account id for the channel runtime."),
            _bool_arg("json", "Emit the channel start result as JSON."),
        ),
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
        name="browser.start",
        description="Start or initialize an agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to start."),
            _bool_arg("json", "Emit the browser start result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.stop",
        description="Stop the agent-browser session, or all sessions when requested.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to stop."),
            _bool_arg("all", "Stop all active agent-browser sessions."),
            _bool_arg("json", "Emit the browser stop result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.batch",
        description="Execute a bounded sequence of agent-browser commands.",
        category="browser",
        accepts_args=True,
        args=(
            _array_arg("commands", "One-line browser command strings to run.", required=True),
            _bool_arg("bail", "Stop on the first failed command."),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser batch result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.dashboard.start",
        description="Start the agent-browser observability dashboard.",
        category="browser",
        accepts_args=True,
        args=(
            _int_arg("port", "Optional dashboard port."),
            _str_arg("session", "agent-browser session name for operator traceability."),
            _bool_arg("json", "Emit the browser dashboard start result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.dashboard.stop",
        description="Stop the agent-browser observability dashboard.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name for operator traceability."),
            _bool_arg("json", "Emit the browser dashboard stop result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.chat",
        description="Send one natural-language browser instruction through agent-browser chat.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("message", "Natural-language browser instruction.", required=True),
            _str_arg("model", "Optional AI Gateway model name."),
            _bool_arg("quiet", "Hide tool calls and return only the AI text response."),
            _bool_arg("verbose", "Show tool commands and raw output."),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser chat result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.ios.device.list",
        description="List available iOS simulators through the agent-browser iOS provider.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the iOS device list result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.ios.swipe",
        description="Run an iOS provider swipe gesture.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("direction", "Swipe direction: up, down, left, or right.", required=True),
            _int_arg("distance", "Optional swipe distance in pixels."),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the iOS swipe result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.ios.tap",
        description="Run an iOS provider tap gesture against a selector/ref.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("target", "Selector/ref to tap.", required=True),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the iOS tap result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.get",
        description="Read a browser value such as text, title, URL, count, box, or styles.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("what", "Browser value to read.", required=True),
            _str_arg("selector", "Optional selector/ref for element-scoped values."),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser get result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.is",
        description="Check browser element state such as visible, enabled, or checked.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("state", "Browser state to check.", required=True),
            _str_arg("selector", "Selector/ref for the element to check.", required=True),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser state result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.set",
        description="Apply guarded browser settings through agent-browser.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg(
                "setting",
                "Setting: viewport, device, geo, offline, headers, credentials, or media.",
                required=True,
            ),
            _array_arg("values", "Setting values as strings.", required=True),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser setting result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.stream.status",
        description="Inspect browser stream status for an agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser stream status result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.stream.enable",
        description="Enable browser WebSocket streaming for an agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to update."),
            _int_arg("port", "Optional localhost stream port to bind."),
            _bool_arg("json", "Emit the browser stream enable result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.stream.disable",
        description="Disable browser WebSocket streaming for an agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser stream disable result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.network.requests",
        description="List captured browser network requests without clearing the log.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _str_arg("filter", "Optional URL pattern to filter captured requests."),
            _str_arg("type", "Optional resource type filter such as xhr,fetch,document."),
            _str_arg("method", "Optional HTTP method filter."),
            _str_arg("status", "Optional HTTP status filter such as 2xx or 400-499."),
            _bool_arg("json", "Emit the browser network request list as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.network.request",
        description="Read full detail for one captured browser network request.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("requestId", "Captured browser network request id.", required=True),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser network request detail as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.network.har.start",
        description="Start recording browser network activity as a HAR artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to record."),
            _bool_arg("json", "Emit browser HAR start result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.network.har.stop",
        description="Stop HAR recording and save an OpenZues temp HAR artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to record."),
            _bool_arg("json", "Emit browser HAR artifact result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.cookies.get",
        description="Read browser cookies for the current agent-browser context.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser cookies as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.cookies.set",
        description="Set one browser cookie with bounded cookie options.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("name", "Cookie name to set.", required=True),
            _str_arg("value", "Cookie value to set.", required=True),
            _str_arg("url", "Optional URL scope for the cookie."),
            _str_arg("domain", "Optional cookie domain."),
            _str_arg("path", "Optional cookie path."),
            _bool_arg("httpOnly", "Set the HttpOnly cookie flag."),
            _bool_arg("secure", "Set the Secure cookie flag."),
            _str_arg("sameSite", "Optional SameSite policy: Strict, Lax, or None."),
            _int_arg("expires", "Optional Unix timestamp expiration in seconds."),
            _str_arg("session", "agent-browser session name to mutate."),
            _bool_arg("json", "Emit browser cookie mutation result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.cookies.clear",
        description="Clear browser cookies for the current agent-browser context.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to mutate."),
            _bool_arg("json", "Emit browser cookie mutation result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.storage.get",
        description="Read localStorage or sessionStorage from the browser context.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("type", "Storage type: local or session.", required=True),
            _str_arg("key", "Optional storage key to read."),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit browser storage as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.storage.set",
        description="Set a localStorage or sessionStorage key in the browser context.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("type", "Storage type: local or session.", required=True),
            _str_arg("key", "Storage key to set.", required=True),
            _str_arg("value", "String value to store.", required=True),
            _str_arg("session", "agent-browser session name to mutate."),
            _bool_arg("json", "Emit browser storage mutation result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.storage.clear",
        description="Clear localStorage or sessionStorage in the browser context.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("type", "Storage type: local or session.", required=True),
            _str_arg("session", "agent-browser session name to mutate."),
            _bool_arg("json", "Emit browser storage mutation result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.session.current",
        description="Read the current agent-browser session name.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the current browser session as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.session.list",
        description="List active agent-browser sessions.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session context to use."),
            _bool_arg("json", "Emit browser sessions as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.diff.snapshot",
        description="Compare the current browser snapshot to the last session snapshot.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("selector", "Optional CSS selector or @ref scope."),
            _bool_arg("compact", "Use compact snapshot diff output."),
            _int_arg("depth", "Optional snapshot depth limit."),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit browser snapshot diff as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.diff.screenshot",
        description="Compare the current browser screenshot to a controlled baseline image.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("baselinePath", "OpenZues temp screenshot baseline path.", required=True),
            _number_arg("threshold", "Optional color distance threshold between 0 and 1."),
            _str_arg("selector", "Optional CSS selector or @ref scope."),
            _bool_arg("fullPage", "Capture full-page screenshot output."),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit browser screenshot diff as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.diff.url",
        description="Compare two browser URLs through the local agent-browser diff runtime.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("url1", "First URL to compare.", required=True),
            _str_arg("url2", "Second URL to compare.", required=True),
            _bool_arg("screenshot", "Include screenshot comparison output."),
            _bool_arg("fullPage", "Capture full-page screenshot output."),
            _str_arg("waitUntil", "Wait strategy: load, domcontentloaded, or networkidle."),
            _str_arg("selector", "Optional CSS selector or @ref scope."),
            _bool_arg("compact", "Use compact diff output."),
            _int_arg("depth", "Optional snapshot depth limit."),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit browser URL diff as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.download",
        description="Click a selector and save the download to an OpenZues temp artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("selector", "Selector or @ref that starts the download.", required=True),
            _str_arg("filenameHint", "Optional safe filename hint for the temp artifact."),
            _str_arg("session", "agent-browser session name to use."),
            _bool_arg("json", "Emit browser download result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.upload",
        description="Upload OpenZues-controlled temp artifacts through a file input selector.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("selector", "Selector or @ref for the file input.", required=True),
            _array_arg("filePaths", "OpenZues temp artifact paths to upload.", required=True),
            _str_arg("session", "agent-browser session name to use."),
            _bool_arg("json", "Emit browser upload result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.profiler.start",
        description="Start recording a browser performance profile for a session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to profile."),
            _str_arg("categories", "Optional comma-separated trace categories."),
            _bool_arg("json", "Emit browser profiler start result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.profiler.stop",
        description="Stop browser profiling and save an OpenZues temp JSON artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to profile."),
            _bool_arg("json", "Emit browser profiler artifact result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.record.start",
        description="Start recording the browser session to an OpenZues temp WebM artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to record."),
            _str_arg("url", "Optional URL to open when recording starts."),
            _bool_arg("json", "Emit browser record start result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.record.stop",
        description="Stop browser recording and report the current OpenZues WebM artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to record."),
            _bool_arg("json", "Emit browser record stop result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.record.restart",
        description="Restart browser recording into a new OpenZues temp WebM artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to record."),
            _str_arg("url", "Optional URL to open when recording restarts."),
            _bool_arg("json", "Emit browser record restart result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.highlight",
        description="Highlight a browser element for visual debugging.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("selector", "Selector or @ref to highlight.", required=True),
            _str_arg("session", "agent-browser session name to debug."),
            _bool_arg("json", "Emit browser highlight result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.inspect",
        description="Open Chrome DevTools for the active browser page.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to debug."),
            _bool_arg("json", "Emit browser inspect result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.trace.start",
        description="Start recording a browser DevTools trace for an agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to trace."),
            _bool_arg("json", "Emit browser trace start result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.trace.stop",
        description="Stop browser trace recording and save an OpenZues temp ZIP artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to trace."),
            _bool_arg("json", "Emit browser trace artifact result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.auth.list",
        description="List saved browser auth profiles by metadata only.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit browser auth profile metadata as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.auth.show",
        description="Show saved browser auth profile metadata without passwords.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("name", "Browser auth profile name.", required=True),
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit browser auth profile metadata as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.auth.save",
        description="Save a browser auth profile using password stdin instead of argv.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("name", "Browser auth profile name.", required=True),
            _str_arg("url", "Login page URL for the auth profile.", required=True),
            _str_arg("username", "Username or login identifier.", required=True),
            _str_arg(
                "password",
                "Password value passed to agent-browser through stdin, not argv.",
                required=True,
            ),
            _str_arg("usernameSelector", "Optional username field selector."),
            _str_arg("passwordSelector", "Optional password field selector."),
            _str_arg("submitSelector", "Optional submit button selector."),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit browser auth save result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.auth.login",
        description="Login using a saved browser auth profile.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("name", "Browser auth profile name.", required=True),
            _str_arg("session", "agent-browser session name to authenticate."),
            _bool_arg("json", "Emit browser auth login result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.auth.delete",
        description="Delete a saved browser auth profile.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("name", "Browser auth profile name.", required=True),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit browser auth delete result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.tabs",
        description="List tabs from the agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser tabs result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.profiles",
        description="List configured browser profiles from the agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser profiles result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.screenshot",
        description="Capture a browser screenshot from the agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to capture."),
            _bool_arg("full", "Capture the full page instead of the visible viewport."),
            _bool_arg("json", "Emit the browser screenshot result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.pdf",
        description="Capture the active browser page as a PDF artifact.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to capture."),
            _bool_arg("json", "Emit the browser PDF result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.navigate",
        description="Navigate the active agent-browser page to a URL.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("url", "URL to navigate the active browser page to.", required=True),
            _str_arg("session", "agent-browser session name for the browser page."),
            _bool_arg("json", "Emit the browser navigation result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.back",
        description="Navigate the active browser page back in history.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name for the page."),
            _bool_arg("json", "Emit the browser back result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.clipboard.read",
        description="Read browser clipboard text for the active agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to inspect."),
            _bool_arg("json", "Emit the browser clipboard read result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.clipboard.write",
        description="Write text to the browser clipboard for the active session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("text", "Text to write to the browser clipboard.", required=True),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser clipboard write result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.clipboard.copy",
        description="Copy the current browser selection through agent-browser.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser clipboard copy result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.clipboard.paste",
        description="Paste browser clipboard text into the focused browser element.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser clipboard paste result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.forward",
        description="Navigate the active browser page forward in history.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name for the page."),
            _bool_arg("json", "Emit the browser forward result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.reload",
        description="Reload the active browser page.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name for the page."),
            _bool_arg("json", "Emit the browser reload result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.close",
        description="Close the agent-browser session, or all sessions when requested.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("session", "agent-browser session name to close."),
            _str_arg("targetId", "Tab target/index to close instead of the session."),
            _bool_arg("all", "Close all active agent-browser sessions."),
            _bool_arg("json", "Emit the browser close result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.confirm",
        description="Approve one pending browser action by id.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("id", "Pending browser action id to approve.", required=True),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser confirmation result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.deny",
        description="Deny one pending browser action by id.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("id", "Pending browser action id to deny.", required=True),
            _str_arg("session", "agent-browser session name to update."),
            _bool_arg("json", "Emit the browser denial result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.focus",
        description="Focus a browser tab target/index in the agent-browser session.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("targetId", "Tab target/index to focus.", required=True),
            _str_arg("session", "agent-browser session name for the tab."),
            _bool_arg("json", "Emit the browser focus result as JSON."),
        ),
    ),
    GatewayCommandSpec(
        name="browser.act",
        description="Run a bounded browser action such as wait, click, type, or evaluate.",
        category="browser",
        accepts_args=True,
        args=(
            _str_arg("kind", "Action kind to run, such as wait, click, type, or evaluate."),
            _str_arg("session", "agent-browser session name for the action."),
            _bool_arg("json", "Emit the browser action result as JSON."),
        ),
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
