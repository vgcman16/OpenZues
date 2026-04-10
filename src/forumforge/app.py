from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from forumforge.database import ForumDatabase
from forumforge.settings import Settings, settings

SORT_LABELS = {
    "latest": "Latest",
    "signal": "Signal",
    "knowledge": "Knowledge",
    "unanswered": "Unanswered",
}

REACTION_CHOICES = [
    ("upvote", "Upvote"),
    ("insight", "Insight"),
    ("thanks", "Thanks"),
]


def render_body_html(value: str) -> Markup:
    paragraphs = [part.strip() for part in value.split("\n\n") if part.strip()]
    if not paragraphs:
        return Markup("")
    rendered = "".join(
        f"<p>{escape(paragraph).replace('\n', Markup('<br>'))}</p>" for paragraph in paragraphs
    )
    return Markup(rendered)


def create_templates(app_settings: Settings) -> Jinja2Templates:
    templates = Jinja2Templates(directory=str(app_settings.templates_dir))
    templates.env.filters["body_html"] = render_body_html
    return templates


def build_notice(request: Request) -> dict[str, str] | None:
    kind = request.query_params.get("notice_kind")
    message = request.query_params.get("notice")
    if not kind or not message:
        return None
    return {"kind": kind, "message": message}


def normalize_tags(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.replace("#", "").split(",") if item.strip()]


def redirect_to(url: str, *, notice: str, notice_kind: str = "success") -> RedirectResponse:
    separator = "&" if "?" in url else "?"
    query = urlencode({"notice": notice, "notice_kind": notice_kind})
    return RedirectResponse(url=f"{url}{separator}{query}", status_code=303)


