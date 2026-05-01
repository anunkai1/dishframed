from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional, Sequence

from .menu_parser import MenuExtractor, coerce_menu_document
from .models import MenuDocument

DEFAULT_CODEX_MODEL = "gpt-5.4"
DEFAULT_CODEX_REASONING_EFFORT = "low"
CODEX_OUTPUT_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _build_prompt() -> str:
    return (
        "Analyze the provided restaurant menu image or images and return only valid JSON. "
        "Use this schema exactly: "
        '{"title": string, "restaurant_name": string|null, "subtitle": string|null, '
        '"sections": [{"name": string, "items": [{"name": string, "price": string|null, '
        '"description": string|null, "image_prompt": string|null}]}], '
        '"source_notes": [string]}. '
        "Preserve section names, dish names, prices, and short descriptions when visible. "
        "Do not invent unseen items. "
        "If a field is unclear, use null or an empty list instead of guessing. "
        "Treat multi-column layouts as one menu, not separate menus. "
        "Ignore decorative illustrations that are not menu items. "
        "Preserve repeated items when they appear in different named sections. "
        "Put visible service hours or short header context into subtitle when useful. "
        "Put allergy notes, gluten-free notes, or house notes into source_notes. "
        "For each item, draft a short image_prompt for later representative dish generation."
    )


def _parse_codex_output(stdout: str) -> str:
    last_agent_message: Optional[str] = None
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") != "item.completed":
            continue
        item = payload.get("item")
        if not isinstance(item, dict) or item.get("type") != "agent_message":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            last_agent_message = text.strip()
    if last_agent_message:
        return last_agent_message
    return (stdout or "").strip()


def _extract_json_payload(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = CODEX_OUTPUT_JSON_PATTERN.search(cleaned)
        if not match:
            raise RuntimeError("Codex extractor did not return valid JSON.")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Codex extractor returned malformed JSON.") from exc


class CodexImageMenuExtractor(MenuExtractor):
    def __init__(
        self,
        *,
        codex_bin: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        workdir: str | Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.codex_bin = codex_bin or os.getenv("DISHFRAMED_CODEX_BIN", "codex")
        self.model = model or os.getenv("DISHFRAMED_CODEX_MODEL", DEFAULT_CODEX_MODEL)
        self.reasoning_effort = reasoning_effort or os.getenv(
            "DISHFRAMED_CODEX_REASONING_EFFORT",
            DEFAULT_CODEX_REASONING_EFFORT,
        )
        self.workdir = Path(
            workdir or os.getenv("DISHFRAMED_CODEX_WORKDIR", Path.cwd())
        ).expanduser()
        self._runner = runner or subprocess.run

    def extract(self, image_paths: Sequence[Path]) -> MenuDocument:
        missing = [path for path in image_paths if not path.exists()]
        if missing:
            missing_str = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Input image not found: {missing_str}")

        if shutil.which(self.codex_bin) is None:
            raise RuntimeError(f"Codex binary not found: {self.codex_bin}")

        cmd = [
            self.codex_bin,
            "exec",
            "--dangerously-bypass-approvals-and-sandbox",
            "--json",
            "--color",
            "never",
            "-m",
            self.model,
            "-c",
            f'model_reasoning_effort="{self.reasoning_effort}"',
        ]
        for image_path in image_paths:
            cmd.extend(["--image", str(image_path)])
        cmd.append("-")

        result = self._runner(
            cmd,
            input=_build_prompt() + "\n",
            capture_output=True,
            text=True,
            cwd=str(self.workdir),
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            raise RuntimeError(stderr or stdout or f"Codex extractor failed with exit code {result.returncode}.")

        payload = _extract_json_payload(_parse_codex_output(result.stdout or ""))
        menu = coerce_menu_document(MenuDocument.model_validate(payload))
        menu.source_notes.append(f"Extracted with Codex model {self.model}.")
        return menu
