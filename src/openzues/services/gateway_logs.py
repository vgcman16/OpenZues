from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

DEFAULT_LIMIT = 500
DEFAULT_MAX_BYTES = 250_000
MAX_LIMIT = 5_000
MAX_BYTES = 1_000_000
_PREFERRED_LOG_PATTERNS: tuple[tuple[int, re.Pattern[str]], ...] = (
    (0, re.compile(r"^openzues-\d{4}-\d{2}-\d{2}\.log$", re.IGNORECASE)),
    (
        1,
        re.compile(r"^openzues(?:-[A-Za-z0-9_-]+)*\.out\.log$", re.IGNORECASE),
    ),
    (
        2,
        re.compile(r"^server(?:-[A-Za-z0-9_-]+)*\.out\.log$", re.IGNORECASE),
    ),
    (
        3,
        re.compile(r"^openzues(?:-[A-Za-z0-9_-]+)*\.err\.log$", re.IGNORECASE),
    ),
    (
        4,
        re.compile(r"^server(?:-[A-Za-z0-9_-]+)*\.err\.log$", re.IGNORECASE),
    ),
    (5, re.compile(r"^openzues(?:-[A-Za-z0-9_-]+)*\.log$", re.IGNORECASE)),
    (6, re.compile(r"^server(?:-[A-Za-z0-9_-]+)*\.log$", re.IGNORECASE)),
)
_CLI_SECRET_RE = re.compile(
    r'(?P<prefix>--(?:api[-_]?key|hook[-_]?token|token|secret|password|passwd)\s+)'
    r'(?P<quote>["\']?)(?P<secret>[^\s"\']+)(?P=quote)',
    re.IGNORECASE,
)
_JSON_SECRET_RE = re.compile(
    r'(?P<prefix>"(?:apiKey|token|secret|password|passwd|accessToken|refreshToken)"\s*:\s*")'
    r'(?P<secret>[^"]+)(?P<suffix>")',
    re.IGNORECASE,
)
_ENV_SECRET_RE = re.compile(
    r'(?P<prefix>\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)\b\s*[=:]\s*(?:["\']?))'
    r'(?P<secret>[^\s"\'\\]+)',
    re.IGNORECASE,
)
_BEARER_TOKEN_RE = re.compile(
    r"(?P<prefix>\b(?:Authorization\s*[:=]\s*)?Bearer\s+)(?P<secret>[A-Za-z0-9._\-+=]+)",
    re.IGNORECASE,
)
_COMMON_TOKEN_RE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"xapp-[A-Za-z0-9-]{10,}|gsk_[A-Za-z0-9_-]{10,}|"
    r"AIza[0-9A-Za-z\-_]{20,}|pplx-[A-Za-z0-9_-]{10,}|"
    r"npm_[A-Za-z0-9]{10,})\b"
)


class GatewayLogsUnavailableError(RuntimeError):
    pass


class _LogSlicePayload(TypedDict):
    cursor: int
    size: int
    lines: list[str]
    truncated: bool
    reset: bool


