from __future__ import annotations

import json
from urllib.request import Request

import pytest

from openzues.services.gateway_model_scan import GatewayModelScanService


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


@pytest.mark.asyncio
async def test_gateway_model_scan_live_probe_posts_tool_and_image_requests(
    monkeypatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-test")
    requests: list[dict[str, object]] = []

    def fake_urlopen(request: Request, *, timeout: float) -> FakeResponse:
        body = json.loads((request.data or b"{}").decode("utf-8"))
        requests.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "authorization": request.get_header("Authorization"),
                "body": body,
            }
        )
        if request.full_url.endswith("/models"):
            return FakeResponse(
                {
                    "data": [
                        {
                            "id": "acme/vision-tools:free",
                            "name": "Acme Vision Tools 70B",
                            "context_length": 131072,
                            "supported_parameters": ["tools"],
                            "modality": "text+image",
                            "pricing": {"prompt": "0", "completion": "0"},
                        },
                        {
                            "id": "acme/text-tools:free",
                            "name": "Acme Text Tools 8B",
                            "context_length": 32768,
                            "supported_parameters": ["tools"],
                            "modality": "text",
                            "pricing": {"prompt": "0", "completion": "0"},
                        },
                    ]
                }
            )
        if "tools" in body:
            return FakeResponse(
                {"choices": [{"message": {"tool_calls": [{"function": {"name": "ping"}}]}}]}
            )
        return FakeResponse({"choices": [{"message": {"content": "OK"}}]})

    service = GatewayModelScanService(urlopen_impl=fake_urlopen)

    results = await service.scan(probe=True, timeout_ms=2500)

    assert [result["modelRef"] for result in results] == [
        "openrouter/acme/vision-tools:free",
        "openrouter/acme/text-tools:free",
    ]
    assert results[0]["tool"]["ok"] is True
    assert results[0]["image"]["ok"] is True
    assert results[1]["tool"]["ok"] is True
    assert results[1]["image"] == {"ok": False, "latencyMs": None, "skipped": True}
    assert [request["url"] for request in requests] == [
        "https://openrouter.ai/api/v1/models",
        "https://openrouter.ai/api/v1/chat/completions",
        "https://openrouter.ai/api/v1/chat/completions",
        "https://openrouter.ai/api/v1/chat/completions",
    ]
    assert requests[1]["authorization"] == "Bearer sk-openrouter-test"
    tool_body = requests[1]["body"]
    assert tool_body["model"] == "acme/vision-tools:free"
    assert tool_body["tool_choice"] == "required"
    image_body = requests[2]["body"]
    content = image_body["messages"][0]["content"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
