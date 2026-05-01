# DishFramed

DishFramed turns restaurant menu photos into a clean visual menu with representative dish imagery.

Telegram is the intended primary user interface, but the core pipeline is being built so it can also run from a local CLI and later a small web/API surface.

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
- Support local JSON-to-preview rendering for fast iteration

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

Render the included sample menu into a preview poster:

```bash
dishframed render-menu examples/sample_menu.json
```

This writes:

- `artifacts/menu_preview.svg`
- `artifacts/menu_preview.html`

Parse OCR-style menu text into structured JSON and a preview:

```bash
dishframed parse-text examples/sample_menu_ocr.txt --title "Breakfast Demo"
```

On Architect/Server3, the default path now prefers the existing authenticated Codex CLI image-analysis path, so no separate OpenAI API key is required there.

Try GPT-based extraction from real menu image(s) with Architect auth:

```bash
cd /home/architect/dishframed
. .venv/bin/activate
dishframed frame --extractor codex --image path/to/menu.jpg
```

Optional extractor env:

- `DISHFRAMED_EXTRACTOR=codex|openai|stub|auto`
- `DISHFRAMED_CODEX_MODEL=gpt-5.4`
- `DISHFRAMED_CODEX_REASONING_EFFORT=low`
- `DISHFRAMED_OPENAI_MODEL=gpt-5.4`
- `DISHFRAMED_OPENAI_REASONING_EFFORT=low`

Optional image-generation env:

- `DISHFRAMED_IMAGE_PROVIDER=auto|venice|openai|codex|none`
- `DISHFRAMED_OPENAI_IMAGE_MODEL=gpt-image-1`
- `DISHFRAMED_OPENAI_IMAGE_QUALITY=medium`
- `DISHFRAMED_OPENAI_IMAGE_SIZE=1024x1024`
- `DISHFRAMED_VENICE_IMAGE_MODEL=qwen-image-2-pro`

Notes:

- `codex` is accepted as an alias for the OpenAI-backed image path so DishFramed can use the same OpenAI family as the extractor.
- `auto` preserves the current behavior order: Venice first when `VENICE_API_KEY` is present, then OpenAI when `OPENAI_API_KEY` is present, otherwise no representative dish images are generated.

If you explicitly want direct OpenAI API usage instead of shared Codex auth:

```bash
export OPENAI_API_KEY=your_key_here
dishframed frame --extractor openai --image path/to/menu.jpg
```

To force the OpenAI-backed image generator for representative dish photos:

```bash
export OPENAI_API_KEY=your_key_here
export DISHFRAMED_IMAGE_PROVIDER=codex
dishframed frame --extractor codex --image path/to/menu.jpg
```
