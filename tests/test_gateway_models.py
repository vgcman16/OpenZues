from __future__ import annotations

import pytest

from openzues.schemas import InstanceView
from openzues.services.gateway_models import GatewayModelsService


def _instance_view(
    models: list[dict[str, object]],
    *,
    instance_id: int = 1,
    name: str = "Local Codex Desktop",
    config: dict[str, object] | None = None,
) -> InstanceView:
    return InstanceView(
        id=instance_id,
        name=name,
        transport="desktop",
        command=None,
        args=None,
        websocket_url=None,
        cwd="C:/workspace",
        auto_connect=False,
        connected=True,
        models=models,
        config=config,
    )


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_returns_default_bounded_catalog() -> None:
    payload = await GatewayModelsService().build_catalog()

    assert payload == {
        "models": [
            {
                "id": "gpt-5.4",
                "name": "gpt-5.4",
                "provider": "openai",
                "isDefault": True,
            },
            {
                "id": "gpt-5.4-mini",
                "name": "gpt-5.4-mini",
                "provider": "openai",
            },
        ]
    }


@pytest.mark.asyncio
async def test_gateway_models_auth_status_returns_empty_snapshot_without_instances() -> None:
    payload = await GatewayModelsService().build_auth_status(refresh=True, now_ms=1234)

    assert payload == {"ts": 1234, "providers": []}


@pytest.mark.asyncio
async def test_gateway_models_auth_status_uses_fakeable_runtime_and_sanitizes_profiles() -> None:
    calls: list[dict[str, object]] = []

    async def fake_auth_status_service(
        *,
        refresh: bool,
        now_ms: int,
    ) -> dict[str, object]:
        calls.append({"refresh": refresh, "nowMs": now_ms})
        return {
            "ts": 1000,
            "providers": [
                {
                    "provider": "openai-codex",
                    "displayName": "OpenAI Codex",
                    "status": "ok",
                    "secret": "sk-hidden",
                    "expiry": {"at": 2000, "remainingMs": 1000, "label": "1s"},
                    "profiles": [
                        {
                            "profileId": "openai-codex:default",
                            "type": "oauth",
                            "status": "ok",
                            "access": "sk-hidden",
                            "expiry": {"at": 2000, "remainingMs": 1000, "label": "1s"},
                        }
                    ],
                    "usage": {"windows": [{"window": "day", "used": 1}], "plan": "pro"},
                }
            ],
        }

    payload = await GatewayModelsService(
        auth_status_service=fake_auth_status_service,
    ).build_auth_status(refresh=True, now_ms=555)

    assert calls == [{"refresh": True, "nowMs": 555}]
    assert payload == {
        "ts": 1000,
        "providers": [
            {
                "provider": "openai-codex",
                "displayName": "OpenAI Codex",
                "status": "ok",
                "expiry": {"at": 2000, "remainingMs": 1000, "label": "1s"},
                "profiles": [
                    {
                        "profileId": "openai-codex:default",
                        "type": "oauth",
                        "status": "ok",
                        "expiry": {"at": 2000, "remainingMs": 1000, "label": "1s"},
                    }
                ],
                "usage": {"windows": [{"window": "day", "used": 1}], "plan": "pro"},
            }
        ],
    }
    assert "sk-hidden" not in str(payload)


@pytest.mark.asyncio
async def test_gateway_models_auth_status_caches_until_refresh() -> None:
    calls: list[int] = []

    async def fake_auth_status_service(
        *,
        refresh: bool,
        now_ms: int,
    ) -> dict[str, object]:
        calls.append(now_ms)
        return {
            "ts": now_ms,
            "providers": [
                {
                    "provider": "anthropic",
                    "displayName": "Anthropic",
                    "status": "missing",
                    "profiles": [],
                }
            ],
        }

    service = GatewayModelsService(auth_status_service=fake_auth_status_service)

    first = await service.build_auth_status(now_ms=1000)
    second = await service.build_auth_status(now_ms=1500)
    refreshed = await service.build_auth_status(refresh=True, now_ms=2000)

    assert calls == [1000, 2000]
    assert second == first
    assert refreshed["ts"] == 2000


@pytest.mark.asyncio
async def test_gateway_models_auth_status_synthesizes_missing_refreshable_provider() -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={"models": {"providers": {"openai-codex": {"auth": "oauth"}}}},
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views,
    ).build_auth_status(now_ms=1234)

    assert payload == {
        "ts": 1234,
        "providers": [
            {
                "provider": "openai-codex",
                "displayName": "openai-codex",
                "status": "missing",
                "profiles": [],
            }
        ],
    }


