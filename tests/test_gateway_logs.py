from __future__ import annotations

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
    assert _shorten_secret("abcd1234") == "********"


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
