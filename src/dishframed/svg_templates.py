from __future__ import annotations

import hashlib
from html import escape

from .models import MenuDocument, MenuItem, MenuSection

PAGE_WIDTH = 1400
MARGIN_X = 84
TOP_PADDING = 92
BOTTOM_PADDING = 84
SECTION_GAP = 42
ITEM_GAP = 20
CARD_GAP = 24
COLUMN_COUNT = 2
CARD_WIDTH = (PAGE_WIDTH - (MARGIN_X * 2) - CARD_GAP) // COLUMN_COUNT
CHARS_PER_LINE = 34
DESCRIPTION_CHARS_PER_LINE = 42
LINE_HEIGHT = 28
DESCRIPTION_LINE_HEIGHT = 20


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines


def _item_card_height(item: MenuItem) -> int:
    description_lines = _wrap_text(item.description or "", DESCRIPTION_CHARS_PER_LINE)
    return 170 + (len(description_lines) * DESCRIPTION_LINE_HEIGHT)


def _section_height(section: MenuSection) -> int:
    if not section.items:
        return 64

    column_heights = [0] * COLUMN_COUNT
    for index, item in enumerate(section.items):
        column = index % COLUMN_COUNT
        column_heights[column] += _item_card_height(item)
        if index >= COLUMN_COUNT:
            column_heights[column] += ITEM_GAP
    return 78 + max(column_heights)


def _palette_for_item(item: MenuItem) -> tuple[str, str, str, str]:
    digest = hashlib.sha256((item.image_prompt or item.name).encode("utf-8")).hexdigest()
    palettes = [
        ("#d97a43", "#f3c37b", "#fff2dc", "#8b4422"),
        ("#6d8f72", "#d9e2a8", "#f3f5df", "#38553d"),
        ("#b85e4b", "#f1c28c", "#fff0e2", "#6f2f24"),
        ("#5c7fa3", "#d4dfef", "#f4f8fc", "#27415e"),
        ("#8b6cb0", "#e2d6f3", "#f7f1fc", "#4c3369"),
        ("#b86f2b", "#efd2a7", "#fff6ea", "#734215"),
    ]
    return palettes[int(digest[:2], 16) % len(palettes)]


def _illustration_kind(item: MenuItem) -> str:
    text = f"{item.name} {item.image_prompt or ''}".lower()
    if any(token in text for token in ("coffee", "latte", "cappuccino", "mocha", "espresso", "macchiato")):
        return "cup"
    if any(token in text for token in ("tea", "chai", "matcha", "earl grey", "peppermint")):
        return "mug"
    if any(token in text for token in ("juice", "smoothie", "milkshake", "frappe", "iced", "acai")):
        return "glass"
    if any(token in text for token in ("croissant", "banana bread", "scone", "cake", "toast", "pancake", "waffle")):
        return "pastry"
    return "plate"


