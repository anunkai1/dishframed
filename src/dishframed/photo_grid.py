from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from .models import MenuDocument, MenuItem, MenuSection

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 2200
BACKGROUND_COLOR = "#f7f1e8"
CARD_BACKGROUND = "#fffaf4"
ACCENT = "#8f4f2a"
TEXT = "#2f241d"
MUTED = "#6d5b4a"
CARD_RADIUS = 28


def render_photo_menu_poster(menu: MenuDocument, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), ImageColor.getrgb(BACKGROUND_COLOR))
    draw = ImageDraw.Draw(image)

    title_font = _load_font(92, bold=True, serif=True)
    subtitle_font = _load_font(34, serif=True)
    section_font = _load_font(30, bold=True, serif=True)
    item_font = _load_font(24, bold=True)
    meta_font = _load_font(22)
    small_font = _load_font(18)

    featured_items = [item for item in _iter_items(menu) if item.image_path and Path(item.image_path).exists()]

    y = 70
    header_title = menu.title or "Menu"
    if menu.restaurant_name:
        draw.text((80, y), menu.restaurant_name.upper(), fill=ACCENT, font=subtitle_font)
        y += 56
    draw.text((80, y), header_title, fill=TEXT, font=title_font)
    y += 110
    if menu.subtitle:
        draw.text((80, y), menu.subtitle, fill=MUTED, font=subtitle_font)
        y += 62

    if featured_items:
        y = _draw_featured_grid(
            image,
            draw,
            featured_items,
            y=y + 12,
            title_font=section_font,
            item_font=item_font,
            meta_font=meta_font,
        )

    _draw_menu_columns(
        draw,
        menu.sections,
        top=max(y + 40, 1230),
        bottom=CANVAS_HEIGHT - 120,
        section_font=section_font,
        item_font=meta_font,
        small_font=small_font,
    )

    if menu.source_notes:
        note = " • ".join(menu.source_notes[:3])
        draw.text((80, CANVAS_HEIGHT - 70), note[:180], fill=MUTED, font=small_font)

    image.save(output_path, format="PNG")
    return output_path


