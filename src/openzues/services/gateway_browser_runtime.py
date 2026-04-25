from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

DEFAULT_BROWSER_SESSION = "openzues-browser"
_BROWSER_SNAPSHOT_CHAR_LIMIT = 24_000
_BROWSER_SNAPSHOT_LINE_LIMIT = 240


class GatewayBrowserRuntimeError(RuntimeError):
    pass


class GatewayBrowserRuntimeService:
    def __init__(self, *, command: str | None = None) -> None:
        self._command = command

    def _resolve_command(self) -> str:
        command = self._command or shutil.which("agent-browser.cmd") or shutil.which(
            "agent-browser"
        )
        if command is None:
            raise GatewayBrowserRuntimeError("agent-browser is not installed or not on PATH")
        return command

    def _run(
        self,
        args: list[str],
        *,
        session: str,
        timeout_seconds: float,
        allow_failure: bool = False,
    ) -> str:
        invocation = [self._resolve_command(), "--session", session, *args]
        try:
            completed = subprocess.run(
                invocation,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except OSError as exc:
            raise GatewayBrowserRuntimeError(
                f"agent-browser {' '.join(args)} failed to start: {exc}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GatewayBrowserRuntimeError(
                f"agent-browser {' '.join(args)} timed out after {timeout_seconds:.0f}s"
            ) from exc
        output = (completed.stdout or "").strip()
        error_output = (completed.stderr or "").strip()
        if completed.returncode != 0:
            if allow_failure:
                return output or error_output
            detail = error_output or output or "browser command failed"
            raise GatewayBrowserRuntimeError(
                f"agent-browser {' '.join(args)} failed: {detail}"
            )
        return output or error_output

    def open_page(self, target: str, *, session: str) -> dict[str, object]:
        output = self._run(["tab", "new", target], session=session, timeout_seconds=15.0)
        target_id = browser_tab_target_id(output)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser tab opened",
            "summary": f"Opened {target} in a new agent-browser tab for session {session}.",
            "url": target,
            "session": session,
            "targetId": target_id or None,
            "output": output,
        }

    def start(self, *, session: str) -> dict[str, object]:
        output = self._run(["open", "about:blank"], session=session, timeout_seconds=10.0)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser session started",
            "summary": f"Started agent-browser session {session}.",
            "session": session,
            "output": output,
        }

    def stop(self, *, session: str, all_sessions: bool = False) -> dict[str, object]:
        args = ["close"]
        if all_sessions:
            args.append("--all")
        output = self._run(args, session=session, timeout_seconds=6.0)
        target = "all browser sessions" if all_sessions else f"browser session {session}"
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser session stopped",
            "summary": f"Stopped {target}.",
            "session": session,
            "allSessions": all_sessions,
            "output": output,
        }

    def navigate(self, target: str, *, session: str) -> dict[str, object]:
        self._run(["open", target], session=session, timeout_seconds=15.0)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser navigated",
            "summary": f"Navigated active browser session {session} to {target}.",
            "url": target,
            "session": session,
        }

    def history(self, action: str, *, session: str) -> dict[str, object]:
        if action not in {"back", "forward", "reload"}:
            raise ValueError(f"unsupported browser history action: {action}")
        output = self._run([action], session=session, timeout_seconds=8.0)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser navigation completed",
            "summary": f"Ran browser {action} in session {session}.",
            "session": session,
            "action": action,
            "output": output,
        }

    def close(
        self,
        *,
        session: str,
        all_sessions: bool = False,
        target_id: str | None = None,
    ) -> dict[str, object]:
        if target_id:
            output = self._run(["tab", "close", target_id], session=session, timeout_seconds=6.0)
            return {
                "ok": True,
                "status": "ready",
                "headline": "Browser tab closed",
                "summary": f"Closed browser tab {target_id} in session {session}.",
                "session": session,
                "targetId": target_id,
                "allSessions": False,
                "output": output,
            }
        args = ["close"]
        if all_sessions:
            args.append("--all")
        output = self._run(args, session=session, timeout_seconds=6.0)
        target = "all browser sessions" if all_sessions else f"browser session {session}"
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser closed",
            "summary": f"Closed {target}.",
            "session": session,
            "allSessions": all_sessions,
            "targetId": None,
            "output": output,
        }

    def focus(self, target_id: str, *, session: str) -> dict[str, object]:
        output = self._run(["tab", target_id], session=session, timeout_seconds=6.0)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser tab focused",
            "summary": f"Focused browser tab {target_id} in session {session}.",
            "session": session,
            "targetId": target_id,
            "output": output,
        }

    def act(self, request: dict[str, Any], *, session: str) -> dict[str, object]:
        kind = browser_act_kind(request)
        args = browser_act_args(kind, request)
        output = self._run(args, session=session, timeout_seconds=10.0)
        lines = browser_output_lines(output)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser action completed",
            "summary": f"Ran browser action {kind} for session {session}.",
            "session": session,
            "kind": kind,
            "output": output,
            "lines": lines,
        }

    def snapshot(self, *, session: str) -> dict[str, object]:
        output = self._run(["snapshot", "-i"], session=session, timeout_seconds=6.0)
        summary = summarize_browser_snapshot(output)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser snapshot captured",
            "summary": summary,
            "session": session,
            "snapshotSummary": summary,
            "snapshotOutput": output,
        }

    def console(self, *, session: str) -> dict[str, object]:
        output = self._run(["console"], session=session, timeout_seconds=5.0)
        return browser_stream_payload(label="console", session=session, output=output)

    def errors(self, *, session: str) -> dict[str, object]:
        output = self._run(["errors"], session=session, timeout_seconds=5.0)
        return browser_stream_payload(label="error", session=session, output=output)

    def profiles(self, *, session: str) -> dict[str, object]:
        output = self._run(["profiles"], session=session, timeout_seconds=5.0)
        return browser_profiles_payload(session=session, output=output)

    def get(
        self,
        what: str,
        *,
        session: str,
        selector: str | None = None,
    ) -> dict[str, object]:
        args = ["get", what]
        if selector is not None:
            args.append(selector)
        output = self._run(args, session=session, timeout_seconds=5.0)
        lines = browser_output_lines(output)
        value = strip_browser_value(output)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser value captured",
            "summary": f"Captured browser {what} value from session {session}.",
            "session": session,
            "what": what,
            "selector": selector,
            "value": value,
            "lines": lines,
        }

    def is_state(self, state: str, selector: str, *, session: str) -> dict[str, object]:
        output = self._run(["is", state, selector], session=session, timeout_seconds=5.0)
        lines = browser_output_lines(output)
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser state checked",
            "summary": f"Checked browser {state} state for {selector} in session {session}.",
            "session": session,
            "state": state,
            "selector": selector,
            "matched": browser_bool_value(output),
            "value": strip_browser_value(output),
            "lines": lines,
        }

    def stream_status(self, *, session: str) -> dict[str, object]:
        output = self._run(["stream", "status"], session=session, timeout_seconds=5.0)
        return browser_stream_status_payload(session=session, output=output)

    def stream_enable(self, *, session: str, port: int | None = None) -> dict[str, object]:
        args = ["stream", "enable"]
        if port is not None:
            args.extend(["--port", str(port)])
        output = self._run(args, session=session, timeout_seconds=5.0)
        return browser_stream_status_payload(session=session, output=output)

    def stream_disable(self, *, session: str) -> dict[str, object]:
        output = self._run(["stream", "disable"], session=session, timeout_seconds=5.0)
        return browser_stream_status_payload(session=session, output=output)

    def network_requests(
        self,
        *,
        session: str,
        filter_pattern: str | None = None,
        resource_type: str | None = None,
        method: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        args = ["network", "requests"]
        if filter_pattern is not None:
            args.extend(["--filter", filter_pattern])
        if resource_type is not None:
            args.extend(["--type", resource_type])
        if method is not None:
            args.extend(["--method", method])
        if status is not None:
            args.extend(["--status", status])
        output = self._run(args, session=session, timeout_seconds=5.0)
        return browser_network_requests_payload(
            session=session,
            output=output,
            filter_pattern=filter_pattern,
            resource_type=resource_type,
            method=method,
            status=status,
        )

    def network_request(self, request_id: str, *, session: str) -> dict[str, object]:
        output = self._run(
            ["network", "request", request_id],
            session=session,
            timeout_seconds=5.0,
        )
        return browser_network_request_payload(
            session=session,
            request_id=request_id,
            output=output,
        )

    def cookies_get(self, *, session: str) -> dict[str, object]:
        output = self._run(["cookies", "get"], session=session, timeout_seconds=5.0)
        return browser_cookies_payload(session=session, output=output)

    def storage_get(
        self,
        storage_type: str,
        *,
        session: str,
        key: str | None = None,
    ) -> dict[str, object]:
        args = ["storage", storage_type, "get"]
        if key is not None:
            args.append(key)
        output = self._run(args, session=session, timeout_seconds=5.0)
        return browser_storage_payload(
            session=session,
            storage_type=storage_type,
            key=key,
            output=output,
        )

    def session_current(self, *, session: str) -> dict[str, object]:
        output = self._run(["session"], session=session, timeout_seconds=5.0)
        return browser_session_current_payload(session=session, output=output)

    def session_list(self, *, session: str) -> dict[str, object]:
        output = self._run(["session", "list"], session=session, timeout_seconds=5.0)
        return browser_session_list_payload(session=session, output=output)

    def diff_snapshot(
        self,
        *,
        session: str,
        selector: str | None = None,
        compact: bool = False,
        depth: int | None = None,
    ) -> dict[str, object]:
        args = ["diff", "snapshot"]
        if selector is not None:
            args.extend(["--selector", selector])
        if compact:
            args.append("--compact")
        if depth is not None:
            args.extend(["--depth", str(depth)])
        output = self._run(args, session=session, timeout_seconds=8.0)
        return browser_diff_snapshot_payload(
            session=session,
            output=output,
            selector=selector,
            compact=compact,
            depth=depth,
        )

    def diff_url(
        self,
        url1: str,
        url2: str,
        *,
        session: str,
        screenshot: bool = False,
        full_page: bool = False,
        wait_until: str | None = None,
        selector: str | None = None,
        compact: bool = False,
        depth: int | None = None,
    ) -> dict[str, object]:
        args = ["diff", "url", url1, url2]
        if screenshot:
            args.append("--screenshot")
        if full_page:
            args.append("--full")
        if wait_until is not None:
            args.extend(["--wait-until", wait_until])
        if selector is not None:
            args.extend(["--selector", selector])
        if compact:
            args.append("--compact")
        if depth is not None:
            args.extend(["--depth", str(depth)])
        output = self._run(args, session=session, timeout_seconds=15.0)
        return browser_diff_url_payload(
            session=session,
            url1=url1,
            url2=url2,
            output=output,
            screenshot=screenshot,
            full_page=full_page,
            wait_until=wait_until,
            selector=selector,
            compact=compact,
            depth=depth,
        )

    def diff_screenshot(
        self,
        *,
        session: str,
        baseline_path: str,
        threshold: float | None = None,
        selector: str | None = None,
        full_page: bool = False,
    ) -> dict[str, object]:
        baseline = browser_diff_screenshot_baseline_path(baseline_path)
        output_path = browser_diff_screenshot_target_path(session)
        args = [
            "diff",
            "screenshot",
            "--baseline",
            str(baseline),
            "--output",
            str(output_path),
        ]
        if threshold is not None:
            args.extend(["--threshold", str(threshold)])
        if selector is not None:
            args.extend(["--selector", selector])
        if full_page:
            args.append("--full")
        output = self._run(args, session=session, timeout_seconds=12.0)
        resolved_path = browser_screenshot_path(output) or str(output_path)
        saved_path = Path(resolved_path)
        size_bytes = saved_path.stat().st_size if saved_path.exists() else None
        return browser_diff_screenshot_payload(
            session=session,
            baseline_path=str(baseline),
            path=resolved_path,
            size_bytes=size_bytes,
            output=output,
            threshold=threshold,
            selector=selector,
            full_page=full_page,
        )

    def download(
        self,
        selector: str,
        *,
        session: str,
        filename_hint: str | None = None,
    ) -> dict[str, object]:
        download_path = browser_download_target_path(session, filename_hint=filename_hint)
        output = self._run(
            ["download", selector, str(download_path)],
            session=session,
            timeout_seconds=30.0,
        )
        saved_path = Path(download_path)
        size_bytes = saved_path.stat().st_size if saved_path.exists() else None
        return browser_download_payload(
            session=session,
            selector=selector,
            filename_hint=filename_hint,
            path=str(download_path),
            size_bytes=size_bytes,
            output=output,
        )

    def upload(
        self,
        selector: str,
        file_paths: list[str],
        *,
        session: str,
    ) -> dict[str, object]:
        guarded_paths = [
            browser_controlled_temp_artifact_path(path, label="upload file")
            for path in file_paths
        ]
        output = self._run(
            ["upload", selector, *(str(path) for path in guarded_paths)],
            session=session,
            timeout_seconds=20.0,
        )
        return browser_upload_payload(
            session=session,
            selector=selector,
            files=[str(path) for path in guarded_paths],
            output=output,
        )

    def auth_list(self, *, session: str) -> dict[str, object]:
        output = self._run(["auth", "list"], session=session, timeout_seconds=5.0)
        return browser_auth_list_payload(session=session, output=output)

    def auth_show(self, name: str, *, session: str) -> dict[str, object]:
        output = self._run(["auth", "show", name], session=session, timeout_seconds=5.0)
        return browser_auth_show_payload(session=session, name=name, output=output)

    def tabs(self, *, session: str) -> dict[str, object]:
        output = self._run(["tab", "list"], session=session, timeout_seconds=5.0)
        return browser_tabs_payload(session=session, output=output)

    def screenshot(self, *, session: str, full_page: bool = False) -> dict[str, object]:
        screenshot_path = browser_screenshot_target_path(session)
        args = ["screenshot"]
        if full_page:
            args.append("--full")
        args.append(str(screenshot_path))
        output = self._run(args, session=session, timeout_seconds=8.0)
        resolved_path = browser_screenshot_path(output) or str(screenshot_path)
        saved_path = Path(resolved_path)
        size_bytes = saved_path.stat().st_size if saved_path.exists() else None
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser screenshot captured",
            "summary": f"Captured browser screenshot for session {session}.",
            "session": session,
            "path": resolved_path,
            "fullPage": full_page,
            "sizeBytes": size_bytes,
            "output": output,
        }

    def pdf(self, *, session: str) -> dict[str, object]:
        pdf_path = browser_pdf_target_path(session)
        output = self._run(["pdf", str(pdf_path)], session=session, timeout_seconds=8.0)
        resolved_path = browser_pdf_path(output) or str(pdf_path)
        saved_path = Path(resolved_path)
        size_bytes = saved_path.stat().st_size if saved_path.exists() else None
        return {
            "ok": True,
            "status": "ready",
            "headline": "Browser PDF captured",
            "summary": f"Captured browser PDF for session {session}.",
            "session": session,
            "path": resolved_path,
            "sizeBytes": size_bytes,
            "output": output,
        }

    def verify(self, target: str, *, session: str) -> dict[str, object]:
        self._run(["open", target], session=session, timeout_seconds=15.0)
        self._run(
            ["wait", "2000"],
            session=session,
            timeout_seconds=5.0,
            allow_failure=True,
        )
        page_url = browser_url_value(
            self._run(
                ["get", "url"],
                session=session,
                timeout_seconds=3.0,
                allow_failure=True,
            )
        )
        title = browser_title_value(
            self._run(
                ["get", "title"],
                session=session,
                timeout_seconds=3.0,
                allow_failure=True,
            )
        )
        has_content = browser_probe_status(
            self._run(
                [
                    "eval",
                    (
                        "document.body && document.body.innerText.trim().length > 0 "
                        "? 'HAS_CONTENT' : 'BLANK'"
                    ),
                ],
                session=session,
                timeout_seconds=3.0,
                allow_failure=True,
            ),
            allowed={"HAS_CONTENT", "BLANK"},
        )
        overlay_status = browser_probe_status(
            self._run(
                [
                    "eval",
                    (
                        "document.querySelector('[data-nextjs-dialog], "
                        ".vite-error-overlay, #webpack-dev-server-client-overlay') "
                        "? 'ERROR_OVERLAY' : 'OK'"
                    ),
                ],
                session=session,
                timeout_seconds=3.0,
                allow_failure=True,
            ),
            allowed={"OK", "ERROR_OVERLAY"},
        )
        snapshot_output = self._run(
            ["snapshot", "-i"],
            session=session,
            timeout_seconds=4.0,
            allow_failure=True,
        )
        errors_output = self._run(
            ["errors"],
            session=session,
            timeout_seconds=3.0,
            allow_failure=True,
        )
        console_output = self._run(
            ["console"],
            session=session,
            timeout_seconds=3.0,
            allow_failure=True,
        )
        error_count = len(browser_output_lines(errors_output))
        console_count = len(browser_output_lines(console_output))
        content_visible = has_content == "HAS_CONTENT"
        overlay_ok = overlay_status in {"", "OK"}
        ok = content_visible and overlay_ok and error_count == 0
        content_summary = "content visible" if content_visible else "page looks blank"
        overlay_summary = "no overlay" if overlay_ok else "error overlay present"
        summary = (
            f"url {page_url or target}, {content_summary}, {overlay_summary}, "
            f"{error_count} page error(s), {console_count} console line(s)."
        )
        return {
            "ok": ok,
            "status": "ready" if ok else "warn",
            "summary": summary,
            "url": page_url or target,
            "title": title or None,
            "session": session,
            "has_content": content_visible,
            "overlay_status": overlay_status or "unknown",
            "error_count": error_count,
            "console_count": console_count,
            "snapshot_summary": summarize_browser_snapshot(snapshot_output),
            "errors_excerpt": first_browser_output_line(errors_output) or None,
            "console_excerpt": first_browser_output_line(console_output) or None,
        }


