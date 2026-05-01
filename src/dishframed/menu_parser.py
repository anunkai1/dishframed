from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol, Sequence

from .models import MenuDocument, MenuItem, MenuSection

PRICE_LINE_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<price>(?:\$?\d+(?:\.\d{2})?)|MP)$",
    re.IGNORECASE,
)


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def looks_like_section_header(line: str) -> bool:
    if not line:
        return False
    if len(line) > 48:
        return False
    letters = [char for char in line if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    return uppercase_ratio >= 0.8


def looks_like_item_line(line: str) -> bool:
    return PRICE_LINE_RE.match(line) is not None


def parse_menu_text(text: str, *, title: str = "Parsed Menu") -> MenuDocument:
    lines = [_clean_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    sections: list[MenuSection] = []
    current_section = MenuSection(name="Menu", items=[])
    current_item: MenuItem | None = None

    for line in lines:
        if looks_like_section_header(line):
            if current_section.items or current_section.name != "Menu":
                sections.append(current_section)
            current_section = MenuSection(name=line.title(), items=[])
            current_item = None
            continue

        item_match = PRICE_LINE_RE.match(line)
        if item_match:
            current_item = MenuItem(
                name=item_match.group("name").strip(),
                price=item_match.group("price").strip(),
            )
            current_section.items.append(current_item)
            continue

        if current_item is None:
            continue

        if current_item.description:
            current_item.description = f"{current_item.description} {line}".strip()
        else:
            current_item.description = line

    if current_section.items or current_section.name != "Menu":
        sections.append(current_section)

    notes: list[str] = []
    if not sections:
        notes.append("Parser did not detect any priced menu items.")
    return MenuDocument(title=title, sections=sections, source_notes=notes)


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


def coerce_menu_document(menu: MenuDocument) -> MenuDocument:
    normalized_sections: list[MenuSection] = []
    for section in menu.sections:
        items = [
            MenuItem(
                name=item.name.strip(),
                price=item.price.strip() if item.price else None,
                description=item.description.strip() if item.description else None,
                image_prompt=item.image_prompt.strip() if item.image_prompt else None,
            )
            for item in section.items
            if item.name.strip()
        ]
        if items:
            normalized_sections.append(MenuSection(name=section.name.strip() or "Menu", items=items))

    notes = [note.strip() for note in menu.source_notes if note.strip()]
    return MenuDocument(
        title=menu.title.strip() or "Extracted Menu",
        restaurant_name=menu.restaurant_name.strip() if menu.restaurant_name else None,
        subtitle=menu.subtitle.strip() if menu.subtitle else None,
        sections=normalized_sections,
        source_notes=notes,
    )