def _draw_featured_grid(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    items: Sequence[MenuItem],
    *,
    y: int,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    item_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    meta_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    draw.text((80, y), "Featured Dishes", fill=ACCENT, font=title_font)
    y += 54

    cols = 4 if len(items) > 8 else 3
    gap = 24
    card_width = (CANVAS_WIDTH - 160 - (gap * (cols - 1))) // cols
    card_height = 360 if cols == 4 else 430
    rows = math.ceil(len(items) / cols)
    for index, item in enumerate(items):
        col = index % cols
        row = index // cols
        x = 80 + col * (card_width + gap)
        card_y = y + row * (card_height + gap)
        _draw_card(canvas, draw, item, x, card_y, card_width, card_height, item_font, meta_font)
    return y + rows * (card_height + gap)


def _draw_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    item: MenuItem,
    x: int,
    y: int,
    width: int,
    height: int,
    item_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    meta_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    card_box = (x, y, x + width, y + height)
    draw.rounded_rectangle(card_box, radius=CARD_RADIUS, fill=ImageColor.getrgb(CARD_BACKGROUND))

    image_bottom = y + (250 if height <= 360 else 290)
    image_box = (x + 14, y + 14, x + width - 14, image_bottom)
    _paste_cover_image(canvas, Path(item.image_path), image_box)

    title = item.name.strip()
    price = item.price or ""
    title_y = image_box[3] + 18
    title_lines = textwrap.wrap(title, width=24) or [title]
    title_block = _truncate_lines("\n".join(title_lines), 2)
    draw.multiline_text(
        (x + 20, title_y),
        title_block,
        fill=TEXT,
        font=item_font,
        spacing=4,
    )
    if price:
        price_box = draw.textbbox((0, 0), price, font=item_font)
        price_width = price_box[2] - price_box[0]
        draw.text((x + width - 20 - price_width, title_y), price, fill=ACCENT, font=item_font)
    description = (item.description or "").strip()
    if description:
        wrapped = textwrap.fill(description, width=32)
        draw.multiline_text(
            (x + 20, image_box[3] + 76),
            _truncate_lines(wrapped, 2),
            fill=MUTED,
            font=meta_font,
            spacing=4,
        )


def _paste_cover_image(canvas: Image.Image, image_path: Path, box: tuple[int, int, int, int]) -> None:
    source = Image.open(image_path).convert("RGB")
    box_width = box[2] - box[0]
    box_height = box[3] - box[1]
    background = _resize_cover(source, box_width, box_height).filter(ImageFilter.GaussianBlur(radius=16))
    framed = background.copy()

    inset = 14
    inner_width = max(box_width - inset * 2, 1)
    inner_height = max(box_height - inset * 2, 1)
    scale = min(inner_width / source.width, inner_height / source.height)
    new_width = max(int(source.width * scale), 1)
    new_height = max(int(source.height * scale), 1)
    resized = source.resize((new_width, new_height))
    offset_x = (box_width - new_width) // 2
    offset_y = (box_height - new_height) // 2
    framed.paste(resized, (offset_x, offset_y))
    mask = Image.new("L", (box_width, box_height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, box_width, box_height), radius=24, fill=255)
    canvas.paste(framed, (box[0], box[1]), mask)


def _resize_cover(source: Image.Image, width: int, height: int) -> Image.Image:
    src_ratio = source.width / source.height
    dst_ratio = width / height
    if src_ratio > dst_ratio:
        new_height = height
        new_width = max(int(new_height * src_ratio), 1)
    else:
        new_width = width
        new_height = max(int(new_width / src_ratio), 1)
    resized = source.resize((new_width, new_height))
    left = max((new_width - width) // 2, 0)
    top = max((new_height - height) // 2, 0)
    return resized.crop((left, top, left + width, top + height))


def _draw_menu_columns(
    draw: ImageDraw.ImageDraw,
    sections: Sequence[MenuSection],
    *,
    top: int,
    bottom: int,
    section_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    item_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    col_gap = 40
    cols = 3
    col_width = (CANVAS_WIDTH - 160 - col_gap * (cols - 1)) // cols
    x_positions = [80 + idx * (col_width + col_gap) for idx in range(cols)]
    current_col = 0
    current_y = top

    for section in sections:
        block_height = _estimate_section_height(section)
        if current_y + block_height > bottom and current_col < cols - 1:
            current_col += 1
            current_y = top
        x = x_positions[current_col]
        draw.text((x, current_y), section.name, fill=ACCENT, font=section_font)
        current_y += 40
        for item in section.items:
            name = item.name.strip()
            price = item.price or ""
            wrapped = textwrap.wrap(name, width=22) or [name]
            name_line = wrapped[0]
            draw.text((x, current_y), name_line, fill=TEXT, font=item_font)
            if price:
                price_box = draw.textbbox((0, 0), price, font=item_font)
                price_width = price_box[2] - price_box[0]
                draw.text((x + col_width - price_width, current_y), price, fill=TEXT, font=item_font)
            current_y += 28
            if len(wrapped) > 1:
                draw.text((x, current_y), _truncate_text(wrapped[1], 22), fill=MUTED, font=small_font)
                current_y += 20
            current_y += 8
        current_y += 12


def _estimate_section_height(section: MenuSection) -> int:
    height = 48
    for item in section.items:
        wrapped_lines = max(1, math.ceil(len(item.name.strip()) / 22))
        height += 36 + max(0, wrapped_lines - 1) * 20
    return height


def _iter_items(menu: MenuDocument) -> Iterable[MenuItem]:
    for section in menu.sections:
        for item in section.items:
            yield item


def _load_font(
    size: int,
    *,
    bold: bool = False,
    serif: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if serif and bold:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
            ]
        )
    elif serif:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
            ]
        )
    elif bold:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            ]
        )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _truncate_lines(text: str, line_limit: int) -> str:
    lines = text.splitlines()
    if len(lines) <= line_limit:
        return text
    return "\n".join(lines[:line_limit]).rstrip() + "…"


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
