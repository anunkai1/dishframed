from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .html_templates import render_menu_html
from .models import MenuDocument, RenderArtifact


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
        output_path = output_dir / "menu_preview.html"
        output_path.write_text(render_menu_html(menu), encoding="utf-8")
        item_count = sum(len(section.items) for section in menu.sections)
        preview_text = f"Rendered HTML preview for {item_count} menu item(s)."
        return RenderArtifact(output_path=output_path, preview_text=preview_text)
