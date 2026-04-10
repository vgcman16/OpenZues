from __future__ import annotations

import typer
import uvicorn

from openzues.settings import settings

app = typer.Typer(help="OpenZues local control plane")


@app.command()
def serve(
    host: str = typer.Option(settings.host, help="Host to bind."),
    port: int = typer.Option(settings.port, help="Port to bind."),
    reload: bool = typer.Option(False, help="Enable hot reload."),
) -> None:
    uvicorn.run(
        "openzues.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
