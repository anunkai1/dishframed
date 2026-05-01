import base64
import subprocess
from pathlib import Path

from PIL import Image

from dishframed.codex_extractor import CodexImageMenuExtractor
from dishframed.image_generation import OpenAIImageGenerator, build_food_image_prompt, default_image_generator
from dishframed.menu_parser import StubMenuExtractor, parse_menu_text
from dishframed.models import MenuDocument, MenuItem, MenuSection
from dishframed.openai_extractor import OpenAIImageMenuExtractor
from dishframed.pipeline import DishFramedPipeline, default_extractor, normalize_input_paths


def test_normalize_input_paths_deduplicates_paths(tmp_path: Path) -> None:
    sample = tmp_path / "menu.jpg"
    sample.touch()
    paths = normalize_input_paths([sample, str(sample)])
    assert paths == [sample.resolve()]


def test_pipeline_requires_at_least_one_image() -> None:
    pipeline = DishFramedPipeline()
    try:
        pipeline.build_menu([])
    except ValueError as exc:
        assert "At least one input image path is required." in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty image list.")


def test_pipeline_writes_render_artifact(tmp_path: Path) -> None:
    image = tmp_path / "menu.jpg"
    image.touch()
    output_dir = tmp_path / "out"

    pipeline = DishFramedPipeline(extractor=StubMenuExtractor())
    artifact = pipeline.run([image], output_dir)

    assert artifact.output_path.exists()
    assert artifact.output_path.name == "menu_preview.png"
    assert (output_dir / "menu_preview.svg").exists()
    assert (output_dir / "menu_preview.html").exists()


