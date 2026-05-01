from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Protocol

from .html_templates import render_menu_html
from .models import MenuDocument, RenderArtifact
from .photo_grid import render_photo_menu_poster
from .svg_templates import render_menu_svg


class MenuRenderer(Protocol):
    def render(self, menu: MenuDocument, output_dir: Path) -> RenderArtifact:
        """Render a menu document into an output artifact."""


class JsonPreviewRenderer:
    def render(self, menu: MenuDocument, output_dir: Path) -> RenderArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "menu_preview.json"
        output_path.write_text(
            json.dumps(menu.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        item_count = sum(len(section.items) for section in menu.sections)
        preview_text = f"Rendered preview for {item_count} menu item(s)."
        return RenderArtifact(output_path=output_path, preview_text=preview_text)


class HtmlPreviewRenderer:
    def render(self, menu: MenuDocument, output_dir: Path) -> RenderArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        html_output_path = output_dir / "menu_preview.html"
        svg_output_path = output_dir / "menu_preview.svg"
        png_output_path = output_dir / "menu_preview.png"
        html_output_path.write_text(render_menu_html(menu), encoding="utf-8")
        svg_output_path.write_text(render_menu_svg(menu), encoding="utf-8")
        if any(item.image_path for section in menu.sections for item in section.items):
            render_photo_menu_poster(menu, png_output_path)
            preview_text = "Rendered photo-card PNG menu with realistic featured dish images."
        else:
            subprocess.run(
                [
                    "convert",
                    "-background",
                    "white",
                    str(svg_output_path),
                    str(png_output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            item_count = sum(len(section.items) for section in menu.sections)
            preview_text = (
                f"Rendered PNG poster with SVG and HTML companions for {item_count} menu item(s)."
            )
        return RenderArtifact(output_path=png_output_path, preview_text=preview_text)
