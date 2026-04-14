from __future__ import annotations

from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse

from forumforge.database import ForumForgeDatabase
from forumforge.settings import Settings


def _page(title: str, body: str) -> HTMLResponse:
    html = (
        "<!doctype html>"
        "<html><head><meta charset='utf-8'><title>"
        f"{escape(title)}</title></head><body>"
        f"{body}</body></html>"
    )
    return HTMLResponse(html)


def _thread_page_html(thread: dict[str, object]) -> str:
    posts = thread.get("posts")
    items: list[str] = []
    if isinstance(posts, list):
        for post in posts:
            if not isinstance(post, dict):
                continue
            reactions = post.get("reactions")
            reaction_text = ""
            if isinstance(reactions, list) and reactions:
                reaction_text = f"<p>{escape(', '.join(str(item) for item in reactions))}</p>"
            accepted_text = "<p>Accepted answer</p>" if bool(post.get("accepted")) else ""
            items.append(
                "<article>"
                f"<h3>{escape(str(post.get('author_name') or 'Unknown'))}</h3>"
                f"<p>{escape(str(post.get('body') or ''))}</p>"
                f"{accepted_text}{reaction_text}"
                "</article>"
            )
    locked_text = "<p>Locked</p>" if bool(thread.get("locked")) else ""
    return (
        f"<h1>{escape(str(thread.get('title') or 'Thread'))}</h1>"
        f"{locked_text}"
        + "".join(items)
    )


def create_app(app_settings: Settings | None = None) -> FastAPI:
    settings = app_settings or Settings()
    database = ForumForgeDatabase(settings.db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        await database.initialize()
        yield

    app = FastAPI(title="ForumForge", lifespan=lifespan)
    app.state.database = database

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        threads = await database.list_home_threads()
        body = ["<h1>ForumForge</h1>"]
        for thread in threads:
            body.append(
                "<section>"
                f"<h2>{escape(thread['forum_name'])}</h2>"
                f"<p>{escape(thread['title'])}</p>"
                "</section>"
            )
        return _page("ForumForge", "".join(body))

    @app.post("/forums/{forum_slug}/threads", response_class=HTMLResponse)
    async def create_thread(
        forum_slug: str,
        author_name: str = Form(...),
        title: str = Form(...),
        body: str = Form(...),
        tags: str = Form(""),
    ) -> HTMLResponse:
        if forum_slug not in {"product-strategy", "build-systems"}:
            raise HTTPException(status_code=404, detail="Forum not found.")
        thread = await database.create_thread(
            forum_slug,
            author_name=author_name,
            title=title,
            body=body,
            tags=tags,
        )
        return _page(
            "Thread published",
            f"<h1>Thread published.</h1><p>{escape(thread['title'])}</p>",
        )

    @app.get("/search", response_class=HTMLResponse)
    async def search(q: str = "") -> HTMLResponse:
        results = await database.search(q)
        items = "".join(f"<li>{escape(result['title'])}</li>" for result in results)
        return _page("Search", f"<h1>Search</h1><ul>{items}</ul>")

    @app.get("/members/{member_slug}", response_class=HTMLResponse)
    async def member(member_slug: str) -> HTMLResponse:
        profile = await database.member_view(member_slug)
        return _page("Member", f"<h1>{escape(profile['name'])}</h1>")

    @app.get("/members/{member_slug}/inbox", response_class=HTMLResponse)
    async def inbox(member_slug: str) -> HTMLResponse:
        messages = await database.member_inbox(member_slug)
        if not messages:
            body = "<h1>Private inbox</h1><p>No private updates yet.</p>"
        else:
            body = "<h1>Private inbox</h1><ul>" + "".join(
                f"<li>{escape(message)}</li>" for message in messages
            ) + "</ul>"
        return _page("Inbox", body)

    @app.get("/moderation/queue", response_class=HTMLResponse)
    async def moderation_queue() -> HTMLResponse:
        entries = await database.moderation_queue()
        body = "<h1>Moderation queue</h1>" + "".join(
            (
                "<article>"
                f"<h2>{escape(entry['title'])}</h2>"
                f"<p>{escape(entry['note'])}</p>"
                "</article>"
            )
            for entry in entries
        )
        return _page("Moderation queue", body)

    @app.get("/threads/{slug}", response_class=HTMLResponse)
    async def thread_page(slug: str) -> HTMLResponse:
        thread = await database.thread_view(slug)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return _page(str(thread["title"]), _thread_page_html(thread))

    @app.post("/threads/{slug}/reply", response_class=HTMLResponse)
    async def reply(
        slug: str,
        author_name: str = Form(...),
        body: str = Form(...),
    ) -> HTMLResponse:
        await database.add_reply(slug, author_name=author_name, body=body)
        thread = await database.thread_view(slug)
        assert thread is not None
        return _page(str(thread["title"]), "<p>Reply posted.</p>" + _thread_page_html(thread))

    @app.post("/threads/{slug}/react/{post_id}", response_class=HTMLResponse)
    async def react(slug: str, post_id: int, kind: str = Form(...)) -> HTMLResponse:
        await database.add_reaction(slug, post_id, kind)
        thread = await database.thread_view(slug)
        assert thread is not None
        return _page(str(thread["title"]), _thread_page_html(thread))

    @app.post("/threads/{slug}/answer/{post_id}", response_class=HTMLResponse)
    async def answer(slug: str, post_id: int) -> HTMLResponse:
        await database.accept_answer(slug, post_id)
        thread = await database.thread_view(slug)
        assert thread is not None
        return _page(str(thread["title"]), _thread_page_html(thread))

    @app.post("/threads/{slug}/moderate/{state}", response_class=HTMLResponse)
    async def moderate(slug: str, state: str) -> HTMLResponse:
        await database.moderate_thread(slug, state)
        thread = await database.thread_view(slug)
        assert thread is not None
        return _page(str(thread["title"]), _thread_page_html(thread))

    return app
