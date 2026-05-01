from __future__ import annotations

from typing import Any

import pytest


class FakeAcpConnection:
    def __init__(self) -> None:
        self.session_updates: list[dict[str, object]] = []

    async def session_update(self, payload: dict[str, object]) -> None:
        self.session_updates.append(payload)


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def request(self, method: str, params: dict[str, object]) -> dict[str, Any]:
        self.calls.append((method, params))
        if method == "sessions.list":
            key = str(params.get("search") or params.get("key") or "agent:main:work")
            return {
                "sessions": [
                    {
                        "key": key,
                        "label": "main-work",
                        "displayName": "Main work",
                        "derivedTitle": "Fix ACP bridge",
                        "updatedAt": 1_710_000_000_000,
                        "thinkingLevel": "high",
                        "modelProvider": "openai",
                        "model": "gpt-5.4",
                        "fastMode": True,
                        "verboseLevel": "full",
                        "traceLevel": "on",
                        "reasoningLevel": "stream",
                        "responseUsage": "tokens",
                        "elevatedLevel": "ask",
                        "totalTokens": 4096,
                        "totalTokensFresh": True,
                        "contextTokens": 8192,
                    }
                ]
            }
        if method == "sessions.get":
            return {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "Question"}]},
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "thinking", "thinking": "Private reasoning"},
                            {"type": "text", "text": "Answer"},
                        ],
                    },
                    {"role": "system", "content": [{"type": "text", "text": "ignore"}]},
                ]
            }
        return {"ok": True}


@pytest.mark.asyncio
async def test_acp_gateway_agent_initializes_openclaw_capabilities() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent

    agent = AcpGatewayAgent(FakeAcpConnection(), FakeGateway())

    response = await agent.initialize({})

    assert response["agentCapabilities"] == {
        "loadSession": True,
        "promptCapabilities": {
            "image": True,
            "audio": False,
            "embeddedContext": True,
        },
        "mcpCapabilities": {
            "http": False,
            "sse": False,
        },
        "sessionCapabilities": {"list": {}},
    }
    assert response["agentInfo"]["name"] == "openclaw-acp"
    assert response["authMethods"] == []


@pytest.mark.asyncio
async def test_acp_gateway_agent_new_session_emits_snapshot_and_commands() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    agent = AcpGatewayAgent(connection, gateway, session_store=store)

    result = await agent.new_session(
        {
            "cwd": "C:/work",
            "mcpServers": [],
            "_meta": {"sessionKey": "agent:main:work"},
        }
    )

    session_id = result["sessionId"]
    assert isinstance(session_id, str)
    assert store.get_session(session_id)["sessionKey"] == "agent:main:work"  # type: ignore[index]
    assert result["modes"]["currentModeId"] == "high"  # type: ignore[index]
    assert {
        option["id"]: option["currentValue"] for option in result["configOptions"]  # type: ignore[index]
    } == {
        "thought_level": "high",
        "fast_mode": "on",
        "verbose_level": "full",
        "trace_level": "on",
        "reasoning_level": "stream",
        "response_usage": "tokens",
        "elevated_level": "ask",
    }
    assert (
        "sessions.list",
        {"limit": 200, "search": "agent:main:work", "includeDerivedTitles": True},
    ) in gateway.calls
    assert {
        "sessionId": session_id,
        "update": {
            "sessionUpdate": "session_info_update",
            "title": "Fix ACP bridge",
            "updatedAt": "2024-03-09T16:00:00.000Z",
        },
    } in connection.session_updates
    assert {
        "sessionId": session_id,
        "update": {
            "sessionUpdate": "usage_update",
            "used": 4096,
            "size": 8192,
            "_meta": {"source": "gateway-session-store", "approximate": True},
        },
    } in connection.session_updates
    assert any(
        update["sessionId"] == session_id
        and isinstance(update["update"], dict)
        and update["update"].get("sessionUpdate") == "available_commands_update"
        for update in connection.session_updates
    )


@pytest.mark.asyncio
async def test_acp_gateway_agent_load_session_replays_transcript_and_snapshot() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    agent = AcpGatewayAgent(connection, gateway, session_store=create_in_memory_session_store())

    result = await agent.load_session(
        {
            "sessionId": "agent:main:work",
            "cwd": "C:/work",
            "mcpServers": [],
            "_meta": {},
        }
    )

    assert result["modes"]["currentModeId"] == "high"  # type: ignore[index]
    assert {
        "sessionId": "agent:main:work",
        "update": {
            "sessionUpdate": "user_message_chunk",
            "content": {"type": "text", "text": "Question"},
        },
    } in connection.session_updates
    assert {
        "sessionId": "agent:main:work",
        "update": {
            "sessionUpdate": "agent_thought_chunk",
            "content": {"type": "text", "text": "Private reasoning"},
        },
    } in connection.session_updates
    assert {
        "sessionId": "agent:main:work",
        "update": {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "Answer"},
        },
    } in connection.session_updates
    assert ("sessions.get", {"key": "agent:main:work", "limit": 1_000_000}) in gateway.calls