def browser_stream_payload(*, label: str, session: str, output: str) -> dict[str, object]:
    lines = browser_output_lines(output)
    return {
        "ok": True,
        "status": "ready",
        "headline": f"Browser {label} captured",
        "summary": f"Captured {len(lines)} {label} line(s) from session {session}.",
        "session": session,
        "lineCount": len(lines),
        "lines": lines,
    }


def browser_tabs_payload(*, session: str, output: str) -> dict[str, object]:
    tabs: list[object] = []
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        raw_tabs = parsed.get("tabs")
        if isinstance(raw_tabs, list):
            tabs = raw_tabs
    elif isinstance(parsed, list):
        tabs = parsed
    lines = browser_output_lines(output)
    tab_count = len(tabs) if tabs else len(lines)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser tabs captured",
        "summary": f"Captured {tab_count} browser tab(s) from session {session}.",
        "session": session,
        "tabCount": tab_count,
        "tabs": tabs,
        "lines": lines,
    }


def browser_profiles_payload(*, session: str, output: str) -> dict[str, object]:
    profiles: list[object] = []
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        raw_profiles = parsed.get("profiles")
        if isinstance(raw_profiles, list):
            profiles = raw_profiles
    elif isinstance(parsed, list):
        profiles = parsed
    lines = browser_output_lines(output)
    profile_count = len(profiles) if profiles else len(lines)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser profiles captured",
        "summary": f"Captured {profile_count} browser profile(s) from session {session}.",
        "session": session,
        "profileCount": profile_count,
        "profiles": profiles,
        "lines": lines,
    }


