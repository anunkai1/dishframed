from __future__ import annotations

from html import escape

from .models import MenuDocument, MenuItem, MenuSection


def _render_item(item: MenuItem) -> str:
    price = f'<div class="item-price">{escape(item.price)}</div>' if item.price else ""
    description = (
        f'<p class="item-description">{escape(item.description)}</p>'
        if item.description
        else ""
    )
    prompt = (
        f'<p class="item-prompt">Prompt: {escape(item.image_prompt)}</p>'
        if item.image_prompt
        else ""
    )
    return (
        '<article class="item-card">'
        '<div class="item-image">'
        f'<div class="item-image-label">{escape(item.name)}</div>'
        "</div>"
        '<div class="item-copy">'
        '<div class="item-header">'
        f'<h3>{escape(item.name)}</h3>'
        f"{price}"
        "</div>"
        f"{description}"
        f"{prompt}"
        "</div>"
        "</article>"
    )


def _render_section(section: MenuSection) -> str:
    items_html = "".join(_render_item(item) for item in section.items)
    return (
        '<section class="menu-section">'
        f'<h2>{escape(section.name)}</h2>'
        f'<div class="item-grid">{items_html}</div>'
        "</section>"
    )


def render_menu_html(menu: MenuDocument) -> str:
    subtitle = f'<p class="hero-subtitle">{escape(menu.subtitle)}</p>' if menu.subtitle else ""
    restaurant_name = (
        f'<p class="restaurant-name">{escape(menu.restaurant_name)}</p>'
        if menu.restaurant_name
        else ""
    )
    sections_html = "".join(_render_section(section) for section in menu.sections)
    source_notes = ""
    if menu.source_notes:
        source_notes = (
            '<section class="notes">'
            "<h2>Source Notes</h2>"
            "<ul>"
            + "".join(f"<li>{escape(note)}</li>" for note in menu.source_notes)
            + "</ul>"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(menu.title)}</title>
    <style>
      :root {{
        --bg: #f4efe7;
        --ink: #24160d;
        --muted: #6f5b4f;
        --panel: rgba(255, 252, 246, 0.88);
        --line: rgba(50, 28, 15, 0.12);
        --accent: #c7682d;
        --accent-2: #f3b45a;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(255,255,255,0.7), transparent 30%),
          linear-gradient(135deg, #efe3d2 0%, #f6f1ea 55%, #ead7bd 100%);
      }}
      .page {{
        width: min(1200px, calc(100vw - 32px));
        margin: 24px auto;
        padding: 28px;
        border-radius: 28px;
        background: var(--panel);
        box-shadow: 0 22px 60px rgba(51, 29, 15, 0.14);
        border: 1px solid var(--line);
      }}
      .hero {{
        padding: 18px 0 28px;
        border-bottom: 1px solid var(--line);
      }}
      .eyebrow {{
        margin: 0 0 10px;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        font-size: 12px;
        color: var(--muted);
      }}
      h1 {{
        margin: 0;
        font-size: clamp(40px, 7vw, 74px);
        line-height: 0.95;
      }}
      .restaurant-name {{
        margin: 12px 0 0;
        font-size: 20px;
        color: var(--muted);
      }}
      .hero-subtitle {{
        margin: 8px 0 0;
        max-width: 720px;
        font-size: 18px;
        color: var(--muted);
      }}
      .menu-section {{
        margin-top: 28px;
      }}
      .menu-section h2 {{
        margin: 0 0 14px;
        font-size: 28px;
      }}
      .item-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 18px;
      }}
      .item-card {{
        overflow: hidden;
        border-radius: 24px;
        background: #fffdf8;
        border: 1px solid var(--line);
      }}
      .item-image {{
        min-height: 180px;
        display: flex;
        align-items: end;
        padding: 18px;
        background:
          linear-gradient(160deg, rgba(199,104,45,0.28), rgba(243,180,90,0.55)),
          linear-gradient(45deg, #8b4a23, #e5a74c);
      }}
      .item-image-label {{
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(255,255,255,0.9);
        font-size: 13px;
      }}
      .item-copy {{
        padding: 16px;
      }}
      .item-header {{
        display: flex;
        align-items: start;
        justify-content: space-between;
        gap: 16px;
      }}
      .item-header h3 {{
        margin: 0;
        font-size: 21px;
      }}
      .item-price {{
        flex: 0 0 auto;
        padding-left: 12px;
        color: var(--accent);
        font-weight: bold;
      }}
      .item-description,
      .item-prompt {{
        margin: 10px 0 0;
        color: var(--muted);
        line-height: 1.45;
      }}
      .item-prompt {{
        font-size: 14px;
      }}
      .notes {{
        margin-top: 32px;
        padding-top: 20px;
        border-top: 1px solid var(--line);
      }}
      .notes h2 {{
        margin: 0 0 8px;
        font-size: 22px;
      }}
      .notes ul {{
        margin: 0;
        padding-left: 20px;
        color: var(--muted);
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <header class="hero">
        <p class="eyebrow">DishFramed Preview</p>
        <h1>{escape(menu.title)}</h1>
        {restaurant_name}
        {subtitle}
      </header>
      {sections_html}
      {source_notes}
    </main>
  </body>
</html>
"""

