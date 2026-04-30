# DishFramed

DishFramed turns restaurant menu photos into a clean visual menu with representative dish imagery.

## What It Is

The intended Server3 flow is:

1. A user sends one or more menu photos in Telegram.
2. DishFramed extracts the menu structure from the images.
3. DishFramed normalizes sections, dish names, prices, and descriptions.
4. DishFramed generates or sources representative dish imagery.
5. DishFramed composes a polished visual menu.
6. The bot sends the result back to Telegram as an image or document.

## Product Positioning

DishFramed is not trying to recover the exact real dish photography of every restaurant.
The first objective is a high-quality visual reconstruction that is useful, attractive, and fast.

## MVP Scope

- Accept menu photos
- Extract structured dishes
- Generate representative dish prompts
- Render a framed menu layout
- Return result through Telegram

## Initial Repo Shape

- `src/dishframed/menu_parser.py`
  Menu extraction contracts and normalized structures.
- `src/dishframed/pipeline.py`
  End-to-end orchestration from photo input to render output.
- `src/dishframed/render.py`
  Renderer contracts and a simple development renderer.
- `src/dishframed/cli.py`
  Local CLI entrypoint for development and testing.
- `docs/mvp.md`
  Build order and architectural decisions.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
dishframed --help
pytest -q
```