def browser_stream_status_payload(*, session: str, output: str) -> dict[str, object]:
    lines = browser_output_lines(output)
    status_text = first_browser_output_line(output) or "unknown"
    streaming: bool | None = None
    port: int | None = None
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        streaming = browser_json_bool(parsed, "streaming", "enabled", "active")
        port = browser_json_int(parsed, "port")
        raw_status = parsed.get("status") or parsed.get("state")
        if isinstance(raw_status, str) and raw_status.strip():
            status_text = raw_status.strip()
    elif status_text.lower() in {"enabled", "active", "streaming", "on"}:
        streaming = True
    elif status_text.lower() in {"disabled", "inactive", "stopped", "off"}:
        streaming = False
    if port is None:
        port = browser_stream_port(output)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser stream status captured",
        "summary": f"Captured browser stream status for session {session}: {status_text}.",
        "session": session,
        "statusText": status_text,
        "streaming": streaming,
        "port": port,
        "lines": lines,
    }


def browser_network_requests_payload(
    *,
    session: str,
    output: str,
    filter_pattern: str | None,
    resource_type: str | None,
    method: str | None,
    status: str | None,
) -> dict[str, object]:
    requests: list[object] = []
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        raw_requests = parsed.get("requests")
        if isinstance(raw_requests, list):
            requests = raw_requests
    elif isinstance(parsed, list):
        requests = parsed
    lines = browser_output_lines(output)
    request_count = len(requests) if requests else len(lines)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser network requests captured",
        "summary": f"Captured {request_count} browser network request(s).",
        "session": session,
        "filter": filter_pattern,
        "type": resource_type,
        "method": method,
        "statusFilter": status,
        "requestCount": request_count,
        "requests": requests,
        "lines": lines,
    }


