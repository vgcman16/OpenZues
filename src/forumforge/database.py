from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "topic"


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def describe_relative(value: str | None) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return "just now"
    delta = datetime.now(UTC) - parsed
    minutes = max(0, int(delta.total_seconds() // 60))
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w ago"
    months = max(1, days // 30)
    return f"{months}mo ago"


def _excerpt(value: str, limit: int = 180) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: max(0, limit - 1)].rstrip() + "..."


def _split_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _join_tags(tags: list[str]) -> str:
    return ",".join(sorted({tag.strip().lower() for tag in tags if tag.strip()}))


def _signal_score(thread: dict[str, Any]) -> int:
    freshness = _parse_timestamp(thread.get("last_posted_at"))
    age_hours = 24.0
    if freshness is not None:
        age_hours = max(1.0, (datetime.now(UTC) - freshness).total_seconds() / 3600)
    score = (
        int(thread.get("reply_count") or 0) * 7
        + int(thread.get("reaction_score") or 0) * 5
        + (18 if thread.get("pinned") else 0)
        + (22 if thread.get("canonical") else 0)
        + (14 if thread.get("state") == "solved" else 0)
    )
    return max(1, int(round(score - min(age_hours * 0.8, 36))))


def _heat_label(score: int) -> str:
    if score >= 70:
        return "Electric"
    if score >= 42:
        return "Hot"
    if score >= 24:
        return "Rising"
    return "Quiet"


SCHEMA = """
CREATE TABLE IF NOT EXISTS forums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    summary TEXT NOT NULL,
    accent TEXT NOT NULL,
    hero TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    bio TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'member',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forum_id INTEGER NOT NULL REFERENCES forums(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    body TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL DEFAULT 'open',
    pinned INTEGER NOT NULL DEFAULT 0,
    locked INTEGER NOT NULL DEFAULT 0,
    canonical INTEGER NOT NULL DEFAULT 0,
    solved_post_id INTEGER,
    view_count INTEGER NOT NULL DEFAULT 0,
    reply_count INTEGER NOT NULL DEFAULT 0,
    reaction_score INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_posted_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    body TEXT NOT NULL,
    is_answer INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS post_reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(post_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_threads_forum_last_posted
ON threads(forum_id, last_posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_threads_state
ON threads(state, last_posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_posts_thread_created
ON posts(thread_id, created_at ASC);
"""


class ForumDatabase:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            await db.executescript(SCHEMA)
            await self._seed(db)
            await db.commit()

    async def _fetchone(
        self,
        db: aiosqlite.Connection,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> aiosqlite.Row | None:
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return row

    async def _fetchall(
        self,
        db: aiosqlite.Connection,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[aiosqlite.Row]:
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return list(rows)

    async def _seed(self, db: aiosqlite.Connection) -> None:
        existing = await self._fetchone(db, "SELECT COUNT(*) AS count FROM forums")
        if existing is not None and int(existing["count"]) > 0:
            return

        now = datetime.now(UTC)
        forums = [
            (
                "product-strategy",
                "Product Strategy",
                (
                    "Where launch plans, roadmaps, migration playbooks, and governance "
                    "threads get sharpened."
                ),
                "#ff7b52",
                "Turn release chaos into crisp operator knowledge.",
                1,
            ),
            (
                "build-systems",
                "Build Systems",
                (
                    "CI hardening, deployment pipelines, observability, and release engineering "
                    "for people who ship every day."
                ),
                "#54c5ff",
                "A forum for the people who keep software alive after the merge.",
                2,
            ),
            (
                "design-lab",
                "Design Lab",
                (
                    "Interface systems, motion critique, typography, and user flows for "
                    "teams who care about product feel."
                ),
                "#9dffb0",
                "Make product taste operational, not subjective.",
                3,
            ),
        ]
        for slug, name, summary, accent, hero, sort_order in forums:
            await db.execute(
                """
                INSERT INTO forums (slug, name, summary, accent, hero, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (slug, name, summary, accent, hero, sort_order, utcnow()),
            )

        members = [
            (
                "atlas",
                "Atlas Vale",
                "Product lead who writes roadmap notes like incident reports.",
                "operator",
            ),
            (
                "mira",
                "Mira Chen",
                "Frontend systems designer obsessed with editorial interfaces and precise motion.",
                "designer",
            ),
            (
                "rowan",
                "Rowan Pike",
                "Platform engineer keeping deploys boring and postmortems honest.",
                "engineer",
            ),
            (
                "sable",
                "Sable Ortiz",
                "Knowledge gardener turning solved work into reusable forum signal.",
                "moderator",
            ),
        ]
        for username, display_name, bio, role in members:
            await db.execute(
                """
                INSERT INTO members (username, display_name, bio, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, display_name, bio, role, utcnow()),
            )

        await self._insert_seed_thread(
            db,
            forum_slug="product-strategy",
            author_username="atlas",
            title="How we turned release notes into canonical rollout playbooks",
            body=(
                "We stopped treating release notes as announcements and started treating them "
                "as operational memory. Each launch now ends with a canonical thread that "
                "captures scope, verification, fallbacks, and what "
                "we wish we had known before shipping."
            ),
            tags=["roadmap", "launch", "knowledge"],
            state="solved",
            pinned=True,
            canonical=True,
            view_count=248,
            created_at=now - timedelta(days=2, hours=6),
            replies=[
                {
                    "author": "sable",
                    "body": (
                        "The key move was forcing every ship thread to end with truths, drift, "
                        "next step, blockers. "
                        "That made each launch searchable as a decision artifact instead of a "
                        "chat log."
                    ),
                    "created_at": now - timedelta(days=2, hours=3),
                    "is_answer": True,
                    "reactions": {"upvote": 12, "insight": 7},
                },
                {
                    "author": "mira",
                    "body": (
                        "We also started pulling the visual deltas into the same thread so "
                        "product, design, and "
                        "support were reacting to one canonical source."
                    ),
                    "created_at": now - timedelta(days=2, hours=1),
                    "reactions": {"upvote": 6, "thanks": 5},
                },
            ],
            opener_reactions={"upvote": 9, "insight": 3},
        )
        await self._insert_seed_thread(
            db,
            forum_slug="build-systems",
            author_username="rowan",
            title="Pattern for deployments that self-report drift before customers feel it",
            body=(
                "We built a release gate that compares migration state, health checks, and queue "
                "lag before a deploy is declared healthy. If the lane smells wrong, the forum "
                "thread gets a pulse update automatically."
            ),
            tags=["deploys", "observability", "ci"],
            state="open",
            pinned=False,
            canonical=False,
            view_count=179,
            created_at=now - timedelta(hours=18),
            replies=[
                {
                    "author": "atlas",
                    "body": (
                        "The part I want next is a human-readable relay packet for each deploy. "
                        "Raw logs are still too "
                        "expensive to parse under pressure."
                    ),
                    "created_at": now - timedelta(hours=14),
                    "reactions": {"upvote": 4, "insight": 2},
                },
                {
                    "author": "sable",
                    "body": (
                        "Thread-level checkpoints could solve that. The forum should capture the "
                        "operator version of "
                        "what is true, what is drifting, and what needs verifying."
                    ),
                    "created_at": now - timedelta(hours=10),
                    "reactions": {"upvote": 5, "thanks": 3},
                },
            ],
            opener_reactions={"upvote": 7},
        )
        await self._insert_seed_thread(
            db,
            forum_slug="design-lab",
            author_username="mira",
            title="What makes a community thread feel editorial instead of archival",
            body=(
                "Most forums make important conversations look the same as dead ones. We want "
                "typography, spacing, "
                "and motion to tell you what deserves attention before you read a word."
            ),
            tags=["interface", "typography", "ux"],
            state="solved",
            pinned=False,
            canonical=True,
            view_count=212,
            created_at=now - timedelta(days=5, hours=4),
            replies=[
                {
                    "author": "atlas",
                    "body": (
                        "Strong hierarchy plus a live context rail changed our read-time "
                        "completely. People stopped "
                        "missing the accepted answer because the layout finally respected "
                        "importance."
                    ),
                    "created_at": now - timedelta(days=5, hours=3),
                    "reactions": {"upvote": 8, "insight": 5},
                },
                {
                    "author": "mira",
                    "body": (
                        "My working rule: treat the thread opener like an editorial lead, "
                        "accepted answers like a "
                        "pull-quote, and side context like an issue desk."
                    ),
                    "created_at": now - timedelta(days=5, hours=2),
                    "is_answer": True,
                    "reactions": {"upvote": 11, "thanks": 4},
                },
            ],
            opener_reactions={"upvote": 10, "insight": 4},
        )
        await self._insert_seed_thread(
            db,
            forum_slug="build-systems",
            author_username="rowan",
            title="Should incident threads auto-promote into a knowledge capsule after resolution?",
            body=(
                "We keep solving the same outage classes. I want a workflow where resolved "
                "incident threads can turn "
                "into durable knowledge capsules without forcing someone to rewrite everything "
                "from scratch."
            ),
            tags=["incident", "automation", "knowledge"],
            state="open",
            pinned=False,
            canonical=False,
            view_count=133,
            created_at=now - timedelta(days=7, hours=9),
            replies=[
                {
                    "author": "sable",
                    "body": (
                        "Yes, but only if the accepted answer is rewritten into relay language "
                        "first. The capsule "
                        "needs truths, triggers, guardrails, and verification."
                    ),
                    "created_at": now - timedelta(days=7, hours=8),
                    "reactions": {"upvote": 7},
                }
            ],
            opener_reactions={"upvote": 4, "insight": 2},
        )

    async def _insert_seed_thread(
        self,
        db: aiosqlite.Connection,
        *,
        forum_slug: str,
        author_username: str,
        title: str,
        body: str,
        tags: list[str],
        state: str,
        pinned: bool,
        canonical: bool,
        view_count: int,
        created_at: datetime,
        replies: list[dict[str, Any]],
        opener_reactions: dict[str, int] | None = None,
    ) -> None:
        forum = await self._fetchone(db, "SELECT id FROM forums WHERE slug = ?", (forum_slug,))
        author = await self._fetchone(
            db,
            "SELECT id FROM members WHERE username = ?",
            (author_username,),
        )
        if forum is None or author is None:
            raise RuntimeError("Seed references missing forum or author.")

        slug = await self._unique_slug(db, "threads", slugify(title))
        created_iso = created_at.isoformat()
        last_posted_at = replies[-1]["created_at"].isoformat() if replies else created_iso
        thread_cursor = await db.execute(
            """
            INSERT INTO threads (
                forum_id,
                author_id,
                slug,
                title,
                excerpt,
                body,
                tags,
                state,
                pinned,
                locked,
                canonical,
                view_count,
                reply_count,
                reaction_score,
                created_at,
                updated_at,
                last_posted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                int(forum["id"]),
                int(author["id"]),
                slug,
                title,
                _excerpt(body),
                body,
                _join_tags(tags),
                state,
                int(pinned),
                int(canonical),
                view_count,
                len(replies),
                created_iso,
                last_posted_at,
                last_posted_at,
            ),
        )
        if thread_cursor.lastrowid is None:
            raise RuntimeError("Failed to create seed thread.")
        thread_id = int(thread_cursor.lastrowid)
        opener_cursor = await db.execute(
            """
            INSERT INTO posts (thread_id, author_id, body, is_answer, created_at, updated_at)
            VALUES (?, ?, ?, 0, ?, ?)
            """,
            (thread_id, int(author["id"]), body, created_iso, created_iso),
        )
        if opener_cursor.lastrowid is None:
            raise RuntimeError("Failed to create seed opener post.")
        opener_id = int(opener_cursor.lastrowid)
        reaction_score = 0
        if opener_reactions:
            reaction_score += await self._apply_reactions(db, opener_id, opener_reactions)

        accepted_post_id: int | None = None
        for reply in replies:
            reply_author = await self._fetchone(
                db,
                "SELECT id FROM members WHERE username = ?",
                (str(reply["author"]),),
            )
            if reply_author is None:
                raise RuntimeError("Seed reply references missing author.")
            reply_iso = reply["created_at"].isoformat()
            post_cursor = await db.execute(
                """
                INSERT INTO posts (thread_id, author_id, body, is_answer, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    int(reply_author["id"]),
                    str(reply["body"]),
                    int(bool(reply.get("is_answer"))),
                    reply_iso,
                    reply_iso,
                ),
            )
            if post_cursor.lastrowid is None:
                raise RuntimeError("Failed to create seed reply post.")
            post_id = int(post_cursor.lastrowid)
            reaction_score += await self._apply_reactions(
                db,
                post_id,
                dict(reply.get("reactions") or {}),
            )
            if reply.get("is_answer"):
                accepted_post_id = post_id

        await db.execute(
            """
            UPDATE threads
            SET solved_post_id = ?, reaction_score = ?, state = ?, canonical = ?
            WHERE id = ?
            """,
            (
                accepted_post_id,
                reaction_score,
                "solved" if accepted_post_id is not None else state,
                int(canonical),
                thread_id,
            ),
        )

    async def _apply_reactions(
        self,
        db: aiosqlite.Connection,
        post_id: int,
        reactions: dict[str, int],
    ) -> int:
        total = 0
        for kind, count in reactions.items():
            total += int(count)
            await db.execute(
                """
                INSERT INTO post_reactions (post_id, kind, count)
                VALUES (?, ?, ?)
                """,
                (post_id, kind, int(count)),
            )
        return total

    async def _unique_slug(
        self,
        db: aiosqlite.Connection,
        table: str,
        base_slug: str,
    ) -> str:
        slug = base_slug
        index = 2
        while True:
            row = await self._fetchone(
                db,
                f"SELECT 1 FROM {table} WHERE slug = ? LIMIT 1",
                (slug,),
            )
            if row is None:
                return slug
            slug = f"{base_slug}-{index}"
            index += 1

    def _decorate_thread(self, row: aiosqlite.Row) -> dict[str, Any]:
        thread = dict(row)
        thread["tags"] = _split_tags(thread.get("tags"))
        thread["freshness"] = describe_relative(str(thread.get("last_posted_at") or ""))
        thread["created_freshness"] = describe_relative(str(thread.get("created_at") or ""))
        thread["signal_score"] = _signal_score(thread)
        thread["heat_label"] = _heat_label(thread["signal_score"])
        thread["state_label"] = "Solved" if thread.get("state") == "solved" else "Live"
        thread["reply_label"] = (
            f"{int(thread.get('reply_count') or 0)} "
            f"{'reply' if int(thread.get('reply_count') or 0) == 1 else 'replies'}"
        )
        thread["view_label"] = f"{int(thread.get('view_count') or 0)} views"
        return thread

    async def _list_threads(
        self,
        *,
        forum_slug: str | None = None,
        sort: str = "latest",
        q: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["1 = 1"]
        params: list[Any] = []
        if forum_slug:
            clauses.append("f.slug = ?")
            params.append(forum_slug)
        if q:
            wildcard = f"%{q.lower()}%"
            clauses.append(
                """
                (
                    lower(t.title) LIKE ?
                    OR lower(t.excerpt) LIKE ?
                    OR lower(t.body) LIKE ?
                    OR lower(t.tags) LIKE ?
                )
                """
            )
            params.extend([wildcard, wildcard, wildcard, wildcard])
        query = f"""
            SELECT
                t.*,
                f.slug AS forum_slug,
                f.name AS forum_name,
                f.accent AS forum_accent,
                m.username AS author_username,
                m.display_name AS author_name,
                m.role AS author_role
            FROM threads t
            JOIN forums f ON f.id = t.forum_id
            JOIN members m ON m.id = t.author_id
            WHERE {" AND ".join(clauses)}
        """
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await self._fetchall(db, query, tuple(params))
        threads = [self._decorate_thread(row) for row in rows]

        if sort == "signal":
            threads.sort(
                key=lambda item: (
                    -int(item["signal_score"]),
                    -int(item["pinned"]),
                    str(item["last_posted_at"]),
                )
            )
        elif sort == "unanswered":
            threads = [
                item
                for item in threads
                if int(item["reply_count"]) == 0 and item["state"] != "solved"
            ]
            threads.sort(key=lambda item: str(item["last_posted_at"]), reverse=True)
        elif sort == "knowledge":
            threads = [item for item in threads if item["canonical"] or item["state"] == "solved"]
            threads.sort(
                key=lambda item: (
                    -int(item["canonical"]),
                    -int(item["signal_score"]),
                    str(item["last_posted_at"]),
                )
            )
        else:
            threads.sort(
                key=lambda item: (
                    -int(item["pinned"]),
                    str(item["last_posted_at"]),
                ),
                reverse=True,
            )
        if limit is not None:
            return threads[:limit]
        return threads

    async def list_forums(self) -> list[dict[str, Any]]:
        query = """
            SELECT
                f.*,
                COUNT(t.id) AS thread_count,
                COALESCE(SUM(CASE WHEN t.state = 'solved' THEN 1 ELSE 0 END), 0) AS solved_count,
                MAX(t.last_posted_at) AS last_posted_at
            FROM forums f
            LEFT JOIN threads t ON t.forum_id = f.id
            GROUP BY f.id
            ORDER BY f.sort_order ASC, f.name ASC
        """
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await self._fetchall(db, query)
        forums: list[dict[str, Any]] = []
        for row in rows:
            forum = dict(row)
            forum["freshness"] = describe_relative(str(forum.get("last_posted_at") or ""))
            forums.append(forum)
        return forums

    async def get_forum(self, slug: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            row = await self._fetchone(
                db,
                "SELECT * FROM forums WHERE slug = ? LIMIT 1",
                (slug,),
            )
        return dict(row) if row is not None else None

    async def home_view(self) -> dict[str, Any]:
        forums = await self.list_forums()
        trending = await self._list_threads(sort="signal", limit=6)
        knowledge = await self._list_threads(sort="knowledge", limit=4)
        resurfacing: list[dict[str, Any]] = []
        for thread in await self._list_threads(sort="signal"):
            last_posted_at = _parse_timestamp(str(thread.get("last_posted_at") or ""))
            if last_posted_at is None:
                continue
            if (datetime.now(UTC) - last_posted_at).days >= 4:
                resurfacing.append(thread)
            if len(resurfacing) >= 4:
                break

        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            stats_row = await self._fetchone(
                db,
                """
                SELECT
                    (SELECT COUNT(*) FROM threads) AS thread_count,
                    (SELECT COUNT(*) FROM posts) AS post_count,
                    (SELECT COUNT(*) FROM members) AS member_count,
                    (SELECT COUNT(*) FROM threads WHERE state = 'solved') AS solved_count
                """,
            )
            recent_posts = await self._fetchall(
                db,
                """
                SELECT
                    p.id,
                    p.body,
                    p.created_at,
                    m.display_name AS author_name,
                    m.username AS author_username,
                    t.title AS thread_title,
                    t.slug AS thread_slug,
                    f.name AS forum_name,
                    f.slug AS forum_slug
                FROM posts p
                JOIN members m ON m.id = p.author_id
                JOIN threads t ON t.id = p.thread_id
                JOIN forums f ON f.id = t.forum_id
                ORDER BY p.created_at DESC
                LIMIT 6
                """,
            )
            contributors = await self._fetchall(
                db,
                """
                SELECT
                    m.username,
                    m.display_name,
                    m.bio,
                    m.role,
                    COUNT(DISTINCT t.id) AS started_threads,
                    COUNT(p.id) AS post_count
                FROM members m
                LEFT JOIN threads t ON t.author_id = m.id
                LEFT JOIN posts p ON p.author_id = m.id
                GROUP BY m.id
                ORDER BY post_count DESC, started_threads DESC, m.display_name ASC
                LIMIT 6
                """,
            )

        stats = dict(stats_row or {})
        activity = []
        for row in recent_posts:
            item = dict(row)
            item["excerpt"] = _excerpt(str(item["body"]), 110)
            item["freshness"] = describe_relative(str(item["created_at"]))
            activity.append(item)

        people = []
        for row in contributors:
            person = dict(row)
            person["pulse"] = (
                int(person["post_count"] or 0) * 3 + int(person["started_threads"] or 0) * 5
            )
            people.append(person)

        return {
            "stats": stats,
            "forums": forums,
            "trending": trending,
            "knowledge": knowledge,
            "resurfacing": resurfacing,
            "activity": activity,
            "contributors": people,
        }

    async def forum_view(
        self,
        forum_slug: str,
        *,
        q: str | None = None,
        sort: str = "latest",
    ) -> dict[str, Any] | None:
        forum = await self.get_forum(forum_slug)
        if forum is None:
            return None
        threads = await self._list_threads(forum_slug=forum_slug, q=q, sort=sort)
        forum["threads"] = threads
        forum["thread_count"] = len(threads)
        forum["sort"] = sort
        forum["query"] = q or ""
        return forum

    async def _post_reactions(
        self,
        db: aiosqlite.Connection,
        post_ids: list[int],
    ) -> dict[int, list[dict[str, Any]]]:
        if not post_ids:
            return {}
        placeholders = ", ".join("?" for _ in post_ids)
        rows = await self._fetchall(
            db,
            f"""
            SELECT post_id, kind, count
            FROM post_reactions
            WHERE post_id IN ({placeholders})
            ORDER BY count DESC, kind ASC
            """,
            tuple(post_ids),
        )
        payload: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            payload.setdefault(int(row["post_id"]), []).append(dict(row))
        return payload

    async def thread_view(self, slug: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                "UPDATE threads SET view_count = view_count + 1 WHERE slug = ?",
                (slug,),
            )
            await db.commit()
            thread_row = await self._fetchone(
                db,
                """
                SELECT
                    t.*,
                    f.slug AS forum_slug,
                    f.name AS forum_name,
                    f.accent AS forum_accent,
                    f.summary AS forum_summary,
                    m.username AS author_username,
                    m.display_name AS author_name,
                    m.role AS author_role
                FROM threads t
                JOIN forums f ON f.id = t.forum_id
                JOIN members m ON m.id = t.author_id
                WHERE t.slug = ?
                LIMIT 1
                """,
                (slug,),
            )
            if thread_row is None:
                return None
            posts = await self._fetchall(
                db,
                """
                SELECT
                    p.*,
                    m.username AS author_username,
                    m.display_name AS author_name,
                    m.role AS author_role
                FROM posts p
                JOIN members m ON m.id = p.author_id
                WHERE p.thread_id = ?
                ORDER BY p.created_at ASC, p.id ASC
                """,
                (int(thread_row["id"]),),
            )
            reactions = await self._post_reactions(db, [int(post["id"]) for post in posts])

        thread = self._decorate_thread(thread_row)
        thread_posts: list[dict[str, Any]] = []
        for index, row in enumerate(posts):
            post = dict(row)
            post["freshness"] = describe_relative(str(post["created_at"]))
            post["excerpt"] = _excerpt(str(post["body"]), 160)
            post["reactions"] = reactions.get(int(post["id"]), [])
            post["reaction_total"] = sum(int(item["count"]) for item in post["reactions"])
            post["is_opener"] = index == 0
            thread_posts.append(post)

        related = [
            item
            for item in await self._list_threads(
                forum_slug=str(thread["forum_slug"]),
                sort="signal",
            )
            if item["slug"] != slug
        ][:4]

        return {
            "thread": thread,
            "posts": thread_posts,
            "related": related,
        }

    async def search(self, q: str) -> list[dict[str, Any]]:
        if not q.strip():
            return []
        return await self._list_threads(q=q, sort="signal", limit=20)

    async def inbox_view(self, username: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            member = await self._fetchone(
                db,
                "SELECT * FROM members WHERE username = ? LIMIT 1",
                (username,),
            )
            if member is None:
                return None

            member_id = int(member["id"])
            thread_replies = await self._fetchall(
                db,
                """
                SELECT
                    p.created_at,
                    p.body,
                    p.is_answer,
                    sender.username AS actor_username,
                    sender.display_name AS actor_name,
                    sender.role AS actor_role,
                    t.slug AS thread_slug,
                    t.title AS thread_title,
                    f.slug AS forum_slug,
                    f.name AS forum_name
                FROM posts p
                JOIN threads t ON t.id = p.thread_id
                JOIN forums f ON f.id = t.forum_id
                JOIN members sender ON sender.id = p.author_id
                WHERE t.author_id = ?
                  AND sender.id != ?
                  AND p.id != (
                      SELECT MIN(opener.id)
                      FROM posts opener
                      WHERE opener.thread_id = t.id
                  )
                ORDER BY p.created_at DESC
                LIMIT 12
                """,
                (member_id, member_id),
            )
            accepted_answers = await self._fetchall(
                db,
                """
                SELECT
                    t.updated_at AS created_at,
                    p.body,
                    owner.username AS actor_username,
                    owner.display_name AS actor_name,
                    owner.role AS actor_role,
                    t.slug AS thread_slug,
                    t.title AS thread_title,
                    f.slug AS forum_slug,
                    f.name AS forum_name
                FROM posts p
                JOIN threads t ON t.id = p.thread_id
                JOIN forums f ON f.id = t.forum_id
                JOIN members owner ON owner.id = t.author_id
                WHERE p.author_id = ?
                  AND owner.id != ?
                  AND p.is_answer = 1
                ORDER BY t.updated_at DESC
                LIMIT 12
                """,
                (member_id, member_id),
            )

        items: list[dict[str, Any]] = []
        for row in thread_replies:
            item = dict(row)
            item["kind"] = "answer" if bool(item["is_answer"]) else "reply"
            item["headline"] = (
                "Accepted answer on your thread"
                if item["kind"] == "answer"
                else "New reply on your thread"
            )
            item["summary"] = (
                f"{item['actor_name']} resolved {item['thread_title']}."
                if item["kind"] == "answer"
                else f"{item['actor_name']} replied in {item['thread_title']}."
            )
            item["freshness"] = describe_relative(str(item["created_at"]))
            item["excerpt"] = _excerpt(str(item["body"]), 132)
            items.append(item)

        for row in accepted_answers:
            item = dict(row)
            item["kind"] = "accepted"
            item["headline"] = "Your reply was marked as accepted answer"
            item["summary"] = f"{item['actor_name']} marked your reply as the thread answer."
            item["freshness"] = describe_relative(str(item["created_at"]))
            item["excerpt"] = _excerpt(str(item["body"]), 132)
            items.append(item)

        items.sort(key=lambda item: str(item["created_at"]), reverse=True)
        inbox = dict(member)
        inbox["messages"] = items[:12]
        inbox["reply_count"] = sum(1 for item in items if item["kind"] == "reply")
        inbox["answer_count"] = sum(1 for item in items if item["kind"] != "reply")
        return inbox

    async def moderation_queue_view(self) -> dict[str, Any]:
        queue: list[dict[str, Any]] = []
        knowledge_candidates = 0
        locked_threads = 0

        for thread in await self._list_threads(sort="signal"):
            created_at = _parse_timestamp(str(thread.get("created_at") or ""))
            age_days = 0 if created_at is None else max(0, (datetime.now(UTC) - created_at).days)

            item: dict[str, Any] | None = None
            if bool(thread["locked"]):
                locked_threads += 1
                item = {
                    "priority": "Review",
                    "headline": "Locked thread needs follow-up",
                    "summary": (
                        "A moderator already paused this thread. Confirm whether it should reopen "
                        "with guidance or stay locked with a clearer closing note."
                    ),
                    "action": "Review lock state",
                }
            elif thread["state"] != "solved" and age_days >= 5:
                item = {
                    "priority": "Stale",
                    "headline": "Stale unresolved thread needs a nudge",
                    "summary": (
                        "This live thread has been sitting unresolved long enough that it risks "
                        "turning into archive noise without intervention."
                    ),
                    "action": "Nudge participants",
                }
            elif thread["state"] != "solved" and int(thread["signal_score"]) >= 24:
                item = {
                    "priority": "High signal",
                    "headline": "High-signal live thread needs moderator guidance",
                    "summary": (
                        "This discussion is attracting strong engagement without resolution. A "
                        "moderator should steer it toward an answer or durable next step."
                    ),
                    "action": "Guide toward resolution",
                }
            elif thread["state"] == "solved" and not bool(thread["canonical"]) and int(
                thread["signal_score"]
            ) >= 24:
                knowledge_candidates += 1
                item = {
                    "priority": "Knowledge",
                    "headline": "Solved thread could be promoted to canonical",
                    "summary": (
                        "The answer lane looks strong enough to preserve as reusable knowledge "
                        "instead of leaving it as a one-off conversation."
                    ),
                    "action": "Review promotion",
                }

            if item is None:
                continue
            queue.append({**item, "thread": thread})

        return {
            "queue_items": queue[:12],
            "stats": {
                "pending_count": len(queue),
                "locked_count": locked_threads,
                "knowledge_count": knowledge_candidates,
            },
        }

    async def profile_view(self, username: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            member = await self._fetchone(
                db,
                "SELECT * FROM members WHERE username = ? LIMIT 1",
                (username,),
            )
            if member is None:
                return None
            threads = await self._fetchall(
                db,
                """
                SELECT
                    t.*,
                    f.slug AS forum_slug,
                    f.name AS forum_name,
                    m.username AS author_username,
                    m.display_name AS author_name,
                    m.role AS author_role
                FROM threads t
                JOIN forums f ON f.id = t.forum_id
                JOIN members m ON m.id = t.author_id
                WHERE m.username = ?
                ORDER BY t.last_posted_at DESC
                LIMIT 10
                """,
                (username,),
            )
            posts = await self._fetchall(
                db,
                """
                SELECT
                    p.body,
                    p.created_at,
                    t.slug AS thread_slug,
                    t.title AS thread_title,
                    f.slug AS forum_slug,
                    f.name AS forum_name
                FROM posts p
                JOIN threads t ON t.id = p.thread_id
                JOIN forums f ON f.id = t.forum_id
                JOIN members m ON m.id = p.author_id
                WHERE m.username = ?
                ORDER BY p.created_at DESC
                LIMIT 10
                """,
                (username,),
            )
        profile = dict(member)
        profile["threads"] = [self._decorate_thread(row) for row in threads]
        profile["posts"] = [
            {
                **dict(row),
                "freshness": describe_relative(str(row["created_at"])),
                "excerpt": _excerpt(str(row["body"]), 140),
            }
            for row in posts
        ]
        return profile

    async def _ensure_member(
        self,
        db: aiosqlite.Connection,
        display_name: str,
    ) -> int:
        cleaned = " ".join(display_name.split()) or "Guest Builder"
        base_slug = slugify(cleaned)
        row = await self._fetchone(
            db,
            "SELECT id, display_name FROM members WHERE username = ? LIMIT 1",
            (base_slug,),
        )
        if row is not None and str(row["display_name"]).lower() == cleaned.lower():
            return int(row["id"])

        username = base_slug
        index = 2
        while row is not None:
            username = f"{base_slug}-{index}"
            row = await self._fetchone(
                db,
                "SELECT id FROM members WHERE username = ? LIMIT 1",
                (username,),
            )
            index += 1

        cursor = await db.execute(
            """
            INSERT INTO members (username, display_name, bio, role, created_at)
            VALUES (?, ?, '', 'member', ?)
            """,
            (username, cleaned, utcnow()),
        )
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to create member.")
        return int(cursor.lastrowid)

    async def create_thread(
        self,
        *,
        forum_slug: str,
        author_name: str,
        title: str,
        body: str,
        tags: list[str],
    ) -> str:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            forum = await self._fetchone(db, "SELECT id FROM forums WHERE slug = ?", (forum_slug,))
            if forum is None:
                raise ValueError("Unknown forum.")
            author_id = await self._ensure_member(db, author_name)
            created_at = utcnow()
            slug = await self._unique_slug(db, "threads", slugify(title))
            thread_cursor = await db.execute(
                """
                INSERT INTO threads (
                    forum_id,
                    author_id,
                    slug,
                    title,
                    excerpt,
                    body,
                    tags,
                    state,
                    pinned,
                    locked,
                    canonical,
                    view_count,
                    reply_count,
                    reaction_score,
                    created_at,
                    updated_at,
                    last_posted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'open', 0, 0, 0, 0, 0, 0, ?, ?, ?)
                """,
                (
                    int(forum["id"]),
                    author_id,
                    slug,
                    title.strip(),
                    _excerpt(body, 160),
                    body.strip(),
                    _join_tags(tags),
                    created_at,
                    created_at,
                    created_at,
                ),
            )
            if thread_cursor.lastrowid is None:
                raise RuntimeError("Failed to create thread.")
            thread_id = int(thread_cursor.lastrowid)
            await db.execute(
                """
                INSERT INTO posts (thread_id, author_id, body, is_answer, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (thread_id, author_id, body.strip(), created_at, created_at),
            )
            await db.commit()
            return slug

    async def create_reply(
        self,
        *,
        thread_slug: str,
        author_name: str,
        body: str,
    ) -> None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            thread = await self._fetchone(
                db,
                "SELECT * FROM threads WHERE slug = ?",
                (thread_slug,),
            )
            if thread is None:
                raise ValueError("Unknown thread.")
            if bool(thread["locked"]):
                raise ValueError("This thread is locked.")
            author_id = await self._ensure_member(db, author_name)
            created_at = utcnow()
            await db.execute(
                """
                INSERT INTO posts (thread_id, author_id, body, is_answer, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?)
                """,
                (int(thread["id"]), author_id, body.strip(), created_at, created_at),
            )
            await db.execute(
                """
                UPDATE threads
                SET reply_count = reply_count + 1, updated_at = ?, last_posted_at = ?
                WHERE id = ?
                """,
                (created_at, created_at, int(thread["id"])),
            )
            await db.commit()

    async def react_to_post(self, *, post_id: int, kind: str) -> str:
        reaction_kind = kind.strip().lower() or "upvote"
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            post = await self._fetchone(
                db,
                "SELECT thread_id FROM posts WHERE id = ? LIMIT 1",
                (post_id,),
            )
            if post is None:
                raise ValueError("Unknown post.")
            thread = await self._fetchone(
                db,
                "SELECT slug FROM threads WHERE id = ? LIMIT 1",
                (int(post["thread_id"]),),
            )
            await db.execute(
                """
                INSERT INTO post_reactions (post_id, kind, count)
                VALUES (?, ?, 1)
                ON CONFLICT(post_id, kind)
                DO UPDATE SET count = count + 1
                """,
                (post_id, reaction_kind),
            )
            await db.execute(
                """
                UPDATE threads
                SET reaction_score = reaction_score + 1, updated_at = ?
                WHERE id = ?
                """,
                (utcnow(), int(post["thread_id"])),
            )
            await db.commit()
            if thread is None:
                raise ValueError("Thread for post not found.")
            return str(thread["slug"])

    async def mark_answer(self, *, thread_slug: str, post_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            thread = await self._fetchone(
                db,
                "SELECT id FROM threads WHERE slug = ?",
                (thread_slug,),
            )
            if thread is None:
                raise ValueError("Unknown thread.")
            thread_id = int(thread["id"])
            post = await self._fetchone(
                db,
                "SELECT id FROM posts WHERE id = ? AND thread_id = ?",
                (post_id, thread_id),
            )
            if post is None:
                raise ValueError("Unknown reply.")
            await db.execute("UPDATE posts SET is_answer = 0 WHERE thread_id = ?", (thread_id,))
            await db.execute("UPDATE posts SET is_answer = 1 WHERE id = ?", (post_id,))
            await db.execute(
                """
                UPDATE threads
                SET solved_post_id = ?, state = 'solved', updated_at = ?
                WHERE id = ?
                """,
                (post_id, utcnow(), thread_id),
            )
            await db.commit()

    async def toggle_thread_flag(self, *, thread_slug: str, field: str) -> None:
        if field not in {"pinned", "locked", "canonical"}:
            raise ValueError("Unsupported moderator flag.")
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            thread = await self._fetchone(
                db,
                f"SELECT id, {field} FROM threads WHERE slug = ?",
                (thread_slug,),
            )
            if thread is None:
                raise ValueError("Unknown thread.")
            next_value = 0 if bool(thread[field]) else 1
            await db.execute(
                f"UPDATE threads SET {field} = ?, updated_at = ? WHERE id = ?",
                (next_value, utcnow(), int(thread["id"])),
            )
            await db.commit()
