from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable, List, Sequence

from .codex_extractor import CodexImageMenuExtractor
from .image_generation import DEFAULT_FEATURED_ITEM_LIMIT, default_image_generator, enrich_menu_with_generated_images
from .menu_parser import MenuExtractor, StubMenuExtractor, parse_menu_text
from .models import MenuDocument, RenderArtifact
from .openai_extractor import OpenAIImageMenuExtractor
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
        image_generator=None,
        featured_item_limit: int | None = DEFAULT_FEATURED_ITEM_LIMIT,
    ) -> None:
        self.extractor = extractor or default_extractor()
        self.renderer = renderer or HtmlPreviewRenderer()
        self.image_generator = image_generator or default_image_generator()
        self.featured_item_limit = featured_item_limit

    def build_menu(self, image_paths: Sequence[str | Path]) -> MenuDocument:
        normalized_paths = normalize_input_paths(image_paths)
        if not normalized_paths:
            raise ValueError("At least one input image path is required.")
        return self.extractor.extract(normalized_paths)

    def run(self, image_paths: Sequence[str | Path], output_dir: str | Path) -> RenderArtifact:
        menu = self.build_menu(image_paths)
        resolved_output_dir = Path(output_dir).expanduser().resolve()
        enriched = enrich_menu_with_generated_images(
            menu,
            output_dir=resolved_output_dir,
            generator=self.image_generator,
            featured_item_limit=self.featured_item_limit,
        )
        return self.renderer.render(enriched, resolved_output_dir)

    def render_menu(self, menu: MenuDocument, output_dir: str | Path) -> RenderArtifact:
        resolved_output_dir = Path(output_dir).expanduser().resolve()
        enriched = enrich_menu_with_generated_images(
            menu,
            output_dir=resolved_output_dir,
            generator=self.image_generator,
            featured_item_limit=self.featured_item_limit,
        )
        return self.renderer.render(enriched, resolved_output_dir)

    def parse_menu_text(self, text: str, *, title: str = "Parsed Menu") -> MenuDocument:
        return parse_menu_text(text, title=title)


def default_extractor() -> MenuExtractor:
    extractor_name = os.getenv("DISHFRAMED_EXTRACTOR", "auto").strip().lower()
    if extractor_name == "stub":
        return StubMenuExtractor()
    if extractor_name == "codex":
        return CodexImageMenuExtractor()
    if extractor_name == "openai":
        return OpenAIImageMenuExtractor()
    codex_bin = os.getenv("DISHFRAMED_CODEX_BIN", "codex")
    if shutil.which(codex_bin):
        return CodexImageMenuExtractor(codex_bin=codex_bin)
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIImageMenuExtractor()
    return StubMenuExtractor()