def _render_card_illustration(item: MenuItem, x: int, y: int, width: int) -> str:
    accent, soft, panel, deep = _palette_for_item(item)
    art_x = x + 18
    art_y = y + 18
    art_w = width - 36
    kind = _illustration_kind(item)

    parts = [
        f'<rect x="{art_x}" y="{art_y}" width="{art_w}" height="120" rx="22" fill="{panel}" stroke="{soft}" stroke-width="1.5"/>',
        f'<circle cx="{art_x + 86}" cy="{art_y + 36}" r="38" fill="{soft}" fill-opacity="0.85"/>',
        f'<circle cx="{art_x + art_w - 72}" cy="{art_y + 90}" r="46" fill="{soft}" fill-opacity="0.55"/>',
        f'<circle cx="{art_x + art_w - 118}" cy="{art_y + 28}" r="20" fill="{accent}" fill-opacity="0.16"/>',
        f'<rect x="{art_x + 28}" y="{art_y + 86}" width="{art_w - 56}" height="28" rx="14" fill="#fffaf2" stroke="{soft}" stroke-width="1"/>',
    ]

    center_x = art_x + art_w // 2
    base_y = art_y + 68

    if kind == "cup":
        parts.extend(
            [
                f'<rect x="{center_x - 38}" y="{base_y - 18}" width="76" height="34" rx="10" fill="{accent}"/>',
                f'<rect x="{center_x - 28}" y="{base_y - 26}" width="56" height="12" rx="6" fill="#fff8ef"/>',
                f'<path d="M {center_x + 38} {base_y - 10} Q {center_x + 62} {base_y - 6} {center_x + 46} {base_y + 10}" fill="none" stroke="{deep}" stroke-width="5" stroke-linecap="round"/>',
                f'<rect x="{center_x - 54}" y="{base_y + 18}" width="108" height="8" rx="4" fill="{deep}" fill-opacity="0.16"/>',
                f'<path d="M {center_x - 16} {base_y - 34} C {center_x - 28} {base_y - 52} {center_x - 10} {base_y - 54} {center_x - 6} {base_y - 38}" fill="none" stroke="{deep}" stroke-width="3" stroke-linecap="round" opacity="0.65"/>',
                f'<path d="M {center_x + 10} {base_y - 36} C {center_x} {base_y - 54} {center_x + 18} {base_y - 56} {center_x + 22} {base_y - 40}" fill="none" stroke="{deep}" stroke-width="3" stroke-linecap="round" opacity="0.65"/>',
            ]
        )
    elif kind == "mug":
        parts.extend(
            [
                f'<rect x="{center_x - 42}" y="{base_y - 20}" width="84" height="40" rx="12" fill="{accent}"/>',
                f'<path d="M {center_x + 42} {base_y - 8} Q {center_x + 64} {base_y} {center_x + 44} {base_y + 16}" fill="none" stroke="{deep}" stroke-width="5" stroke-linecap="round"/>',
                f'<rect x="{center_x - 56}" y="{base_y + 22}" width="112" height="8" rx="4" fill="{deep}" fill-opacity="0.16"/>',
            ]
        )
    elif kind == "glass":
        parts.extend(
            [
                f'<path d="M {center_x - 28} {base_y - 34} L {center_x + 28} {base_y - 34} L {center_x + 18} {base_y + 26} L {center_x - 18} {base_y + 26} Z" fill="{accent}" fill-opacity="0.92"/>',
                f'<rect x="{center_x - 4}" y="{base_y - 48}" width="8" height="18" rx="4" fill="{deep}" fill-opacity="0.55"/>',
                f'<circle cx="{center_x + 18}" cy="{base_y - 20}" r="8" fill="#fff7ed" fill-opacity="0.7"/>',
                f'<circle cx="{center_x - 2}" cy="{base_y - 8}" r="7" fill="#fff7ed" fill-opacity="0.55"/>',
                f'<rect x="{center_x - 44}" y="{base_y + 30}" width="88" height="8" rx="4" fill="{deep}" fill-opacity="0.16"/>',
            ]
        )
    elif kind == "pastry":
        parts.extend(
            [
                f'<ellipse cx="{center_x}" cy="{base_y + 18}" rx="56" ry="12" fill="{deep}" fill-opacity="0.12"/>',
                f'<path d="M {center_x - 44} {base_y + 4} Q {center_x - 10} {base_y - 42} {center_x + 30} {base_y - 8} Q {center_x + 42} {base_y + 4} {center_x + 20} {base_y + 18} Q {center_x - 10} {base_y + 30} {center_x - 44} {base_y + 4}" fill="{accent}" />',
                f'<path d="M {center_x - 24} {base_y - 6} Q {center_x - 6} {base_y - 26} {center_x + 12} {base_y - 10}" fill="none" stroke="#fff8ef" stroke-width="5" stroke-linecap="round" opacity="0.9"/>',
            ]
        )
    else:
        parts.extend(
            [
                f'<ellipse cx="{center_x}" cy="{base_y + 10}" rx="72" ry="18" fill="{deep}" fill-opacity="0.10"/>',
                f'<circle cx="{center_x}" cy="{base_y}" r="40" fill="#fffaf2" stroke="{accent}" stroke-width="8"/>',
                f'<circle cx="{center_x}" cy="{base_y}" r="24" fill="{soft}"/>',
                f'<circle cx="{center_x - 18}" cy="{base_y - 6}" r="8" fill="{accent}" fill-opacity="0.85"/>',
                f'<circle cx="{center_x + 6}" cy="{base_y + 8}" r="7" fill="{deep}" fill-opacity="0.35"/>',
                f'<circle cx="{center_x + 18}" cy="{base_y - 10}" r="6" fill="{accent}" fill-opacity="0.55"/>',
            ]
        )

    return "".join(parts)


