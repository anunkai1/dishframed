from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from .models import MenuDocument


class MenuExtractor(Protocol):
    def extract(self, image_paths: Sequence[Path]) -> MenuDocument:
        """Extract a normalized menu document from input images."""


class StubMenuExtractor:
    def extract(self, image_paths: Sequence[Path]) -> MenuDocument:
        notes = [f"Stub extractor received {len(image_paths)} image(s)."]
        return MenuDocument(
            title="Extracted Menu",
            sections=[],
            source_notes=notes,
        )

