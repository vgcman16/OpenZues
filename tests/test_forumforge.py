from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from forumforge.app import create_app
from forumforge.settings import Settings


def make_client(tmp_path) -> TestClient:
    app_settings = Settings(
        data_dir=tmp_path / "forumforge-data",
        db_path=tmp_path / "forumforge-data" / "forumforge.db",
    )
    app = create_app(app_settings)
    return TestClient(app)


def test_home_page_renders_seed_content(tmp_path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "ForumForge" in response.text
    assert "How we turned release notes into canonical rollout playbooks" in response.text
    assert "Product Strategy" in response.text


def test_create_thread_and_search_flow(tmp_path) -> None:
    with make_client(tmp_path) as client:
        publish = client.post(
            "/forums/product-strategy/threads",
            data={
                "author_name": "Nova Sprint",
                "title": "Operator handbook for launch freeze weekends",
                "body": (
                    "We need a shared checklist for freeze weekends, escalation paths, and "
                    "verification before promotion."
                ),
                "tags": "launch, verification, ops",
            },
        )
        search = client.get("/search", params={"q": "freeze weekends"})
        profile = client.get("/members/nova-sprint")
        inbox = client.get("/members/nova-sprint/inbox")

    assert publish.status_code == 200
    assert "Thread published." in publish.text
    assert "Operator handbook for launch freeze weekends" in search.text
    assert profile.status_code == 200
    assert "Nova Sprint" in profile.text
    assert inbox.status_code == 200
    assert "No private updates yet." in inbox.text


def test_seeded_inbox_and_queue_render(tmp_path) -> None:
    with make_client(tmp_path) as client:
        inbox = client.get("/members/atlas/inbox")
        queue = client.get("/moderation/queue")

    assert inbox.status_code == 200
    assert "Private inbox" in inbox.text
    assert "New reply on your thread" in inbox.text
    assert "Accepted answer on your thread" in inbox.text
    assert "How we turned release notes into canonical rollout playbooks" in inbox.text

    assert queue.status_code == 200
    assert "Moderation queue" in queue.text
    assert "Pattern for deployments that self-report drift before customers feel it" in queue.text
    assert "High-signal live thread needs moderator guidance" in queue.text
    assert "Stale unresolved thread needs a nudge" in queue.text


def test_reply_react_answer_and_moderate_thread(tmp_path) -> None:
    with make_client(tmp_path) as client:
        publish = client.post(
            "/forums/build-systems/threads",
            data={
                "author_name": "Lane Keeper",
                "title": "Checklist for recovering a noisy deployment lane",
                "body": (
                    "Document the quickest path to verify the lane, isolate drift, and decide "
                    "whether to roll forward or restore."
                ),
                "tags": "deploys, reliability",
            },
        )
        assert publish.status_code == 200

        payload = asyncio.run(client.app.state.database.search("noisy deployment lane"))
        slug = payload[0]["slug"]

        reply = client.post(
            f"/threads/{slug}/reply",
            data={
                "author_name": "Mira Chen",
                "body": (
                    "Start with health checks, then compare migration state and queue lag "
                    "before deciding whether the lane is safe."
                ),
            },
        )
        thread_payload = asyncio.run(client.app.state.database.thread_view(slug))
        assert thread_payload is not None
        reply_post = next(post for post in thread_payload["posts"] if not post["is_opener"])

        reaction = client.post(
            f"/threads/{slug}/react/{reply_post['id']}",
            data={"kind": "insight"},
        )
        answer = client.post(f"/threads/{slug}/answer/{reply_post['id']}")
        lock = client.post(f"/threads/{slug}/moderate/locked")
        thread_page = client.get(f"/threads/{slug}")
        queue = client.get("/moderation/queue")

    assert reply.status_code == 200
    assert reaction.status_code == 200
    assert answer.status_code == 200
    assert lock.status_code == 200
    assert "Accepted answer" in thread_page.text
    assert "Locked" in thread_page.text
    assert "insight" in thread_page.text.lower()
    assert "Checklist for recovering a noisy deployment lane" in queue.text
    assert "Locked thread needs follow-up" in queue.text
