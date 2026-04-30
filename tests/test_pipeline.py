from pathlib import Path

from dishframed.pipeline import DishFramedPipeline, normalize_input_paths


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

    pipeline = DishFramedPipeline()
    artifact = pipeline.run([image], output_dir)

    assert artifact.output_path.exists()
    assert artifact.output_path.name == "menu_preview.json"
