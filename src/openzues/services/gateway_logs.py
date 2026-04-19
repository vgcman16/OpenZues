from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

DEFAULT_LIMIT = 500
DEFAULT_MAX_BYTES = 250_000
MAX_LIMIT = 5_000
MAX_BYTES = 1_000_000
_TOKEN_FLAG_RE = re.compile(r"(?P<flag>--(?:hook-)?token)\s+(?P<secret>\S+)")


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
            candidates = [path for path in self._logs_root.rglob("*.log") if path.is_file()]
        except OSError as exc:
            raise GatewayLogsUnavailableError(f"log read failed: {exc}") from exc
        if not candidates:
            raise GatewayLogsUnavailableError("log read failed: no workspace log files available")
        return max(candidates, key=lambda path: path.stat().st_mtime_ns)

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


def _redact_sensitive_tokens(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        flag = match.group("flag")
        secret = match.group("secret")
        return f"{flag} {_shorten_secret(secret)}"

    return _TOKEN_FLAG_RE.sub(replace, text)


def _shorten_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "********"
    return f"{secret[:6]}…{secret[-4:]}"