def create_app(app_settings: Settings = settings) -> FastAPI:
    database = ForumDatabase(app_settings.effective_db_path)
    templates = create_templates(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await database.initialize()
        app.state.database = database
        app.state.templates = templates
        yield

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(app_settings.static_dir)), name="static")

    def base_context(request: Request) -> dict[str, object]:
        return {
            "request": request,
            "notice": build_notice(request),
            "sort_labels": SORT_LABELS,
        }

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request) -> HTMLResponse:
        payload = await database.home_view()
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                **base_context(request),
                "page_title": "ForumForge",
                "home": payload,
                "reaction_choices": REACTION_CHOICES,
            },
        )

    @app.get("/forums/{forum_slug}", response_class=HTMLResponse)
    async def forum_page(
        request: Request,
        forum_slug: str,
        q: str = "",
        sort: str = "latest",
    ) -> HTMLResponse:
        payload = await database.forum_view(forum_slug, q=q or None, sort=sort)
        if payload is None:
            raise HTTPException(status_code=404, detail="Forum not found")
        return templates.TemplateResponse(
            request,
            "forum.html",
            {
                **base_context(request),
                "page_title": payload["name"],
                "forum": payload,
                "sort": sort,
            },
        )

    @app.get("/threads/{thread_slug}", response_class=HTMLResponse)
    async def thread_page(request: Request, thread_slug: str) -> HTMLResponse:
        payload = await database.thread_view(thread_slug)
        if payload is None:
            raise HTTPException(status_code=404, detail="Thread not found")
        return templates.TemplateResponse(
            request,
            "thread.html",
            {
                **base_context(request),
                "page_title": payload["thread"]["title"],
                "payload": payload,
                "reaction_choices": REACTION_CHOICES,
            },
        )

    @app.get("/members/{username}", response_class=HTMLResponse)
    async def profile_page(request: Request, username: str) -> HTMLResponse:
        profile = await database.profile_view(username)
        if profile is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                **base_context(request),
                "page_title": profile["display_name"],
                "profile": profile,
            },
        )

    @app.get("/members/{username}/inbox", response_class=HTMLResponse)
    async def member_inbox_page(request: Request, username: str) -> HTMLResponse:
        inbox = await database.inbox_view(username)
        if inbox is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return templates.TemplateResponse(
            request,
            "inbox.html",
            {
                **base_context(request),
                "page_title": f"{inbox['display_name']} inbox",
                "inbox": inbox,
            },
        )

    @app.get("/moderation/queue", response_class=HTMLResponse)
    async def moderation_queue_page(request: Request) -> HTMLResponse:
        payload = await database.moderation_queue_view()
        return templates.TemplateResponse(
            request,
            "moderation_queue.html",
            {
                **base_context(request),
                "page_title": "Moderation queue",
                "payload": payload,
            },
        )

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request, q: str = "") -> HTMLResponse:
        results = await database.search(q) if q else []
        return templates.TemplateResponse(
            request,
            "search.html",
            {
                **base_context(request),
                "page_title": "Search",
                "query": q,
                "results": results,
            },
        )

    @app.post("/forums/{forum_slug}/threads")
    async def create_thread(
        request: Request,
        forum_slug: str,
        author_name: str = Form(...),
        title: str = Form(...),
        body: str = Form(...),
        tags: str = Form(""),
    ) -> RedirectResponse:
        if len(title.strip()) < 8 or len(body.strip()) < 24:
            return redirect_to(
                str(request.url_for("forum_page", forum_slug=forum_slug)),
                notice="Give the thread a clearer title and a fuller opening post.",
                notice_kind="error",
            )
        slug = await database.create_thread(
            forum_slug=forum_slug,
            author_name=author_name,
            title=title,
            body=body,
            tags=normalize_tags(tags),
        )
        return redirect_to(
            str(request.url_for("thread_page", thread_slug=slug)),
            notice="Thread published.",
        )

    @app.post("/threads/{thread_slug}/reply")
    async def create_reply(
        request: Request,
        thread_slug: str,
        author_name: str = Form(...),
        body: str = Form(...),
    ) -> RedirectResponse:
        if len(body.strip()) < 12:
            return redirect_to(
                str(request.url_for("thread_page", thread_slug=thread_slug)),
                notice="Replies should add a little more signal before posting.",
                notice_kind="error",
            )
        try:
            await database.create_reply(thread_slug=thread_slug, author_name=author_name, body=body)
        except ValueError as exc:
            return redirect_to(
                str(request.url_for("thread_page", thread_slug=thread_slug)),
                notice=str(exc),
                notice_kind="error",
            )
        return redirect_to(
            str(request.url_for("thread_page", thread_slug=thread_slug)),
            notice="Reply posted.",
        )

    @app.post("/threads/{thread_slug}/react/{post_id}")
    async def react_to_post(
        request: Request,
        thread_slug: str,
        post_id: int,
        kind: str = Form(...),
    ) -> RedirectResponse:
        try:
            slug = await database.react_to_post(post_id=post_id, kind=kind)
        except ValueError as exc:
            return redirect_to(
                str(request.url_for("thread_page", thread_slug=thread_slug)),
                notice=str(exc),
                notice_kind="error",
            )
        return redirect_to(
            str(request.url_for("thread_page", thread_slug=slug)),
            notice=f"{kind.title()} added.",
        )

    @app.post("/threads/{thread_slug}/answer/{post_id}")
    async def mark_answer(request: Request, thread_slug: str, post_id: int) -> RedirectResponse:
        try:
            await database.mark_answer(thread_slug=thread_slug, post_id=post_id)
        except ValueError as exc:
            return redirect_to(
                str(request.url_for("thread_page", thread_slug=thread_slug)),
                notice=str(exc),
                notice_kind="error",
            )
        return redirect_to(
            str(request.url_for("thread_page", thread_slug=thread_slug)),
            notice="Answer marked. This thread now reads as resolved knowledge.",
        )

    @app.post("/threads/{thread_slug}/moderate/{field}")
    async def moderate_thread(request: Request, thread_slug: str, field: str) -> RedirectResponse:
        try:
            await database.toggle_thread_flag(thread_slug=thread_slug, field=field)
        except ValueError as exc:
            return redirect_to(
                str(request.url_for("thread_page", thread_slug=thread_slug)),
                notice=str(exc),
                notice_kind="error",
            )
        return redirect_to(
            str(request.url_for("thread_page", thread_slug=thread_slug)),
            notice=f"{field.title()} state updated.",
        )

    return app