def browser_network_request_payload(
    *,
    session: str,
    request_id: str,
    output: str,
) -> dict[str, object]:
    detail: object | None = None
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        detail = parsed
    lines = browser_output_lines(output)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser network request captured",
        "summary": f"Captured browser network request {request_id}.",
        "session": session,
        "requestId": request_id,
        "detail": detail,
        "lines": lines,
    }


def browser_cookies_payload(*, session: str, output: str) -> dict[str, object]:
    cookies: list[object] = []
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        raw_cookies = parsed.get("cookies")
        if isinstance(raw_cookies, list):
            cookies = raw_cookies
    elif isinstance(parsed, list):
        cookies = parsed
    lines = browser_output_lines(output)
    cookie_count = len(cookies) if cookies else len(lines)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser cookies captured",
        "summary": f"Captured {cookie_count} browser cookie(s).",
        "session": session,
        "cookieCount": cookie_count,
        "cookies": cookies,
        "lines": lines,
    }


def browser_storage_payload(
    *,
    session: str,
    storage_type: str,
    key: str | None,
    output: str,
) -> dict[str, object]:
    entries: object | None = None
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict | list):
        entries = parsed
    lines = browser_output_lines(output)
    entry_count = len(entries) if isinstance(entries, dict | list) else len(lines)
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser storage captured",
        "summary": f"Captured {storage_type}Storage from session {session}.",
        "session": session,
        "type": storage_type,
        "key": key,
        "entryCount": entry_count,
        "entries": entries,
        "lines": lines,
    }


