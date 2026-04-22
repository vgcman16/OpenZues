from __future__ import annotations

import os
from pathlib import Path

import pytest

from openzues.services.gateway_logs import (
    GatewayLogsService,
    _redact_sensitive_tokens,
    _shorten_secret,
)


@pytest.mark.asyncio
async def test_gateway_logs_tail_redacts_cli_json_and_bearer_secrets(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    log_path = logs_root / "openzues.log"
    cli_secret = "sk-openai-1234567890abcdefghijkl"
    json_secret = "tok_1234567890abcdefghijklmnop"
    bearer_secret = "bearer_1234567890abcdefghijklmnop"
    log_path.write_text(
        "\n".join(
            [
                f'codex --api-key "{cli_secret}"',
                f'{{"accessToken":"{json_secret}"}}',
                f"Authorization: Bearer {bearer_secret}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = await GatewayLogsService(logs_root=logs_root).read_tail(
        limit=10,
        max_bytes=10_000,
    )

    assert payload["file"] == str(log_path)
    assert payload["lines"] == [
        f'codex --api-key "{_shorten_secret(cli_secret)}"',
        f'{{"accessToken":"{_shorten_secret(json_secret)}"}}',
        f"Authorization: Bearer {_shorten_secret(bearer_secret)}",
    ]
    joined_lines = "\n".join(payload["lines"])
    assert cli_secret not in joined_lines
    assert json_secret not in joined_lines
    assert bearer_secret not in joined_lines


def test_gateway_logs_short_secrets_mask_completely() -> None:
    assert _shorten_secret("abcd1234") == "***"


def test_gateway_logs_masks_medium_length_bearer_tokens_completely() -> None:
    bearer_secret = "abcdef1234567890"

    redacted = _redact_sensitive_tokens(f"Authorization: Bearer {bearer_secret}")

    assert redacted == "Authorization: Bearer ***"


def test_gateway_logs_only_redacts_bare_bearer_tokens_at_openclaw_length_threshold() -> None:
    short_bearer_secret = "abcdef1234567890"
    long_bearer_secret = "abcdef1234567890zz"

    redacted = _redact_sensitive_tokens(
        "\n".join(
            [
                f"Bearer {short_bearer_secret}",
                f"Bearer {long_bearer_secret}",
            ]
        )
    )

    assert redacted == "\n".join(
        [
            f"Bearer {short_bearer_secret}",
            f"Bearer {_shorten_secret(long_bearer_secret)}",
        ]
    )


@pytest.mark.asyncio
async def test_gateway_logs_tail_prefers_runtime_logs_over_newer_debug_artifacts(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    runtime_log = logs_root / "openzues-2026-04-22.log"
    debug_log = logs_root / "browser-step-debug.log"
    runtime_log.write_text("runtime line\n", encoding="utf-8")
    debug_log.write_text("debug line\n", encoding="utf-8")
    os.utime(runtime_log, (10, 10))
    os.utime(debug_log, None)

    payload = await GatewayLogsService(logs_root=logs_root).read_tail(
        limit=10,
        max_bytes=10_000,
    )

    assert payload["file"] == str(runtime_log)
    assert payload["lines"] == ["runtime line"]


@pytest.mark.asyncio
async def test_gateway_logs_tail_falls_back_to_latest_generic_log_without_runtime_match(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    older = logs_root / "alpha.log"
    newer = logs_root / "browser-step-debug.log"
    older.write_text("older line\n", encoding="utf-8")
    newer.write_text("newer line\n", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, None)

    payload = await GatewayLogsService(logs_root=logs_root).read_tail(
        limit=10,
        max_bytes=10_000,
    )

    assert payload["file"] == str(newer)
    assert payload["lines"] == ["newer line"]


@pytest.mark.asyncio
async def test_gateway_logs_tail_reads_configured_log_file_path_even_when_other_logs_are_newer(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    configured = logs_root / "watch.log"
    newer_debug = logs_root / "browser-step-debug.log"
    configured.write_text("configured line\n", encoding="utf-8")
    newer_debug.write_text("debug line\n", encoding="utf-8")
    os.utime(configured, (1, 1))
    os.utime(newer_debug, None)

    payload = await GatewayLogsService(logs_root=configured).read_tail(
        limit=10,
        max_bytes=10_000,
    )

    assert payload["file"] == str(configured)
    assert payload["lines"] == ["configured line"]


@pytest.mark.asyncio
async def test_gateway_logs_tail_redacts_multiline_private_key_blocks(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    log_path = logs_root / "openzues.log"
    key_material = [
        "-----BEGIN PRIVATE KEY-----",
        "very-secret-material-123",
        "still-secret-material-456",
        "-----END PRIVATE KEY-----",
    ]
    log_path.write_text(
        "\n".join(["before key", *key_material, "after key"]) + "\n",
        encoding="utf-8",
    )

    payload = await GatewayLogsService(logs_root=logs_root).read_tail(
        limit=20,
        max_bytes=10_000,
    )

    assert payload["file"] == str(log_path)
    assert payload["lines"] == [
        "before key",
        "-----BEGIN PRIVATE KEY-----",
        "...redacted...",
        "-----END PRIVATE KEY-----",
        "after key",
    ]
    joined_lines = "\n".join(payload["lines"])
    assert "very-secret-material-123" not in joined_lines
    assert "still-secret-material-456" not in joined_lines


@pytest.mark.asyncio
async def test_gateway_logs_tail_falls_back_to_latest_rolling_log_when_configured_daily_file_is_missing(
    tmp_path: Path,
) -> None:
    logs_root = tmp_path / "logs"
    logs_root.mkdir(parents=True, exist_ok=True)
    older = logs_root / "openzues-2026-04-21.log"
    newer = logs_root / "openzues-2026-04-22.log"
    debug = logs_root / "browser-step-debug.log"
    older.write_text("older runtime\n", encoding="utf-8")
    newer.write_text("newer runtime\n", encoding="utf-8")
    debug.write_text("debug line\n", encoding="utf-8")
    os.utime(older, (10, 10))
    os.utime(newer, (20, 20))
    os.utime(debug, None)

    configured_missing = logs_root / "openzues-2026-04-23.log"
    payload = await GatewayLogsService(logs_root=configured_missing).read_tail(
        limit=10,
        max_bytes=10_000,
    )

    assert payload["file"] == str(newer)
    assert payload["lines"] == ["newer runtime"]


def test_gateway_logs_redacts_env_assignments_and_common_token_prefixes() -> None:
    env_secret = "sk-openai-abcdefghijklmnopqrstuvwxyz"
    github_pat = "github_pat_abcdefghijklmnopqrstuvwxyz123456"

    redacted = _redact_sensitive_tokens(
        f"OPENAI_API_KEY={env_secret}\nsecondary {github_pat}"
    )

    assert redacted == (
        f"OPENAI_API_KEY={_shorten_secret(env_secret)}\n"
        f"secondary {_shorten_secret(github_pat)}"
    )


def test_gateway_logs_redacts_telegram_bot_tokens_and_bot_api_urls() -> None:
    telegram_token = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"

    redacted = _redact_sensitive_tokens(
        "\n".join(
            [
                telegram_token,
                f"GET https://api.telegram.org/bot{telegram_token}/getMe HTTP/1.1",
            ]
        )
    )

    assert redacted == "\n".join(
        [
            _shorten_secret(telegram_token),
            f"GET https://api.telegram.org/bot{_shorten_secret(telegram_token)}/getMe HTTP/1.1",
        ]
    )
    assert telegram_token not in redacted
