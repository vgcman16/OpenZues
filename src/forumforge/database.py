from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from pathlib import Path


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "thread"


@dataclass(slots=True)
class ForumPost:
    id: int
    author_name: str
    author_slug: str
    body: str
    is_opener: bool
    reactions: list[str] = field(default_factory=list)
    accepted: bool = False


@dataclass(slots=True)
class ForumThread:
    slug: str
    forum_slug: str
    forum_name: str
    title: str
    author_name: str
    author_slug: str
    body: str
    tags: list[str]
    posts: list[ForumPost]
    locked: bool = False


@dataclass(slots=True)
class ModerationQueueEntry:
    title: str
    note: str


class ForumForgeDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._initialized = False
        self._lock = asyncio.Lock()
        self._next_post_id = 1
        self._forums = {
            "product-strategy": "Product Strategy",
            "build-systems": "Build Systems",
        }
        self._threads: dict[str, ForumThread] = {}
        self._member_names: dict[str, str] = {}
        self._member_inbox: dict[str, list[str]] = {}
        self._moderation_queue: list[ModerationQueueEntry] = []

    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._seed_data()
            self._initialized = True

    async def list_home_threads(self) -> list[dict[str, str]]:
        await self.initialize()
        return [
            {
                "slug": thread.slug,
                "forum_name": thread.forum_name,
                "title": thread.title,
            }
            for thread in self._threads.values()
        ]

    async def create_thread(
        self,
        forum_slug: str,
        *,
        author_name: str,
        title: str,
        body: str,
        tags: str,
    ) -> dict[str, str]:
        await self.initialize()
        async with self._lock:
            forum_name = self._forums[forum_slug]
            author_slug = _slugify(author_name)
            self._member_names[author_slug] = author_name
            slug = self._unique_thread_slug(title)
            opener = ForumPost(
                id=self._allocate_post_id(),
                author_name=author_name,
                author_slug=author_slug,
                body=body,
                is_opener=True,
            )
            thread = ForumThread(
                slug=slug,
                forum_slug=forum_slug,
                forum_name=forum_name,
                title=title,
                author_name=author_name,
                author_slug=author_slug,
                body=body,
                tags=[part.strip() for part in tags.split(",") if part.strip()],
                posts=[opener],
            )
            self._threads[slug] = thread
            return {"slug": slug, "title": title}

    async def search(self, query: str) -> list[dict[str, str]]:
        await self.initialize()
        wanted = query.strip().lower()
        if not wanted:
            return []
        matches: list[dict[str, str]] = []
        for thread in self._threads.values():
            haystacks = [
                thread.title.lower(),
                thread.body.lower(),
                " ".join(thread.tags).lower(),
                " ".join(post.body.lower() for post in thread.posts),
            ]
            if any(wanted in haystack for haystack in haystacks):
                matches.append({"slug": thread.slug, "title": thread.title})
        return matches

    async def thread_view(self, slug: str) -> dict[str, object] | None:
        await self.initialize()
        thread = self._threads.get(slug)
        if thread is None:
            return None
        return {
            "slug": thread.slug,
            "title": thread.title,
            "locked": thread.locked,
            "posts": [
                {
                    "id": post.id,
                    "author_name": post.author_name,
                    "author_slug": post.author_slug,
                    "body": post.body,
                    "is_opener": post.is_opener,
                    "reactions": list(post.reactions),
                    "accepted": post.accepted,
                }
                for post in thread.posts
            ],
        }

    async def add_reply(self, slug: str, *, author_name: str, body: str) -> dict[str, object]:
        await self.initialize()
        async with self._lock:
            thread = self._threads[slug]
            author_slug = _slugify(author_name)
            self._member_names[author_slug] = author_name
            reply = ForumPost(
                id=self._allocate_post_id(),
                author_name=author_name,
                author_slug=author_slug,
                body=body,
                is_opener=False,
            )
            thread.posts.append(reply)
            self._member_inbox.setdefault(thread.author_slug, []).append(
                f"New reply on your thread: {thread.title}"
            )
            return {"post_id": reply.id}

    async def add_reaction(self, slug: str, post_id: int, kind: str) -> None:
        await self.initialize()
        async with self._lock:
            post = self._find_post(self._threads[slug], post_id)
            post.reactions.append(kind)

    async def accept_answer(self, slug: str, post_id: int) -> None:
        await self.initialize()
        async with self._lock:
            thread = self._threads[slug]
            post = self._find_post(thread, post_id)
            post.accepted = True
            self._member_inbox.setdefault(thread.author_slug, []).append(
                f"Accepted answer on your thread: {thread.title}"
            )

    async def moderate_thread(self, slug: str, state: str) -> None:
        await self.initialize()
        async with self._lock:
            thread = self._threads[slug]
            if state == "locked":
                thread.locked = True
                self._upsert_queue_entry(thread.title, "Locked thread needs follow-up")

    async def member_view(self, member_slug: str) -> dict[str, str]:
        await self.initialize()
        display_name = self._member_names.get(
            member_slug,
            " ".join(part.capitalize() for part in member_slug.split("-") if part),
        )
        return {"slug": member_slug, "name": display_name}

    async def member_inbox(self, member_slug: str) -> list[str]:
        await self.initialize()
        return list(self._member_inbox.get(member_slug, []))

    async def moderation_queue(self) -> list[dict[str, str]]:
        await self.initialize()
        return [{"title": item.title, "note": item.note} for item in self._moderation_queue]

    def _seed_data(self) -> None:
        self._seed_thread(
            forum_slug="product-strategy",
            author_name="Atlas",
            title="How we turned release notes into canonical rollout playbooks",
            body=(
                "A writeup on turning release notes into trusted rollout playbooks "
                "without losing operational nuance."
            ),
            tags=["rollouts", "playbooks"],
        )
        self._member_inbox["atlas"] = [
            (
                "New reply on your thread: "
                "How we turned release notes into canonical rollout playbooks"
            ),
            (
                "Accepted answer on your thread: "
                "How we turned release notes into canonical rollout playbooks"
            ),
        ]
        self._seed_queue_thread(
            "build-systems",
            "Pattern for deployments that self-report drift before customers feel it",
            "Deploy Bot",
            "Capture drift signals before the incident report starts writing itself.",
            "Needs moderator review",
        )
        self._seed_queue_thread(
            "build-systems",
            "High-signal live thread needs moderator guidance",
            "Queue Watcher",
            "A fast-moving thread needs moderator guidance before it fragments.",
            "High-signal live thread needs moderator guidance",
        )
        self._seed_queue_thread(
            "build-systems",
            "Stale unresolved thread needs a nudge",
            "Queue Watcher",
            "An unresolved thread has gone quiet and needs a moderator nudge.",
            "Stale unresolved thread needs a nudge",
        )

    def _seed_thread(
        self,
        *,
        forum_slug: str,
        author_name: str,
        title: str,
        body: str,
        tags: list[str],
    ) -> None:
        author_slug = _slugify(author_name)
        self._member_names[author_slug] = author_name
        slug = self._unique_thread_slug(title)
        opener = ForumPost(
            id=self._allocate_post_id(),
            author_name=author_name,
            author_slug=author_slug,
            body=body,
            is_opener=True,
        )
        self._threads[slug] = ForumThread(
            slug=slug,
            forum_slug=forum_slug,
            forum_name=self._forums[forum_slug],
            title=title,
            author_name=author_name,
            author_slug=author_slug,
            body=body,
            tags=tags,
            posts=[opener],
        )

    def _seed_queue_thread(
        self,
        forum_slug: str,
        title: str,
        author_name: str,
        body: str,
        note: str,
    ) -> None:
        self._seed_thread(
            forum_slug=forum_slug,
            author_name=author_name,
            title=title,
            body=body,
            tags=["moderation"],
        )
        self._moderation_queue.append(ModerationQueueEntry(title=title, note=note))

    def _unique_thread_slug(self, title: str) -> str:
        base = _slugify(title)
        candidate = base
        suffix = 2
        while candidate in self._threads:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    def _allocate_post_id(self) -> int:
        post_id = self._next_post_id
        self._next_post_id += 1
        return post_id

    def _find_post(self, thread: ForumThread, post_id: int) -> ForumPost:
        for post in thread.posts:
            if post.id == post_id:
                return post
        raise KeyError(post_id)

    def _upsert_queue_entry(self, title: str, note: str) -> None:
        for entry in self._moderation_queue:
            if entry.title == title:
                entry.note = note
                return
        self._moderation_queue.append(ModerationQueueEntry(title=title, note=note))
