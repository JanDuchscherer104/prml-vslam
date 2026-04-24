"""Focused tests for the Rich-backed console wrapper."""

from __future__ import annotations

from prml_vslam.utils.console import Console, _ConsoleLogHighlighter


def test_console_logging_renders_namespace_prefix(capsys) -> None:
    Console.configure_logging(force=True)

    console = Console("prml_vslam.pipeline.backend_ray").child("RayPipelineBackend").child("demo")
    console.info("hello %s", "world")

    captured = capsys.readouterr()

    assert "[pipeline.backend_ray.RayPipelineBackend.demo]" in captured.out
    assert "hello world" in captured.out


def test_console_logging_config_uses_namespace_highlighter() -> None:
    logger = Console.configure_logging(force=True)

    assert logger.handlers
    handler = logger.handlers[0]
    assert isinstance(handler.highlighter, _ConsoleLogHighlighter)
    assert Console._rich_console.get_style("log.namespace_prefix")


def test_console_log_highlighter_preserves_namespace_and_repr_payload_styles() -> None:
    highlighter = _ConsoleLogHighlighter()

    rendered = highlighter(
        "[pipeline.demo] SLAM processed=73 fps=13.29 "
        "refs=[('keyframe_pointmap', 'colors', 'image', (224, 224, 3), 'uint8')]"
    )
    styles = {str(span.style) for span in rendered.spans}

    assert "log.namespace_prefix" in styles
    assert "repr.attrib_name" in styles
    assert "repr.number" in styles
    assert "repr.str" in styles
    assert "repr.brace" in styles


def test_console_exception_renders_with_namespace_prefix(capsys) -> None:
    Console.configure_logging(force=True)
    console = Console("prml_vslam.pipeline.coordinator")

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        console.exception("failed")

    captured = capsys.readouterr()
    assert "[pipeline.coordinator]" in captured.out
    assert "failed" in captured.out
