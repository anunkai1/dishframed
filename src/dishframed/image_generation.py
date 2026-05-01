from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Protocol

from .models import MenuDocument, MenuItem

DEFAULT_VENICE_BASE_URL = "https://api.venice.ai/api/v1"
DEFAULT_VENICE_IMAGE_MODEL = "qwen-image-2-pro"
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-image-1"
DEFAULT_FEATURED_ITEM_LIMIT: int | None = None
DEFAULT_IMAGE_CACHE_DIR = Path.home() / ".cache" / "dishframed" / "generated_items"
SKIP_SECTION_TOKENS = {
    "extras",
    "extra",
    "drinks",
    "beverages",
    "coffee",
    "tea",
    "juice",
    "smoothie",
}
LOW_PRIORITY_SECTION_TOKENS = {"kids", "mini"}
SECTION_PRIORITY = {
    "classics": 6,
    "staples": 5,
    "mains": 5,
    "sweet": 5,
    "light": 4,
    "small": 3,
}


class MenuImageGenerator(Protocol):
    def generate(self, prompt: str, output_path: Path) -> Path:
        """Generate a menu image for the provided prompt."""


def default_image_generator() -> Optional[MenuImageGenerator]:
    provider = os.getenv("DISHFRAMED_IMAGE_PROVIDER", "auto").strip().lower()

    venice_api_key = os.getenv("VENICE_API_KEY", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if provider == "none":
        return None
    if provider in {"codex", "openai"}:
        if not openai_api_key:
            raise RuntimeError(
                "DISHFRAMED_IMAGE_PROVIDER is set to an OpenAI-backed generator, but OPENAI_API_KEY is missing."
            )
        return OpenAIImageGenerator(api_key=openai_api_key)
    if provider == "venice":
        if not venice_api_key:
            raise RuntimeError(
                "DISHFRAMED_IMAGE_PROVIDER=venice requires VENICE_API_KEY to be set."
            )
        return VeniceImageGenerator(
            api_key=venice_api_key,
            base_url=os.getenv("DISHFRAMED_VENICE_BASE_URL", DEFAULT_VENICE_BASE_URL).strip()
            or DEFAULT_VENICE_BASE_URL,
            model=os.getenv("DISHFRAMED_VENICE_IMAGE_MODEL", DEFAULT_VENICE_IMAGE_MODEL).strip()
            or DEFAULT_VENICE_IMAGE_MODEL,
        )
    if provider != "auto":
        raise RuntimeError(
            "Unsupported DISHFRAMED_IMAGE_PROVIDER. Expected one of: auto, venice, openai, codex, none."
        )
    if venice_api_key:
        return VeniceImageGenerator(
            api_key=venice_api_key,
            base_url=os.getenv("DISHFRAMED_VENICE_BASE_URL", DEFAULT_VENICE_BASE_URL).strip()
            or DEFAULT_VENICE_BASE_URL,
            model=os.getenv("DISHFRAMED_VENICE_IMAGE_MODEL", DEFAULT_VENICE_IMAGE_MODEL).strip()
            or DEFAULT_VENICE_IMAGE_MODEL,
        )
    if openai_api_key:
        return OpenAIImageGenerator(api_key=openai_api_key)
    return None


class _OpenAIImagesClient(Protocol):
    def generate(self, **kwargs): ...


class _OpenAIClientLike(Protocol):
    images: _OpenAIImagesClient


class OpenAIImageGenerator:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        quality: str | None = None,
        size: str | None = None,
        client: _OpenAIClientLike | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        self.model = model or os.getenv("DISHFRAMED_OPENAI_IMAGE_MODEL", DEFAULT_OPENAI_IMAGE_MODEL)
        self.quality = quality or os.getenv("DISHFRAMED_OPENAI_IMAGE_QUALITY", "medium")
        self.size = size or os.getenv("DISHFRAMED_OPENAI_IMAGE_SIZE", "1024x1024")
        self._client = client

    def _get_client(self) -> _OpenAIClientLike:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI image generation.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is not installed. Run `pip install -e .[dev]` in the DishFramed repo."
            ) from exc
        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str, output_path: Path) -> Path:
        client = self._get_client()
        response = client.images.generate(
            model=self.model,
            prompt=prompt,
            quality=self.quality,
            size=self.size,
            output_format="png",
            response_format="b64_json",
        )
        if not getattr(response, "data", None):
            raise RuntimeError("OpenAI image generation returned no image data.")
        image_payload = response.data[0]
        image_b64 = getattr(image_payload, "b64_json", None)
        if not image_b64:
            raise RuntimeError("OpenAI image generation did not return base64 image data.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(image_b64))
        return output_path


class VeniceImageGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_VENICE_BASE_URL,
        model: str = DEFAULT_VENICE_IMAGE_MODEL,
        timeout_seconds: int | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds or int(
            os.getenv("DISHFRAMED_VENICE_IMAGE_TIMEOUT_SECONDS", "180")
        )

    def generate(self, prompt: str, output_path: Path) -> Path:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "png",
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "safe_mode": True,
            "hide_watermark": True,
            "return_binary": False,
            "seed": _prompt_seed(prompt),
            "negative_prompt": (
                "text, menu, letters, watermark, logo, collage, multiple plates, hands, people, "
                "table clutter, low resolution, blurry, deformed food, cropped plate"
            ),
        }
        request = urllib.request.Request(
            url=f"{self.base_url}/image/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                parsed = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Venice image generation failed: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Venice image generation failed: {exc.reason}") from exc

        images = parsed.get("images")
        if not isinstance(images, list) or not images or not isinstance(images[0], str):
            raise RuntimeError("Venice image generation did not return image data.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(base64.b64decode(images[0]))
        return output_path


def enrich_menu_with_generated_images(
    menu: MenuDocument,
    *,
    output_dir: Path,
    generator: Optional[MenuImageGenerator],
    featured_item_limit: int | None = DEFAULT_FEATURED_ITEM_LIMIT,
) -> MenuDocument:
    if generator is None:
        return menu

    menu_copy = MenuDocument.model_validate(menu.model_dump(mode="python"))
    cache_dir = Path(
        os.getenv("DISHFRAMED_IMAGE_CACHE_DIR", str(DEFAULT_IMAGE_CACHE_DIR))
    ).expanduser()
    selected = select_featured_items(menu_copy, featured_item_limit=featured_item_limit)
    generated_count = 0
    generation_error: Optional[str] = None
    for item in selected:
        prompt = build_food_image_prompt(menu_copy, item)
        filename = f"{_prompt_hash(prompt)}.png"
        image_path = cache_dir / filename
        if not image_path.exists():
            try:
                generator.generate(prompt, image_path)
            except Exception as exc:
                generation_error = str(exc)
                break
        item.image_path = image_path
        item.image_prompt = prompt
        generated_count += 1

    if generated_count:
        menu_copy.source_notes.append(
            f"Generated {generated_count} representative dish image(s) for featured items."
        )
    if generation_error:
        menu_copy.source_notes.append(
            f"Image generation fallback used because representative photos could not be generated: {generation_error}"
        )
    return menu_copy


def select_featured_items(menu: MenuDocument, featured_item_limit: int | None) -> list[MenuItem]:
    ranked: list[tuple[int, int, MenuItem]] = []
    fallback_ranked: list[tuple[int, int, MenuItem]] = []
    for section in menu.sections:
        section_name = section.name.strip().lower()
        is_skipped_section = any(token in section_name for token in SKIP_SECTION_TOKENS)
        priority = 1
        for token, score in SECTION_PRIORITY.items():
            if token in section_name:
                priority = score
                break
        if any(token in section_name for token in LOW_PRIORITY_SECTION_TOKENS):
            priority = min(priority, 2)
        for item in section.items:
            if not item.name.strip():
                continue
            price_score = _price_value(item.price)
            target = fallback_ranked if is_skipped_section else ranked
            target.append((priority, price_score, item))
    ranked.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    limit = featured_item_limit if featured_item_limit and featured_item_limit > 0 else None
    if ranked:
        selected = ranked if limit is None else ranked[:limit]
        return [item for _, _, item in selected]
    fallback_ranked.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    selected = fallback_ranked if limit is None else fallback_ranked[:limit]
    return [item for _, _, item in selected]


def build_food_image_prompt(menu: MenuDocument, item: MenuItem) -> str:
    description = item.description or ""
    base_prompt = _normalize_prompt_text(item.name.strip() or (item.image_prompt or "signature dish"))
    restaurant_hint = f" from {menu.restaurant_name}" if menu.restaurant_name else ""
    description_clause = (
        f" Dish details: {_normalize_prompt_text(description)}." if description else ""
    )
    return (
        f"Photorealistic premium restaurant food photography of {base_prompt}{restaurant_hint}."
        f"{description_clause} Single plated serving, appetizing composition, natural editorial lighting, "
        "clean ceramic plate or bowl, shallow depth of field, realistic garnish, high-end brunch or cafe menu style. "
        "No text, no collage, no split layout, no menu background, no people, no hands."
    )


def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _prompt_seed(prompt: str) -> int:
    return int(_prompt_hash(prompt)[:8], 16) % 1_000_000_000


def _price_value(price: Optional[str]) -> int:
    if not price:
        return 0
    digits = "".join(char for char in price if char.isdigit())
    if not digits:
        return 0
    try:
        return int(digits[:4])
    except ValueError:
        return 0


def _normalize_prompt_text(text: str) -> str:
    normalized = (
        text.replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    return normalized