def browser_session_current_payload(*, session: str, output: str) -> dict[str, object]:
    current_session = strip_browser_value(first_browser_output_line(output)) or session
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser session captured",
        "summary": f"Current browser session is {current_session}.",
        "session": session,
        "currentSession": current_session,
        "lines": browser_output_lines(output),
    }


def browser_session_list_payload(*, session: str, output: str) -> dict[str, object]:
    sessions: list[Any] = []
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        raw_sessions = parsed.get("sessions")
        if isinstance(raw_sessions, list):
            sessions = raw_sessions
    elif isinstance(parsed, list):
        sessions = parsed
    lines = browser_output_lines(output)
    if not sessions:
        sessions = lines
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser sessions captured",
        "summary": f"Captured {len(sessions)} browser session(s).",
        "session": session,
        "sessionCount": len(sessions),
        "sessions": sessions,
        "lines": lines,
    }


def browser_diff_snapshot_payload(
    *,
    session: str,
    output: str,
    selector: str | None,
    compact: bool,
    depth: int | None,
) -> dict[str, object]:
    lines = browser_output_lines(output)
    summary = first_browser_output_line(output) or "No browser snapshot diff was returned."
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser snapshot diff captured",
        "summary": summary,
        "session": session,
        "selector": selector,
        "compact": compact,
        "depth": depth,
        "diffSummary": summary,
        "lineCount": len(lines),
        "lines": lines,
    }


