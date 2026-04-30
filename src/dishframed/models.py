from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    name: str
    price: Optional[str] = None
    description: Optional[str] = None
    image_prompt: Optional[str] = None
    image_path: Optional[Path] = None


class MenuSection(BaseModel):
    name: str
    items: List[MenuItem] = Field(default_factory=list)


class MenuDocument(BaseModel):
    title: str = "Menu"
    restaurant_name: Optional[str] = None
    sections: List[MenuSection] = Field(default_factory=list)
    source_notes: List[str] = Field(default_factory=list)


class RenderArtifact(BaseModel):
    output_path: Path
    preview_text: str