def _render_item_card(item: MenuItem, x: int, y: int, width: int, height: int) -> str:
    name_lines = _wrap_text(item.name, CHARS_PER_LINE)
    description_lines = _wrap_text(item.description or "", DESCRIPTION_CHARS_PER_LINE)
    image_prompt = item.image_prompt or item.name
    badge_text = escape(image_prompt[:38] + ("..." if len(image_prompt) > 38 else ""))
    price_text = escape(item.price) if item.price else ""
    _, soft, _, _ = _palette_for_item(item)

    lines = [
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="26" fill="#fffaf2" stroke="#d7c3ac" stroke-width="2"/>',
        _render_card_illustration(item, x, y, width),
        f'<text x="{x + 52}" y="{y + 121}" font-size="15" fill="#54321c" font-family="Arial, sans-serif">{badge_text}</text>',
        f'<line x1="{x + 22}" y1="{y + 154}" x2="{x + width - 22}" y2="{y + 154}" stroke="{soft}" stroke-width="2"/>',
    ]

    text_y = y + 172
    for line in name_lines:
        lines.append(
            f'<text x="{x + 28}" y="{text_y}" font-size="28" font-weight="700" fill="#22150e" font-family="Georgia, serif">{escape(line)}</text>'
        )
        text_y += LINE_HEIGHT

    if price_text:
        lines.append(
            f'<text x="{x + width - 28}" y="{y + 176}" text-anchor="end" font-size="26" font-weight="700" fill="#b85e27" font-family="Georgia, serif">{price_text}</text>'
        )

    description_y = text_y + 8
    for line in description_lines:
        lines.append(
            f'<text x="{x + 28}" y="{description_y}" font-size="18" fill="#6d584b" font-family="Georgia, serif">{escape(line)}</text>'
        )
        description_y += DESCRIPTION_LINE_HEIGHT

    return "".join(lines)


def render_menu_svg(menu: MenuDocument) -> str:
    section_heights = [_section_height(section) for section in menu.sections]
    notes_height = 0
    if menu.source_notes:
        notes_height = 56 + (len(menu.source_notes) * 28)

    page_height = (
        TOP_PADDING
        + 140
        + sum(section_heights)
        + (SECTION_GAP * max(len(menu.sections) - 1, 0))
        + notes_height
        + BOTTOM_PADDING
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_WIDTH}" height="{page_height}" viewBox="0 0 {PAGE_WIDTH} {page_height}" role="img" aria-labelledby="title desc">',
        "<title id=\"title\">DishFramed Preview</title>",
        f'<desc id="desc">{escape(menu.title)}</desc>',
        "<defs>",
        '<linearGradient id="pageGradient" x1="0%" x2="100%" y1="0%" y2="100%">'
        '<stop offset="0%" stop-color="#f7ead6"/>'
        '<stop offset="55%" stop-color="#fbf6ef"/>'
        '<stop offset="100%" stop-color="#ebd3b6"/>'
        "</linearGradient>",
        "</defs>",
        f'<rect width="{PAGE_WIDTH}" height="{page_height}" fill="url(#pageGradient)"/>',
        f'<rect x="30" y="30" width="{PAGE_WIDTH - 60}" height="{page_height - 60}" rx="34" fill="#fffaf4" fill-opacity="0.82" stroke="#dbc9b7" stroke-width="2"/>',
        f'<text x="{MARGIN_X}" y="{TOP_PADDING}" font-size="18" letter-spacing="5" fill="#7b6758" font-family="Arial, sans-serif">DISHFRAMED PREVIEW</text>',
        f'<text x="{MARGIN_X}" y="{TOP_PADDING + 64}" font-size="62" font-weight="700" fill="#24160d" font-family="Georgia, serif">{escape(menu.title)}</text>',
    ]

    header_y = TOP_PADDING + 104
    if menu.restaurant_name:
        parts.append(
            f'<text x="{MARGIN_X}" y="{header_y}" font-size="28" fill="#6d584b" font-family="Georgia, serif">{escape(menu.restaurant_name)}</text>'
        )
        header_y += 36
    if menu.subtitle:
        parts.append(
            f'<text x="{MARGIN_X}" y="{header_y}" font-size="22" fill="#6d584b" font-family="Arial, sans-serif">{escape(menu.subtitle)}</text>'
        )

    y = TOP_PADDING + 172
    for section in menu.sections:
        parts.append(
            f'<text x="{MARGIN_X}" y="{y}" font-size="38" font-weight="700" fill="#2f1d12" font-family="Georgia, serif">{escape(section.name)}</text>'
        )
        y += 28
        column_heights = [0] * COLUMN_COUNT
        for index, item in enumerate(section.items):
            column = index % COLUMN_COUNT
            card_x = MARGIN_X + (column * (CARD_WIDTH + CARD_GAP))
            card_y = y + 22 + column_heights[column]
            card_height = _item_card_height(item)
            parts.append(_render_item_card(item, card_x, card_y, CARD_WIDTH, card_height))
            column_heights[column] += card_height + ITEM_GAP
        y += _section_height(section) + SECTION_GAP

    if menu.source_notes:
        parts.append(
            f'<text x="{MARGIN_X}" y="{y}" font-size="28" font-weight="700" fill="#2f1d12" font-family="Georgia, serif">Source Notes</text>'
        )
        y += 34
        for note in menu.source_notes:
            parts.append(
                f'<text x="{MARGIN_X}" y="{y}" font-size="20" fill="#6d584b" font-family="Georgia, serif">• {escape(note)}</text>'
            )
            y += 28

    parts.append("</svg>")
    return "".join(parts)
