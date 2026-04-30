from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from .pipeline import DishFramedPipeline

app = typer.Typer(help="DishFramed development CLI.")


@app.command()
def frame(
    image: List[Path] = typer.Option(..., "--image", "-i", help="Input menu image path."),
    output_dir: Path = typer.Option(
        Path("./artifacts"),
        "--output-dir",
        help="Directory for rendered output.",
    ),
) -> None:
    pipeline = DishFramedPipeline()
    artifact = pipeline.run(image, output_dir)
    typer.echo(f"Output: {artifact.output_path}")
    typer.echo(artifact.preview_text)


@app.command()
def plan() -> None:
    typer.echo("DishFramed MVP:")
    typer.echo("1. Extract menu structure from menu photos.")
    typer.echo("2. Enrich dishes with image prompts.")
    typer.echo("3. Render a framed visual menu.")
    typer.echo("4. Return it through Telegram.")


def main(argv: Optional[list[str]] = None) -> None:
    if argv is None:
        app()
        return
    app(args=argv, standalone_mode=False)