def test_pipeline_renders_structured_menu_document(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    pipeline = DishFramedPipeline(image_generator=_FakeImageGenerator())
    menu = MenuDocument(
        title="Lunch Demo",
        sections=[
            MenuSection(
                name="Mains",
                items=[
                    MenuItem(
                        name="Chicken Katsu",
                        price="18",
                        description="Crisp cutlet with rice and curry.",
                    )
                ],
            )
        ],
    )

    artifact = pipeline.render_menu(menu, output_dir)

    assert artifact.output_path.exists()
    assert artifact.output_path.name == "menu_preview.png"
    assert artifact.output_path.stat().st_size > 0
    svg = (output_dir / "menu_preview.svg").read_text(encoding="utf-8")
    html = (output_dir / "menu_preview.html").read_text(encoding="utf-8")
    assert "Lunch Demo" in svg
    assert "Lunch Demo" in html
    assert "Chicken Katsu" in html
    assert "Chicken Katsu" in svg


class _FakeImageGenerator:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def generate(self, prompt: str, output_path: Path) -> Path:
        self.calls.append((prompt, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1024, 1024), (220, 180, 120)).save(output_path, format="PNG")
        return output_path


def test_pipeline_generates_featured_item_images(tmp_path: Path, monkeypatch) -> None:
    output_dir = tmp_path / "out"
    monkeypatch.setenv("DISHFRAMED_IMAGE_CACHE_DIR", str(tmp_path / "cache"))
    generator = _FakeImageGenerator()
    pipeline = DishFramedPipeline(image_generator=generator)
    menu = MenuDocument(
        title="Breakfast Demo",
        restaurant_name="The Deck",
        sections=[
            MenuSection(
                name="Classics",
                items=[
                    MenuItem(
                        name="Avocado Toast",
                        price="$24",
                        description="Smashed avocado with feta on sourdough.",
                        image_prompt="Avocado toast with poached egg and feta",
                    )
                ],
            )
        ],
    )

    artifact = pipeline.render_menu(menu, output_dir)

    assert artifact.output_path.exists()
    assert "photo-card" in artifact.preview_text
    assert len(generator.calls) == 1
    assert generator.calls[0][1].exists()


def test_parse_menu_text_builds_sections_and_items() -> None:
    raw = """
    BREAKFAST SIGNATURES
    Kaya French Toast 26
    Pandan-coconut jam, soy caramel.
    Curry and Waffle 20
    Tamarind fish curry.

    BREAKFAST CLASSICS
    Avocado Toast 26
    Salmon cream cheese, watercress.
    """

    menu = parse_menu_text(raw, title="Breakfast Demo")

    assert menu.title == "Breakfast Demo"
    assert len(menu.sections) == 2
    assert menu.sections[0].name == "Breakfast Signatures"
    assert menu.sections[0].items[0].name == "Kaya French Toast"
    assert menu.sections[0].items[0].price == "26"
    assert "Pandan-coconut jam" in (menu.sections[0].items[0].description or "")
    assert menu.sections[1].items[0].name == "Avocado Toast"


def test_default_extractor_uses_stub_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DISHFRAMED_EXTRACTOR", raising=False)
    monkeypatch.setattr("dishframed.pipeline.shutil.which", lambda _: None)

    extractor = default_extractor()

    assert isinstance(extractor, StubMenuExtractor)


def test_default_extractor_prefers_codex_when_available(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DISHFRAMED_EXTRACTOR", raising=False)
    monkeypatch.setattr("dishframed.pipeline.shutil.which", lambda _: "/usr/bin/codex")

    extractor = default_extractor()

    assert isinstance(extractor, CodexImageMenuExtractor)


def test_default_image_generator_prefers_venice_in_auto_mode(monkeypatch) -> None:
    monkeypatch.setenv("VENICE_API_KEY", "venice-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("DISHFRAMED_IMAGE_PROVIDER", raising=False)

    generator = default_image_generator()

    assert generator is not None
    assert generator.__class__.__name__ == "VeniceImageGenerator"


def test_default_image_generator_supports_codex_alias(monkeypatch) -> None:
    monkeypatch.setenv("DISHFRAMED_IMAGE_PROVIDER", "codex")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.delenv("VENICE_API_KEY", raising=False)

    generator = default_image_generator()

    assert isinstance(generator, OpenAIImageGenerator)


def test_default_image_generator_requires_openai_key_for_codex_alias(monkeypatch) -> None:
    monkeypatch.setenv("DISHFRAMED_IMAGE_PROVIDER", "codex")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        default_image_generator()
    except RuntimeError as exc:
        assert "OPENAI_API_KEY is missing" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError when codex image provider has no OPENAI_API_KEY.")


class _FakeParsedResponse:
    def __init__(self, parsed):
        self.output_parsed = parsed


class _FakeResponsesAPI:
    def __init__(self, parsed):
        self.parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeParsedResponse(self.parsed)


class _FakeOpenAIClient:
    def __init__(self, parsed):
        self.responses = _FakeResponsesAPI(parsed)


class _FakeImagesResponse:
    def __init__(self, image_b64: str):
        self.data = [type("ImagePayload", (), {"b64_json": image_b64})()]


class _FakeImagesAPI:
    def __init__(self, image_b64: str):
        self.image_b64 = image_b64
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeImagesResponse(self.image_b64)


class _FakeOpenAIImageClient:
    def __init__(self, image_b64: str):
        self.images = _FakeImagesAPI(image_b64)


def test_openai_extractor_maps_structured_output(tmp_path: Path) -> None:
    image = tmp_path / "menu.jpg"
    image.write_bytes(b"fake-image")
    parsed = {
        "title": "Lunch Menu",
        "restaurant_name": "Cafe Demo",
        "subtitle": "Weekday Specials",
        "sections": [
            {
                "name": "Mains",
                "items": [
                    {
                        "name": "Chicken Katsu",
                        "price": "$18",
                        "description": "Crisp cutlet with curry sauce.",
                        "image_prompt": "Golden chicken katsu with Japanese curry",
                    }
                ],
            }
        ],
        "source_notes": ["Read from uploaded menu image."],
    }
    fake_client = _FakeOpenAIClient(parsed)
    extractor = OpenAIImageMenuExtractor(client=fake_client, model="gpt-5.4")

    menu = extractor.extract([image])

    assert menu.title == "Lunch Menu"
    assert menu.restaurant_name == "Cafe Demo"
    assert menu.sections[0].items[0].name == "Chicken Katsu"
    assert menu.sections[0].items[0].image_prompt == "Golden chicken katsu with Japanese curry"
    assert menu.source_notes[-1] == "Extracted with OpenAI model gpt-5.4."
    assert fake_client.responses.calls[0]["model"] == "gpt-5.4"


def test_codex_extractor_maps_structured_output(tmp_path: Path, monkeypatch) -> None:
    image = tmp_path / "menu.jpg"
    image.write_bytes(b"fake-image")

    def fake_runner(*args, **kwargs):
        del args, kwargs
        return subprocess.CompletedProcess(
            args=["codex"],
            returncode=0,
            stdout=(
                '{"type":"item.completed","item":{"type":"agent_message","text":"'
                '{\\"title\\": \\"Lunch Menu\\", \\"restaurant_name\\": \\"Cafe Demo\\", '
                '\\"subtitle\\": null, \\"sections\\": [{\\"name\\": \\"Mains\\", '
                '\\"items\\": [{\\"name\\": \\"Chicken Katsu\\", \\"price\\": \\"18\\", '
                '\\"description\\": \\"Crisp cutlet with curry sauce.\\", '
                '\\"image_prompt\\": \\"Golden chicken katsu with Japanese curry\\"}]}], '
                '\\"source_notes\\": [\\"Read from image.\\"]}"}}\n'
            ),
            stderr="",
        )

    monkeypatch.setattr("dishframed.codex_extractor.shutil.which", lambda _: "/usr/bin/codex")
    extractor = CodexImageMenuExtractor(runner=fake_runner, model="gpt-5.4")

    menu = extractor.extract([image])

    assert menu.title == "Lunch Menu"
    assert menu.restaurant_name == "Cafe Demo"
    assert menu.sections[0].items[0].name == "Chicken Katsu"
    assert menu.sections[0].items[0].image_prompt == "Golden chicken katsu with Japanese curry"
    assert menu.source_notes[-1] == "Extracted with Codex model gpt-5.4."


def test_openai_image_generator_writes_png(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (32, 32), (120, 90, 30)).save(source, format="PNG")
    image_b64 = base64.b64encode(source.read_bytes()).decode("ascii")
    client = _FakeOpenAIImageClient(image_b64)
    generator = OpenAIImageGenerator(client=client, model="gpt-image-1")
    output_path = tmp_path / "generated.png"

    generated = generator.generate("Golden chicken katsu", output_path)

    assert generated == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"\x89PNG")
    assert client.images.calls[0]["model"] == "gpt-image-1"
    assert client.images.calls[0]["response_format"] == "b64_json"


def test_build_food_image_prompt_uses_menu_context() -> None:
    menu = MenuDocument(restaurant_name="Deck Cafe", title="Breakfast")
    item = MenuItem(
        name="Kaya French Toast",
        description="Pandan-coconut jam, soy caramel, egg jam.",
    )

    prompt = build_food_image_prompt(menu, item)

    assert "Kaya French Toast" in prompt
    assert "Deck Cafe" in prompt
    assert "Photorealistic premium restaurant food photography" in prompt