class GatewayLogsService:
    def __init__(self, *, logs_root: Path | str | None = None) -> None:
        self._logs_root = Path(logs_root) if logs_root is not None else Path.cwd() / "logs"

    async def read_tail(
        self,
        *,
        cursor: int | None = None,
        limit: int | None = None,
        max_bytes: int | None = None,
    ) -> dict[str, object]:
        log_file = self._resolve_latest_log_file()
        resolved_limit = _clamp(limit or DEFAULT_LIMIT, minimum=1, maximum=MAX_LIMIT)
        resolved_max_bytes = _clamp(
            max_bytes or DEFAULT_MAX_BYTES,
            minimum=1,
            maximum=MAX_BYTES,
        )
        slice_payload = self._read_log_slice(
            log_file,
            cursor=cursor,
            limit=resolved_limit,
            max_bytes=resolved_max_bytes,
        )
        return {
            "file": str(log_file),
            "cursor": slice_payload["cursor"],
            "size": slice_payload["size"],
            "lines": [_redact_sensitive_tokens(line) for line in slice_payload["lines"]],
            "truncated": slice_payload["truncated"],
            "reset": slice_payload["reset"],
        }

    def _resolve_latest_log_file(self) -> Path:
        try:
            candidates: list[tuple[Path, int]] = []
            for path in self._logs_root.rglob("*.log"):
                try:
                    if not path.is_file():
                        continue
                    candidates.append((path, path.stat().st_mtime_ns))
                except OSError:
                    continue
        except OSError as exc:
            raise GatewayLogsUnavailableError(f"log read failed: {exc}") from exc
        if not candidates:
            raise GatewayLogsUnavailableError("log read failed: no workspace log files available")
        return min(
            candidates,
            key=lambda item: (
                _log_candidate_priority(item[0]),
                -item[1],
                item[0].name.lower(),
                str(item[0]).lower(),
            ),
        )[0]

    def _read_log_slice(
        self,
        file_path: Path,
        *,
        cursor: int | None,
        limit: int,
        max_bytes: int,
    ) -> _LogSlicePayload:
        try:
            size = file_path.stat().st_size
        except OSError as exc:
            raise GatewayLogsUnavailableError(f"log read failed: {exc}") from exc

        resolved_cursor = cursor if isinstance(cursor, int) and cursor >= 0 else None
        reset = False
        truncated = False
        start = 0

        if resolved_cursor is not None:
            if resolved_cursor > size:
                reset = True
                start = max(0, size - max_bytes)
                truncated = start > 0
            else:
                start = resolved_cursor
                if size - start > max_bytes:
                    reset = True
                    truncated = True
                    start = max(0, size - max_bytes)
        else:
            start = max(0, size - max_bytes)
            truncated = start > 0

        if size == 0 or size <= start:
            return {
                "cursor": size,
                "size": size,
                "lines": [],
                "truncated": truncated,
                "reset": reset,
            }

        try:
            with file_path.open("rb") as handle:
                prefix = b""
                if start > 0:
                    handle.seek(start - 1)
                    prefix = handle.read(1)
                handle.seek(start)
                payload = handle.read(size - start)
        except OSError as exc:
            raise GatewayLogsUnavailableError(f"log read failed: {exc}") from exc

        text = payload.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if start > 0 and prefix != b"\n":
            lines = lines[1:]
        if len(lines) > limit:
            lines = lines[-limit:]

        return {
            "cursor": size,
            "size": size,
            "lines": lines,
            "truncated": truncated,
            "reset": reset,
        }


def _clamp(value: int, *, minimum: int, maximum: int) -> int:
    return min(max(value, minimum), maximum)


def _log_candidate_priority(path: Path) -> int:
    name = path.name
    for priority, pattern in _PREFERRED_LOG_PATTERNS:
        if pattern.fullmatch(name):
            return priority
    return len(_PREFERRED_LOG_PATTERNS)


def _redact_sensitive_tokens(text: str) -> str:
    redacted = _CLI_SECRET_RE.sub(_replace_cli_secret, text)
    redacted = _JSON_SECRET_RE.sub(_replace_json_secret, redacted)
    redacted = _ENV_SECRET_RE.sub(_replace_env_secret, redacted)
    redacted = _BEARER_TOKEN_RE.sub(_replace_bearer_secret, redacted)
    return _COMMON_TOKEN_RE.sub(lambda match: _shorten_secret(match.group(0)), redacted)


def _replace_cli_secret(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    quote = match.group("quote") or ""
    secret = match.group("secret")
    return f"{prefix}{quote}{_shorten_secret(secret)}{quote}"


def _replace_json_secret(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    secret = match.group("secret")
    suffix = match.group("suffix")
    return f"{prefix}{_shorten_secret(secret)}{suffix}"


def _replace_env_secret(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    secret = match.group("secret")
    return f"{prefix}{_shorten_secret(secret)}"


def _replace_bearer_secret(match: re.Match[str]) -> str:
    prefix = match.group("prefix")
    secret = match.group("secret")
    return f"{prefix}{_shorten_secret(secret)}"


def _shorten_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "********"
    return f"{secret[:6]}...{secret[-4:]}"
