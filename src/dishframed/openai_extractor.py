from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Protocol, Sequence

from pydantic import BaseModel, Field

from .menu_parser import MenuExtractor, coerce_menu_document
from .models import MenuDocument, MenuItem, MenuSection

DEFAULT_MODEL = "gpt-5.4"
DEFAULT_REASONING_EFFORT = "low"


class _ResponsesClient(Protocol):
    def parse(self, **kwargs): ...


class _OpenAIClientLike(Protocol):
    responses: _ResponsesClient


class OpenAIExtractorItem(BaseModel):
    name: str
    price: str | None = None
    description: str | None = None
    image_prompt: str | None = None


class OpenAIExtractorSection(BaseModel):
    name: str
    items: list[OpenAIExtractorItem] = Field(default_factory=list)


class OpenAIExtractorResult(BaseModel):
    title: str = "Extracted Menu"
    restaurant_name: str | None = None
    subtitle: str | None = None
    sections: list[OpenAIExtractorSection] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)


def _guess_media_type(image_path: Path) -> str:
    media_type, _ = mimetypes.guess_type(image_path.name)
    return media_type or "image/jpeg"


def _image_to_data_url(image_path: Path) -> str:
    payload = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    media_type = _guess_media_type(image_path)
    return f"data:{media_type};base64,{payload}"


def _build_prompt() -> str:
    return (
        "Extract a restaurant menu from these image(s). "
        "Return only the structured menu content. "
        "Preserve section names, dish names, prices, and short descriptions when visible. "
        "Do not invent items that are not present. "
        "If the menu title or restaurant name is unclear, leave it blank rather than guessing. "
        "Keep prices exactly as shown when possible. "
        "Treat multi-column layouts as one menu, not separate menus. "
        "Ignore decorative illustrations that are not menu items. "
        "Preserve repeated items when they appear in different named sections. "
        "Put visible service hours or short header context into subtitle when useful. "
        "Put allergy notes, gluten-free notes, or house notes into source_notes. "
        "For each item, also draft a concise image_prompt suitable for generating a representative dish image later."
    )


def _to_menu_document(result: OpenAIExtractorResult) -> MenuDocument:
    menu = MenuDocument(
        title=result.title,
        restaurant_name=result.restaurant_name,
        subtitle=result.subtitle,
        sections=[
            MenuSection(
                name=section.name,
                items=[
                    MenuItem(
                        name=item.name,
                        price=item.price,
                        description=item.description,
                        image_prompt=item.image_prompt,
                    )
                    for item in section.items
                ],
            )
            for section in result.sections
        ],
        source_notes=result.source_notes,
    )
    return coerce_menu_document(menu)


class OpenAIImageMenuExtractor(MenuExtractor):
    def __init__(
        self,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        client: _OpenAIClientLike | None = None,
    ) -> None:
        self.model = model or os.getenv("DISHFRAMED_OPENAI_MODEL", DEFAULT_MODEL)
        self.reasoning_effort = reasoning_effort or os.getenv(
            "DISHFRAMED_OPENAI_REASONING_EFFORT",
            DEFAULT_REASONING_EFFORT,
        )
        self._client = client

    def _get_client(self) -> _OpenAIClientLike:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "OpenAI SDK is not installed. Run `pip install -e .[dev]` in the DishFramed repo."
            ) from exc

        self._client = OpenAI()
        return self._client

    def extract(self, image_paths: Sequence[Path]) -> MenuDocument:
        missing = [path for path in image_paths if not path.exists()]
        if missing:
            missing_str = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Input image not found: {missing_str}")

        client = self._get_client()
        content = [{"type": "input_text", "text": _build_prompt()}]
        for image_path in image_paths:
            content.append(
                {
                    "type": "input_image",
                    "image_url": _image_to_data_url(image_path),
                }
            )

        response = client.responses.parse(
            model=self.model,
            input=[{"role": "user", "content": content}],
            text_format=OpenAIExtractorResult,
            reasoning={"effort": self.reasoning_effort},
            store=False,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI extraction returned no structured output.")
        if not isinstance(parsed, OpenAIExtractorResult):
            parsed = OpenAIExtractorResult.model_validate(parsed)

        menu = _to_menu_document(parsed)
        menu.source_notes.append(f"Extracted with OpenAI model {self.model}.")
        return menu