def browser_diff_url_payload(
    *,
    session: str,
    url1: str,
    url2: str,
    output: str,
    screenshot: bool,
    full_page: bool,
    wait_until: str | None,
    selector: str | None,
    compact: bool,
    depth: int | None,
) -> dict[str, object]:
    lines = browser_output_lines(output)
    summary = first_browser_output_line(output) or "No browser URL diff was returned."
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser URL diff captured",
        "summary": summary,
        "session": session,
        "url1": url1,
        "url2": url2,
        "screenshot": screenshot,
        "fullPage": full_page,
        "waitUntil": wait_until,
        "selector": selector,
        "compact": compact,
        "depth": depth,
        "diffSummary": summary,
        "lineCount": len(lines),
        "lines": lines,
    }


def browser_diff_screenshot_payload(
    *,
    session: str,
    baseline_path: str,
    path: str,
    size_bytes: int | None,
    output: str,
    threshold: float | None,
    selector: str | None,
    full_page: bool,
) -> dict[str, object]:
    lines = browser_output_lines(output)
    summary = first_browser_output_line(output) or "Browser screenshot diff captured."
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser screenshot diff captured",
        "summary": summary,
        "session": session,
        "baselinePath": baseline_path,
        "path": path,
        "sizeBytes": size_bytes,
        "threshold": threshold,
        "selector": selector,
        "fullPage": full_page,
        "diffSummary": summary,
        "lineCount": len(lines),
        "lines": lines,
    }


def browser_download_payload(
    *,
    session: str,
    selector: str,
    filename_hint: str | None,
    path: str,
    size_bytes: int | None,
    output: str,
) -> dict[str, object]:
    lines = browser_output_lines(output)
    summary = first_browser_output_line(output) or "Browser download captured."
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser download captured",
        "summary": summary,
        "session": session,
        "selector": selector,
        "filenameHint": filename_hint,
        "path": path,
        "sizeBytes": size_bytes,
        "lineCount": len(lines),
        "lines": lines,
        "output": output,
    }


def browser_upload_payload(
    *,
    session: str,
    selector: str,
    files: list[str],
    output: str,
) -> dict[str, object]:
    lines = browser_output_lines(output)
    summary = first_browser_output_line(output) or "Browser upload completed."
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser upload completed",
        "summary": summary,
        "session": session,
        "selector": selector,
        "fileCount": len(files),
        "files": files,
        "lineCount": len(lines),
        "lines": lines,
        "output": output,
    }


def browser_auth_list_payload(*, session: str, output: str) -> dict[str, object]:
    profiles: list[Any] = []
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        raw_profiles = parsed.get("profiles")
        if isinstance(raw_profiles, list):
            profiles = raw_profiles
    elif isinstance(parsed, list):
        profiles = parsed
    lines = browser_output_lines(output)
    if not profiles:
        profiles = lines
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser auth profiles captured",
        "summary": f"Captured {len(profiles)} browser auth profile(s).",
        "session": session,
        "profileCount": len(profiles),
        "profiles": profiles,
        "lines": lines,
    }


def browser_auth_show_payload(*, session: str, name: str, output: str) -> dict[str, object]:
    profile: object | None = None
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        profile = parsed
    return {
        "ok": True,
        "status": "ready",
        "headline": "Browser auth profile captured",
        "summary": f"Captured browser auth profile metadata for {name}.",
        "session": session,
        "name": name,
        "profile": profile,
        "lines": browser_output_lines(output),
    }


