# DishFramed MVP

## Goal

Ship a Telegram-triggered workflow on Server3 that accepts a menu photo and returns a visually framed menu image.

## MVP Sequence

1. Input handling
   - Accept one or more menu photos.
   - Save job metadata and local working files.
2. Menu extraction
   - Detect menu sections.
   - Extract dish names, prices, and descriptions.
   - Normalize into a stable JSON structure.
3. Prompt enrichment
   - Infer cuisine/style hints.
   - Build safe image prompts per dish.
4. Visual generation
   - Generate one representative image per dish or per selected dishes.
5. Layout render
   - Compose card grid or magazine-style poster.
6. Delivery
   - Return image or PDF to Telegram.

## Principles

- Keep OCR/extraction separate from rendering.
- Preserve intermediate JSON for debugging and replay.
- Make rendering deterministic from a structured menu document.
- Cache dish images and normalized menu outputs.
- Treat "exact real dish photo" as out of scope for v1.

## Suggested First Milestones

### Milestone 1
- Local CLI accepts a prebuilt JSON menu and renders a framed mock output.

### Milestone 2
- Plug in real menu extraction from a menu photo.

### Milestone 3
- Plug in image generation.

### Milestone 4
- Attach Telegram workflow.

