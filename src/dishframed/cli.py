from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from pydantic import ValidationError

from .models import MenuDocument
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
def render_menu(
    menu_json: Path = typer.Argument(..., help="Structured menu JSON file."),
    output_dir: Path = typer.Option(
        Path("./artifacts"),
        "--output-dir",
        help="Directory for rendered output.",
    ),
) -> None:
    try:
        menu = MenuDocument.model_validate_json(menu_json.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"Menu JSON not found: {menu_json}") from exc
    except ValidationError as exc:
        raise typer.BadParameter(f"Invalid menu JSON: {exc}") from exc

    pipeline = DishFramedPipeline()
    artifact = pipeline.render_menu(menu, output_dir)
    typer.echo(f"Output: {artifact.output_path}")
    typer.echo(artifact.preview_text)


@app.command()
def parse_text(
    text_file: Path = typer.Argument(..., help="OCR-style menu text file."),
    title: str = typer.Option("Parsed Menu", "--title", help="Menu title."),
    json_out: Path = typer.Option(
        Path("./artifacts/parsed_menu.json"),
        "--json-out",
        help="Where to write normalized menu JSON.",
    ),
    output_dir: Path = typer.Option(
        Path("./artifacts"),
        "--output-dir",
        help="Directory for rendered output.",
    ),
) -> None:
    try:
        raw_text = text_file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise typer.BadParameter(f"Text file not found: {text_file}") from exc

    pipeline = DishFramedPipeline()
    menu = pipeline.parse_menu_text(raw_text, title=title)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(menu.model_dump_json(indent=2), encoding="utf-8")
    artifact = pipeline.render_menu(menu, output_dir)

    typer.echo(f"Menu JSON: {json_out}")
    typer.echo(f"Preview: {artifact.output_path}")
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