def browser_screenshot_target_path(session: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", session.strip()).strip(".-")
    safe_session = slug[:48] or DEFAULT_BROWSER_SESSION
    return Path(tempfile.gettempdir()) / f"openzues-browser-{safe_session}-{time.time_ns()}.png"


def browser_diff_screenshot_target_path(session: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", session.strip()).strip(".-")
    safe_session = slug[:48] or DEFAULT_BROWSER_SESSION
    return (
        Path(tempfile.gettempdir())
        / f"openzues-browser-diff-{safe_session}-{time.time_ns()}.png"
    )


def browser_download_target_path(session: str, *, filename_hint: str | None = None) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", session.strip()).strip(".-")
    safe_session = slug[:48] or DEFAULT_BROWSER_SESSION
    raw_filename = Path(filename_hint or "download.bin").name
    safe_filename = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw_filename).strip(".-")
    safe_filename = (safe_filename or "download.bin")[:96]
    return (
        Path(tempfile.gettempdir())
        / f"openzues-browser-download-{safe_session}-{time.time_ns()}-{safe_filename}"
    )


def browser_controlled_temp_artifact_path(path: str, *, label: str) -> Path:
    raw_path = Path(path)
    if not raw_path.is_absolute():
        raise GatewayBrowserRuntimeError(f"{label} must be an OpenZues temp artifact")
    try:
        resolved_path = raw_path.resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    except OSError as exc:
        raise GatewayBrowserRuntimeError(
            f"{label} must be an existing OpenZues temp artifact"
        ) from exc
    if not resolved_path.is_file():
        raise GatewayBrowserRuntimeError(f"{label} must be an OpenZues temp artifact")
    try:
        resolved_path.relative_to(temp_root)
    except ValueError as exc:
        raise GatewayBrowserRuntimeError(f"{label} must be an OpenZues temp artifact") from exc
    if not resolved_path.name.startswith("openzues-browser-"):
        raise GatewayBrowserRuntimeError(f"{label} must be an OpenZues temp artifact")
    return resolved_path


def browser_diff_screenshot_baseline_path(path: str) -> Path:
    raw_path = Path(path)
    if not raw_path.is_absolute():
        raise GatewayBrowserRuntimeError(
            "browser diff baseline must be an OpenZues temp screenshot absolute path"
        )
    try:
        resolved_path = raw_path.resolve(strict=True)
        temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    except OSError as exc:
        raise GatewayBrowserRuntimeError(
            "browser diff baseline must be an existing OpenZues temp screenshot"
        ) from exc
    try:
        resolved_path.relative_to(temp_root)
    except ValueError as exc:
        raise GatewayBrowserRuntimeError(
            "browser diff baseline must be an OpenZues temp screenshot"
        ) from exc
    suffix = resolved_path.suffix.lower()
    if not resolved_path.name.startswith("openzues-browser-") or suffix not in {
        ".jpeg",
        ".jpg",
        ".png",
    }:
        raise GatewayBrowserRuntimeError(
            "browser diff baseline must be an OpenZues temp screenshot"
        )
    return resolved_path


def browser_pdf_target_path(session: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", session.strip()).strip(".-")
    safe_session = slug[:48] or DEFAULT_BROWSER_SESSION
    return Path(tempfile.gettempdir()) / f"openzues-browser-{safe_session}-{time.time_ns()}.pdf"


def browser_screenshot_path(output: str) -> str:
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        for key in ("path", "screenshot", "screenshotPath", "file"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    path_pattern = re.compile(
        r"([A-Za-z]:[\\/][^\r\n\"']+\.(?:png|jpe?g)|/[^\s\"']+\.(?:png|jpe?g))",
        re.IGNORECASE,
    )
    for line in browser_output_lines(output):
        match = path_pattern.search(line)
        if match:
            return match.group(1).strip()
    return ""


def browser_pdf_path(output: str) -> str:
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        for key in ("path", "pdf", "pdfPath", "file"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    path_pattern = re.compile(
        r"([A-Za-z]:[\\/][^\r\n\"']+\.pdf|/[^\s\"']+\.pdf)",
        re.IGNORECASE,
    )
    for line in browser_output_lines(output):
        match = path_pattern.search(line)
        if match:
            return match.group(1).strip()
    return ""


def browser_act_kind(request: dict[str, Any]) -> str:
    value = request.get("kind")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("browser.act request.kind is required")
    return value.strip()


def browser_tab_target_id(output: str) -> str:
    try:
        parsed = json.loads(output) if output else None
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        for key in ("targetId", "id", "tabId"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for line in browser_output_lines(output):
        match = re.search(
            r"\b(?:targetId|tabId|id)\s*[:=]\s*([A-Za-z0-9_.:@-]+)",
            line,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
    return ""


def browser_act_args(kind: str, request: dict[str, Any]) -> list[str]:
    if kind == "wait":
        time_ms = browser_request_int(request, "timeMs")
        selector = browser_request_string(request, "selector", "ref", "targetId")
        if time_ms is not None:
            return ["wait", str(time_ms)]
        if selector:
            return ["wait", selector]
        timeout_ms = browser_request_int(request, "timeoutMs") or 1000
        return ["wait", str(timeout_ms)]
    if kind == "click":
        return ["click", browser_required_selector(request, kind)]
    if kind in {"dblclick", "doubleClick"}:
        return ["dblclick", browser_required_selector(request, kind)]
    if kind == "type":
        text = browser_required_string(request, "text", label="browser.act request.text")
        selector = browser_request_string(request, "selector", "ref", "targetId")
        return ["type", selector, text] if selector else ["keyboard", "type", text]
    if kind == "fill":
        return [
            "fill",
            browser_required_selector(request, kind),
            browser_required_string(request, "text", label="browser.act request.text"),
        ]
    if kind == "press":
        return ["press", browser_required_string(request, "key", label="browser.act request.key")]
    if kind in {"hover", "focus", "check", "uncheck"}:
        return [kind, browser_required_selector(request, kind)]
    if kind == "select":
        values = browser_request_string_list(request, "values", "value")
        if not values:
            raise ValueError("browser.act select requires value or values")
        return ["select", browser_required_selector(request, kind), *values]
    if kind == "scroll":
        direction = browser_required_string(
            request,
            "direction",
            label="browser.act request.direction",
        )
        if direction not in {"up", "down", "left", "right"}:
            raise ValueError("browser.act scroll direction must be up, down, left, or right")
        px = browser_request_int(request, "px")
        return ["scroll", direction, str(px)] if px is not None else ["scroll", direction]
    if kind == "scrollintoview":
        return ["scrollintoview", browser_required_selector(request, kind)]
    if kind == "evaluate":
        return ["eval", browser_required_string(request, "fn", label="browser.act request.fn")]
    if kind == "resize":
        width = browser_request_int(request, "width")
        height = browser_request_int(request, "height")
        if width is None or height is None:
            raise ValueError("browser.act resize requires width and height")
        return ["set", "viewport", str(width), str(height)]
    if kind == "close":
        return ["close"]
    raise ValueError(f"unsupported browser.act kind: {kind}")


def browser_request_string(request: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = request.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def browser_request_string_list(request: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        value = request.get(key)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            values: list[str] = []
            for entry in value:
                if not isinstance(entry, str) or not entry.strip():
                    raise ValueError(f"browser.act request.{key} entries must be strings")
                values.append(entry.strip())
            if values:
                return values
    return []


def browser_required_string(request: dict[str, Any], key: str, *, label: str) -> str:
    value = browser_request_string(request, key)
    if not value:
        raise ValueError(f"{label} is required")
    return value


def browser_required_selector(request: dict[str, Any], kind: str) -> str:
    selector = browser_request_string(request, "ref", "selector", "targetId", "element")
    if not selector:
        raise ValueError(f"browser.act {kind} requires ref, selector, targetId, or element")
    return selector


def browser_request_int(request: dict[str, Any], key: str) -> int | None:
    value = request.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def strip_browser_value(value: str) -> str:
    text = value.strip()
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        return text[1:-1]
    return text


def browser_bool_value(value: str) -> bool | None:
    text = strip_browser_value(value).strip().lower()
    if text in {"true", "1", "yes", "visible", "enabled", "checked"}:
        return True
    if text in {"false", "0", "no", "hidden", "disabled", "unchecked"}:
        return False
    return None


def browser_url_value(value: str) -> str:
    text = strip_browser_value(value)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return text
    return ""


def browser_title_value(value: str) -> str:
    text = strip_browser_value(value)
    if not text or "\x00" in text or "HRESULT" in text or "failed" in text.lower():
        return ""
    return text


def browser_probe_status(value: str, *, allowed: set[str]) -> str:
    text = strip_browser_value(value)
    return text if text in allowed else ""


def browser_json_bool(payload: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "enabled", "active", "streaming", "on"}:
                return True
            if lowered in {"false", "0", "no", "disabled", "inactive", "stopped", "off"}:
                return False
    return None


def browser_json_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def browser_stream_port(output: str) -> int | None:
    for line in browser_output_lines(output):
        match = re.search(r"\bport\s*[:=]\s*(\d{1,5})\b", line, re.IGNORECASE)
        if not match:
            continue
        port = int(match.group(1))
        if 1 <= port <= 65_535:
            return port
    return None


def browser_output_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def first_browser_output_line(output: str, *, limit: int = 280) -> str:
    for line in browser_output_lines(output):
        return line[:limit]
    return ""


def summarize_browser_snapshot(output: str, *, limit: int = 8) -> str:
    truncated_output = output[:_BROWSER_SNAPSHOT_CHAR_LIMIT]
    lines: list[str] = []
    for raw_line in truncated_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lines.append(line)
        if len(lines) >= _BROWSER_SNAPSHOT_LINE_LIMIT:
            break
    if not lines:
        return "No interactive browser snapshot lines were returned."
    interesting = [
        line
        for line in lines
        if line.startswith("- ")
        or line.startswith("[")
        or 'heading "' in line
        or 'button "' in line
        or 'textbox "' in line
    ]
    sample = interesting[:limit] if interesting else lines[:limit]
    summary = " | ".join(sample)
    if len(output) > len(truncated_output) or len(lines) >= _BROWSER_SNAPSHOT_LINE_LIMIT:
        summary += " | [snapshot truncated]"
    return summary
