from __future__ import annotations

import asyncio
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


@pytest.mark.asyncio
async def test_acp_gateway_agent_prompt_sends_chat_and_resolves_on_final_event() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    store.create_session(
        session_id="session-1",
        session_key="agent:main:main",
        cwd="C:/work",
    )
    agent = AcpGatewayAgent(connection, gateway, session_store=store)

    prompt_task = asyncio.create_task(
        agent.prompt(
            {
                "sessionId": "session-1",
                "prompt": [{"type": "text", "text": "hello"}],
                "_meta": {"prefixCwd": False, "thinking": "high"},
            }
        )
    )
    await asyncio.sleep(0)

    send_method, send_params = gateway.calls[-1]
    assert send_method == "chat.send"
    run_id = send_params["idempotencyKey"]
    assert isinstance(run_id, str)
    assert send_params == {
        "sessionKey": "agent:main:main",
        "message": "hello",
        "idempotencyKey": run_id,
        "thinking": "high",
    }
    assert store.get_session("session-1")["activeRunId"] == run_id  # type: ignore[index]
    assert not prompt_task.done()

    await agent.handle_gateway_event(
        {
            "event": "chat",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "state": "final",
                "stopReason": "max_tokens",
            },
        }
    )

    assert await prompt_task == {"stopReason": "max_tokens"}
    assert store.get_session("session-1")["activeRunId"] is None  # type: ignore[index]


@pytest.mark.asyncio
async def test_acp_gateway_agent_chat_delta_emits_incremental_text_and_thinking() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    store.create_session(
        session_id="session-1",
        session_key="agent:main:main",
        cwd="C:/work",
    )
    agent = AcpGatewayAgent(connection, gateway, session_store=store)
    prompt_task = asyncio.create_task(
        agent.prompt(
            {
                "sessionId": "session-1",
                "prompt": [{"type": "text", "text": "hello"}],
                "_meta": {"prefixCwd": False},
            }
        )
    )
    await asyncio.sleep(0)
    run_id = gateway.calls[-1][1]["idempotencyKey"]
    connection.session_updates.clear()

    await agent.handle_gateway_event(
        {
            "event": "chat",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "state": "delta",
                "message": {
                    "content": [
                        {"type": "thinking", "thinking": "Private"},
                        {"type": "text", "text": "Visible"},
                    ]
                },
            },
        }
    )
    await agent.handle_gateway_event(
        {
            "event": "chat",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "state": "delta",
                "message": {
                    "content": [
                        {"type": "thinking", "thinking": "Private thought"},
                        {"type": "text", "text": "Visible reply"},
                    ]
                },
            },
        }
    )
    await agent.handle_gateway_event(
        {
            "event": "chat",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "state": "final",
            },
        }
    )

    assert {
        "sessionId": "session-1",
        "update": {
            "sessionUpdate": "agent_thought_chunk",
            "content": {"type": "text", "text": "Private"},
        },
    } in connection.session_updates
    assert {
        "sessionId": "session-1",
        "update": {
            "sessionUpdate": "agent_thought_chunk",
            "content": {"type": "text", "text": " thought"},
        },
    } in connection.session_updates
    assert {
        "sessionId": "session-1",
        "update": {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": "Visible"},
        },
    } in connection.session_updates
    assert {
        "sessionId": "session-1",
        "update": {
            "sessionUpdate": "agent_message_chunk",
            "content": {"type": "text", "text": " reply"},
        },
    } in connection.session_updates
    assert await prompt_task == {"stopReason": "end_turn"}


@pytest.mark.asyncio
async def test_acp_gateway_agent_cancel_aborts_active_prompt_run() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    store.create_session(
        session_id="session-1",
        session_key="agent:main:main",
        cwd="C:/work",
    )
    agent = AcpGatewayAgent(connection, gateway, session_store=store)
    prompt_task = asyncio.create_task(
        agent.prompt(
            {
                "sessionId": "session-1",
                "prompt": [{"type": "text", "text": "hello"}],
                "_meta": {"prefixCwd": False},
            }
        )
    )
    await asyncio.sleep(0)
    run_id = gateway.calls[-1][1]["idempotencyKey"]

    await agent.cancel({"sessionId": "session-1"})

    assert ("chat.abort", {"sessionKey": "agent:main:main", "runId": run_id}) in gateway.calls
    assert await prompt_task == {"stopReason": "cancelled"}