@pytest.mark.asyncio
async def test_gateway_models_auth_status_skips_env_backed_refreshable_provider() -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={
                    "models": {
                        "providers": {
                            "openai-codex": {"auth": "oauth", "apiKey": "sk-present"}
                        }
                    }
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views,
    ).build_auth_status(now_ms=1234)

    assert payload == {"ts": 1234, "providers": []}


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_normalizes_sorts_and_merges_duplicates() -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {"id": "openai/gpt-5.4-mini", "input": ["text"]},
                    {
                        "id": "anthropic/claude-3.7-sonnet",
                        "displayName": "claude-3.7-sonnet",
                        "reasoning": True,
                        "input": ["text", "image", "text"],
                    },
                    {
                        "id": "gpt-5.4-mini",
                        "provider": "openai",
                        "alias": "Fast GPT",
                        "contextWindow": 128_000,
                        "reasoning": False,
                        "input": ["image", "text"],
                    },
                ]
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert payload == {
        "models": [
            {
                "id": "claude-3.7-sonnet",
                "name": "claude-3.7-sonnet",
                "provider": "anthropic",
                "reasoning": True,
                "input": ["text", "image"],
            },
            {
                "id": "gpt-5.4",
                "name": "gpt-5.4",
                "provider": "openai",
                "isDefault": True,
            },
            {
                "id": "gpt-5.4-mini",
                "name": "gpt-5.4-mini",
                "provider": "openai",
                "alias": "Fast GPT",
                "contextWindow": 128_000,
                "reasoning": False,
                "input": ["text", "image"],
            },
        ]
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_prefers_richer_duplicate_display_name() -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {"id": "openai/gpt-5.4-mini"},
                    {
                        "id": "gpt-5.4-mini",
                        "provider": "openai",
                        "displayName": "GPT 5.4 Mini",
                    },
                ]
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert payload["models"][-1] == {
        "id": "gpt-5.4-mini",
        "name": "GPT 5.4 Mini",
        "provider": "openai",
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_normalizes_openclaw_provider_aliases() -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {
                        "id": "bedrock/claude-3.7-sonnet",
                        "displayName": "Claude 3.7 Sonnet",
                        "contextWindow": 200_000,
                    },
                    {
                        "id": "claude-3.7-sonnet",
                        "provider": "amazon-bedrock",
                        "reasoning": True,
                        "input": ["text", "image"],
                    },
                    {"id": "z-ai/glm-4.6", "input": ["text"]},
                    {
                        "id": "glm-4.6",
                        "provider": "zai",
                        "alias": "GLM Fast",
                    },
                    {"id": "qwencloud/qwen-max", "input": ["text"]},
                ]
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.7-sonnet"
    ) == {
        "id": "claude-3.7-sonnet",
        "name": "Claude 3.7 Sonnet",
        "provider": "amazon-bedrock",
        "contextWindow": 200_000,
        "reasoning": True,
        "input": ["text", "image"],
    }
    assert next(model for model in payload["models"] if model["id"] == "glm-4.6") == {
        "id": "glm-4.6",
        "name": "glm-4.6",
        "provider": "zai",
        "alias": "GLM Fast",
        "input": ["text"],
    }
    assert next(model for model in payload["models"] if model["id"] == "qwen-max") == {
        "id": "qwen-max",
        "name": "qwen-max",
        "provider": "qwen",
        "input": ["text"],
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_synthesizes_configured_primary_model() -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={
                    "model": "anthropic/claude-3.7-sonnet",
                    "model_reasoning_effort": "high",
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.7-sonnet"
    ) == {
        "id": "claude-3.7-sonnet",
        "name": "claude-3.7-sonnet",
        "provider": "anthropic",
        "isDefault": True,
        "defaultReasoningEffort": "high",
    }
    assert [model["id"] for model in payload["models"] if model.get("isDefault")] == [
        "claude-3.7-sonnet"
    ]
    assert next(model for model in payload["models"] if model["id"] == "gpt-5.4") == {
        "id": "gpt-5.4",
        "name": "gpt-5.4",
        "provider": "openai",
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_synthesizes_object_configured_primary_model(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={
                    "model": {
                        "primary": "anthropic/claude-3.7-sonnet",
                        "fallbacks": ["openai/gpt-5.4"],
                    },
                    "modelReasoningEffort": "high",
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.7-sonnet"
    ) == {
        "id": "claude-3.7-sonnet",
        "name": "claude-3.7-sonnet",
        "provider": "anthropic",
        "isDefault": True,
        "defaultReasoningEffort": "high",
    }
    assert [model["id"] for model in payload["models"] if model.get("isDefault")] == [
        "claude-3.7-sonnet"
    ]
    assert next(model for model in payload["models"] if model["id"] == "gpt-5.4") == {
        "id": "gpt-5.4",
        "name": "gpt-5.4",
        "provider": "openai",
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_synthesizes_object_configured_fallback_models(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={
                    "model": {
                        "primary": "anthropic/claude-3.7-sonnet",
                        "fallbacks": [
                            " openrouter/deepseek-chat ",
                            "openrouter/deepseek-chat",
                            " ",
                            "anthropic/claude-3.5-haiku",
                        ],
                    },
                    "modelReasoningEffort": "high",
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.7-sonnet"
    ) == {
        "id": "claude-3.7-sonnet",
        "name": "claude-3.7-sonnet",
        "provider": "anthropic",
        "isDefault": True,
        "defaultReasoningEffort": "high",
    }
    assert next(model for model in payload["models"] if model["id"] == "deepseek-chat") == {
        "id": "deepseek-chat",
        "name": "deepseek-chat",
        "provider": "openrouter",
    }
    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.5-haiku"
    ) == {
        "id": "claude-3.5-haiku",
        "name": "claude-3.5-haiku",
        "provider": "anthropic",
    }
    assert [model["id"] for model in payload["models"] if model["id"] == "deepseek-chat"] == [
        "deepseek-chat"
    ]
    assert [model["id"] for model in payload["models"] if model.get("isDefault")] == [
        "claude-3.7-sonnet"
    ]


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_infers_provider_for_unprefixed_configured_model(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {
                        "id": "openai/gpt-5.4-mini",
                        "displayName": "GPT 5.4 Mini",
                        "contextWindow": 128_000,
                    }
                ],
                config={
                    "model": "gpt-5.4-mini",
                    "model_reasoning_effort": "medium",
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(model for model in payload["models"] if model["id"] == "gpt-5.4-mini") == {
        "id": "gpt-5.4-mini",
        "name": "GPT 5.4 Mini",
        "provider": "openai",
        "contextWindow": 128_000,
        "isDefault": True,
        "defaultReasoningEffort": "medium",
    }


@pytest.mark.asyncio
async def test_gateway_models_infers_provider_for_unprefixed_object_primary(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {
                        "id": "openai/gpt-5.4-mini",
                        "displayName": "GPT 5.4 Mini",
                        "contextWindow": 128_000,
                    }
                ],
                config={
                    "model": {
                        "primary": "gpt-5.4-mini",
                        "fallbacks": ["anthropic/claude-3.7-sonnet"],
                    },
                    "model_reasoning_effort": "medium",
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(model for model in payload["models"] if model["id"] == "gpt-5.4-mini") == {
        "id": "gpt-5.4-mini",
        "name": "GPT 5.4 Mini",
        "provider": "openai",
        "contextWindow": 128_000,
        "isDefault": True,
        "defaultReasoningEffort": "medium",
    }
    assert [model["id"] for model in payload["models"] if model.get("isDefault")] == [
        "gpt-5.4-mini"
    ]


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_filters_to_allowlisted_configured_models_by_default(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {"id": "openai/gpt-test-z"},
                    {
                        "id": "anthropic/claude-test-a",
                        "displayName": "A-Model",
                        "contextWindow": 200_000,
                    },
                    {
                        "id": "openrouter/deepseek-chat",
                        "displayName": "DeepSeek Chat",
                    },
                ],
                config={
                    "agents": {
                        "defaults": {
                            "model": {"primary": "openai/gpt-test-z"},
                            "models": {
                                "openai/gpt-test-z": {},
                                "anthropic/claude-test-a": {},
                            },
                        }
                    }
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert payload == {
        "models": [
            {
                "id": "claude-test-a",
                "name": "A-Model",
                "provider": "anthropic",
                "contextWindow": 200_000,
            },
            {
                "id": "gpt-test-z",
                "name": "gpt-test-z",
                "provider": "openai",
            },
        ]
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_keeps_configured_fallbacks_visible_with_allowlist(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [
                    {
                        "id": "openai/gpt-5.4-mini",
                        "displayName": "GPT 5.4 Mini",
                    },
                    {
                        "id": "anthropic/claude-3.7-sonnet",
                        "displayName": "Claude 3.7 Sonnet",
                    },
                    {
                        "id": "openrouter/deepseek-chat",
                        "displayName": "DeepSeek Chat",
                    },
                ],
                config={
                    "agents": {
                        "defaults": {
                            "model": {
                                "primary": "openai/gpt-5.4-mini",
                                "fallbacks": ["anthropic/claude-3.7-sonnet"],
                            },
                            "models": {
                                "openai/gpt-5.4-mini": {},
                            },
                        }
                    }
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert payload == {
        "models": [
            {
                "id": "claude-3.7-sonnet",
                "name": "Claude 3.7 Sonnet",
                "provider": "anthropic",
            },
            {
                "id": "gpt-5.4-mini",
                "name": "GPT 5.4 Mini",
                "provider": "openai",
            },
        ]
    }


@pytest.mark.asyncio
async def test_gateway_models_applies_configured_metadata_to_synthetic_allowlist(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={
                    "agents": {
                        "defaults": {
                            "model": {"primary": "nvidia/moonshotai/kimi-k2.5"},
                            "models": {
                                "nvidia/moonshotai/kimi-k2.5": {
                                    "alias": "Kimi K2.5 (NVIDIA)"
                                }
                            },
                        }
                    },
                    "models": {
                        "providers": {
                            "nvidia": {
                                "models": [
                                    {
                                        "id": "moonshotai/kimi-k2.5",
                                        "name": "Kimi K2.5 (Configured)",
                                        "contextWindow": 32_000,
                                    }
                                ]
                            }
                        }
                    },
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert payload == {
        "models": [
            {
                "id": "moonshotai/kimi-k2.5",
                "name": "Kimi K2.5 (Configured)",
                "alias": "Kimi K2.5 (NVIDIA)",
                "provider": "nvidia",
                "contextWindow": 32_000,
            }
        ]
    }


@pytest.mark.asyncio
async def test_gateway_models_build_catalog_resolves_configured_aliases_for_primary_and_fallbacks(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [],
                config={
                    "model": {
                        "primary": "sonnet",
                        "fallbacks": ["fast", "fast"],
                    },
                    "modelReasoningEffort": "high",
                    "agents": {
                        "defaults": {
                            "models": {
                                "anthropic/claude-3.7-sonnet": {"alias": "sonnet"},
                                "openai/gpt-5.4-mini": {"alias": "fast"},
                            }
                        }
                    },
                    "models": {
                        "providers": {
                            "anthropic": {
                                "models": [
                                    {
                                        "id": "claude-3.7-sonnet",
                                        "name": "Claude 3.7 Sonnet",
                                        "contextWindow": 200_000,
                                        "reasoning": True,
                                        "input": ["text", "image"],
                                    }
                                ]
                            },
                            "openai": {
                                "models": [
                                    {
                                        "id": "gpt-5.4-mini",
                                        "name": "GPT 5.4 Mini",
                                        "contextWindow": 128_000,
                                        "reasoning": False,
                                        "input": ["text"],
                                    }
                                ]
                            },
                        }
                    },
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.7-sonnet"
    ) == {
        "id": "claude-3.7-sonnet",
        "name": "Claude 3.7 Sonnet",
        "provider": "anthropic",
        "alias": "sonnet",
        "contextWindow": 200_000,
        "reasoning": True,
        "input": ["text", "image"],
        "isDefault": True,
        "defaultReasoningEffort": "high",
    }
    assert next(model for model in payload["models"] if model["id"] == "gpt-5.4-mini") == {
        "id": "gpt-5.4-mini",
        "name": "GPT 5.4 Mini",
        "provider": "openai",
        "alias": "fast",
        "contextWindow": 128_000,
        "reasoning": False,
        "input": ["text"],
    }
    assert [model["id"] for model in payload["models"] if model["id"] == "gpt-5.4-mini"] == [
        "gpt-5.4-mini"
    ]


@pytest.mark.asyncio
async def test_gateway_models_overlays_configured_provider_metadata(
) -> None:
    async def list_instance_views() -> list[InstanceView]:
        return [
            _instance_view(
                [{"id": "anthropic/claude-3.7-sonnet"}],
                config={
                    "agents": {
                        "defaults": {
                            "models": {
                                "anthropic/claude-3.7-sonnet": {"alias": "sonnet"}
                            }
                        }
                    },
                    "models": {
                        "providers": {
                            "anthropic": {
                                "models": [
                                    {
                                        "id": "claude-3.7-sonnet",
                                        "name": "Claude 3.7 Sonnet",
                                        "contextWindow": 200_000,
                                        "reasoning": True,
                                        "input": ["text", "image"],
                                    }
                                ]
                            }
                        }
                    },
                },
            )
        ]

    payload = await GatewayModelsService(
        list_instance_views=list_instance_views
    ).build_catalog()

    assert next(
        model for model in payload["models"] if model["id"] == "claude-3.7-sonnet"
    ) == {
        "id": "claude-3.7-sonnet",
        "name": "Claude 3.7 Sonnet",
        "provider": "anthropic",
        "alias": "sonnet",
        "contextWindow": 200_000,
        "reasoning": True,
        "input": ["text", "image"],
    }
