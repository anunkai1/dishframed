from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Sequence

from .menu_parser import MenuExtractor, StubMenuExtractor
from .models import MenuDocument, RenderArtifact
from .render import HtmlPreviewRenderer, MenuRenderer


def normalize_input_paths(paths: Iterable[str | Path]) -> List[Path]:
    normalized: List[Path] = []
    for candidate in paths:
        path = Path(candidate).expanduser().resolve()
        if path not in normalized:
            normalized.append(path)
    return normalized


class DishFramedPipeline:
    def __init__(
        self,
        extractor: MenuExtractor | None = None,
        renderer: MenuRenderer | None = None,
    ) -> None:
        self.extractor = extractor or StubMenuExtractor()
        self.renderer = renderer or HtmlPreviewRenderer()

    def build_menu(self, image_paths: Sequence[str | Path]) -> MenuDocument:
        normalized_paths = normalize_input_paths(image_paths)
        if not normalized_paths:
            raise ValueError("At least one input image path is required.")
        return self.extractor.extract(normalized_paths)

    def run(self, image_paths: Sequence[str | Path], output_dir: str | Path) -> RenderArtifact:
        menu = self.build_menu(image_paths)
        return self.renderer.render(menu, Path(output_dir).expanduser().resolve())

    def render_menu(self, menu: MenuDocument, output_dir: str | Path) -> RenderArtifact:
        return self.renderer.render(menu, Path(output_dir).expanduser().resolve())