@pytest.mark.asyncio
async def test_acp_gateway_agent_streams_tool_call_events() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    store.create_session(
        session_id="session-1",
        session_key="agent:main:main",
        cwd="C:/work",
    )
    agent = AcpGatewayAgent(connection, gateway, session_store=store)
    prompt_task = asyncio.create_task(
        agent.prompt(
            {
                "sessionId": "session-1",
                "prompt": [{"type": "text", "text": "hello"}],
                "_meta": {"prefixCwd": False},
            }
        )
    )
    await asyncio.sleep(0)
    run_id = gateway.calls[-1][1]["idempotencyKey"]
    connection.session_updates.clear()

    await agent.handle_gateway_event(
        {
            "event": "agent",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "stream": "tool",
                "data": {
                    "phase": "start",
                    "toolCallId": "tool-1",
                    "name": "shell.exec",
                    "args": {"path": "C:/work/app.py", "line": 4},
                },
            },
        }
    )
    await agent.handle_gateway_event(
        {
            "event": "agent",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "stream": "tool",
                "data": {
                    "phase": "update",
                    "toolCallId": "tool-1",
                    "partialResult": "running\nFILE:C:/work/app.py",
                },
            },
        }
    )
    await agent.handle_gateway_event(
        {
            "event": "agent",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "stream": "tool",
                "data": {
                    "phase": "result",
                    "toolCallId": "tool-1",
                    "result": {"text": "done"},
                },
            },
        }
    )
    await agent.handle_gateway_event(
        {
            "event": "chat",
            "payload": {
                "sessionKey": "agent:main:main",
                "runId": run_id,
                "state": "final",
            },
        }
    )

    assert connection.session_updates[:3] == [
        {
            "sessionId": "session-1",
            "update": {
                "sessionUpdate": "tool_call",
                "toolCallId": "tool-1",
                "title": "shell.exec: path: C:/work/app.py, line: 4",
                "status": "in_progress",
                "rawInput": {"path": "C:/work/app.py", "line": 4},
                "kind": "execute",
                "locations": [{"path": "C:/work/app.py", "line": 4}],
            },
        },
        {
            "sessionId": "session-1",
            "update": {
                "sessionUpdate": "tool_call_update",
                "toolCallId": "tool-1",
                "status": "in_progress",
                "rawOutput": "running\nFILE:C:/work/app.py",
                "content": [
                    {
                        "type": "content",
                        "content": {"type": "text", "text": "running\nFILE:C:/work/app.py"},
                    }
                ],
                "locations": [{"path": "C:/work/app.py", "line": 4}],
            },
        },
        {
            "sessionId": "session-1",
            "update": {
                "sessionUpdate": "tool_call_update",
                "toolCallId": "tool-1",
                "status": "completed",
                "rawOutput": {"text": "done"},
                "content": [
                    {"type": "content", "content": {"type": "text", "text": "done"}}
                ],
                "locations": [{"path": "C:/work/app.py", "line": 4}],
            },
        },
    ]
    assert await prompt_task == {"stopReason": "end_turn"}


@pytest.mark.asyncio
async def test_acp_gateway_agent_set_session_mode_patches_and_refreshes_controls() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    store.create_session(
        session_id="session-1",
        session_key="agent:main:work",
        cwd="C:/work",
    )
    agent = AcpGatewayAgent(connection, gateway, session_store=store)

    result = await agent.set_session_mode({"sessionId": "session-1", "modeId": "high"})

    assert result == {}
    assert ("sessions.patch", {"key": "agent:main:work", "thinkingLevel": "high"}) in gateway.calls
    assert {
        "sessionId": "session-1",
        "update": {
            "sessionUpdate": "current_mode_update",
            "currentModeId": "high",
        },
    } in connection.session_updates
    assert any(
        update["sessionId"] == "session-1"
        and isinstance(update["update"], dict)
        and update["update"].get("sessionUpdate") == "config_option_update"
        and any(
            option.get("id") == "thought_level" and option.get("currentValue") == "high"
            for option in update["update"].get("configOptions", [])
        )
        for update in connection.session_updates
    )


@pytest.mark.asyncio
async def test_acp_gateway_agent_set_session_config_option_patches_openclaw_fields() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    connection = FakeAcpConnection()
    gateway = FakeGateway()
    store = create_in_memory_session_store()
    store.create_session(
        session_id="session-1",
        session_key="agent:main:work",
        cwd="C:/work",
    )
    agent = AcpGatewayAgent(connection, gateway, session_store=store)

    result = await agent.set_session_config_option(
        {"sessionId": "session-1", "configId": "fast_mode", "value": "on"}
    )

    assert ("sessions.patch", {"key": "agent:main:work", "fastMode": True}) in gateway.calls
    assert any(
        option["id"] == "fast_mode" and option["currentValue"] == "on"
        for option in result["configOptions"]  # type: ignore[index]
    )


@pytest.mark.asyncio
async def test_acp_gateway_agent_rate_limits_new_session_creates() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    agent = AcpGatewayAgent(
        FakeAcpConnection(),
        FakeGateway(),
        session_store=create_in_memory_session_store(),
        session_create_rate_limit={"maxRequests": 2, "windowMs": 60_000},
    )

    await agent.new_session({"cwd": "C:/one", "mcpServers": [], "_meta": {"sessionKey": "one"}})
    await agent.new_session({"cwd": "C:/two", "mcpServers": [], "_meta": {"sessionKey": "two"}})

    with pytest.raises(RuntimeError, match="ACP session creation rate limit exceeded"):
        await agent.new_session(
            {"cwd": "C:/three", "mcpServers": [], "_meta": {"sessionKey": "three"}}
        )


@pytest.mark.asyncio
async def test_acp_gateway_agent_existing_load_session_refresh_does_not_count_rate_limit() -> None:
    from openzues.services.acp_agent import AcpGatewayAgent
    from openzues.services.acp_session_store import create_in_memory_session_store

    store = create_in_memory_session_store()
    agent = AcpGatewayAgent(
        FakeAcpConnection(),
        FakeGateway(),
        session_store=store,
        session_create_rate_limit={"maxRequests": 1, "windowMs": 60_000},
    )

    load_shared = {"sessionId": "shared", "cwd": "C:/one", "mcpServers": [], "_meta": {}}
    await agent.load_session(load_shared)
    await agent.load_session(load_shared)

    with pytest.raises(RuntimeError, match="ACP session creation rate limit exceeded"):
        await agent.load_session(
            {"sessionId": "new", "cwd": "C:/two", "mcpServers": [], "_meta": {}}
        )
