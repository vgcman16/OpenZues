from __future__ import annotations

import typer

app = typer.Typer(help="ForumForge local discussion sandbox.")


@app.command()
def serve() -> None:
    typer.echo("Use `uvicorn forumforge.app:create_app` to run ForumForge.")
