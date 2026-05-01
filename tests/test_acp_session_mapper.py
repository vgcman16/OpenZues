from __future__ import annotations

import pytest


class FakeGateway:
    def __init__(self, *, label_key: str = "agent:main:label") -> None:
        self.label_key = label_key
        self.requests: list[tuple[str, dict[str, object]]] = []

    async def request(self, method: str, params: dict[str, object]) -> dict[str, object]:
        self.requests.append((method, params))
        if method == "sessions.resolve" and "label" in params:
            return {"ok": True, "key": self.label_key}
        if method == "sessions.resolve" and "key" in params:
            return {"ok": True, "key": params["key"]}
        return {"ok": True}


def test_acp_session_mapper_parses_upstream_meta_aliases() -> None:
    from openzues.services.acp_session_mapper import parse_session_meta

    assert parse_session_meta(
        {
            "session": "agent:main:main",
            "label": "Support",
            "reset": True,
            "requireExisting": False,
            "prefixCwd": True,
        }
    ) == {
        "sessionKey": "agent:main:main",
        "sessionLabel": "Support",
        "resetSession": True,
        "requireExisting": False,
        "prefixCwd": True,
    }
    assert parse_session_meta(None) == {}
    assert parse_session_meta({"sessionKey": "   ", "reset": "true"}) == {}


@pytest.mark.asyncio
async def test_acp_session_mapper_prefers_explicit_label_over_session_key() -> None:
    from openzues.services.acp_session_mapper import parse_session_meta, resolve_session_key

    gateway = FakeGateway()
    key = await resolve_session_key(
        meta=parse_session_meta(
            {"sessionLabel": "support", "sessionKey": "agent:main:main"}
        ),
        fallback_key="acp:fallback",
        gateway=gateway,
        opts={},
    )

    assert key == "agent:main:label"
    assert gateway.requests == [("sessions.resolve", {"label": "support"})]


@pytest.mark.asyncio
async def test_acp_session_mapper_meta_key_overrides_default_label_without_lookup() -> None:
    from openzues.services.acp_session_mapper import parse_session_meta, resolve_session_key

    gateway = FakeGateway()
    key = await resolve_session_key(
        meta=parse_session_meta({"sessionKey": "agent:main:override"}),
        fallback_key="acp:fallback",
        gateway=gateway,
        opts={"defaultSessionLabel": "default-label"},
    )

    assert key == "agent:main:override"
    assert gateway.requests == []


@pytest.mark.asyncio
async def test_acp_session_mapper_requires_existing_keys_when_requested() -> None:
    from openzues.services.acp_session_mapper import parse_session_meta, resolve_session_key

    gateway = FakeGateway()
    key = await resolve_session_key(
        meta=parse_session_meta(
            {"sessionKey": "agent:main:main", "requireExisting": True}
        ),
        fallback_key="acp:fallback",
        gateway=gateway,
        opts={},
    )

    assert key == "agent:main:main"
    assert gateway.requests == [("sessions.resolve", {"key": "agent:main:main"})]


@pytest.mark.asyncio
async def test_acp_session_mapper_resets_session_only_when_requested() -> None:
    from openzues.services.acp_session_mapper import parse_session_meta, reset_session_if_needed

    gateway = FakeGateway()

    await reset_session_if_needed(
        meta=parse_session_meta({}),
        session_key="agent:main:main",
        gateway=gateway,
        opts={},
    )
    await reset_session_if_needed(
        meta=parse_session_meta({"resetSession": True}),
        session_key="agent:main:main",
        gateway=gateway,
        opts={},
    )

    assert gateway.requests == [("sessions.reset", {"key": "agent:main:main"})]
