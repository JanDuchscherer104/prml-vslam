import importlib.util
from pathlib import Path


def load_mempalace_repo_module():
    module_path = Path(".agents/skills/mempalace-repo/scripts/mempalace_repo.py").resolve()
    spec = importlib.util.spec_from_file_location("mempalace_repo", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mempalace_executable_uses_env_override(monkeypatch):
    module = load_mempalace_repo_module()
    monkeypatch.setenv("MEMPALACE", "/tmp/custom-mempalace")

    assert module.mempalace_executable() == "/tmp/custom-mempalace"


def test_external_paper_text_source_filter_skips_plot_assets(tmp_path):
    module = load_mempalace_repo_module()
    literature_root = tmp_path / "tex-src"
    narrative_source = literature_root / "arXiv-Example" / "main.tex"
    plot_source = literature_root / "arXiv-Example" / "fig" / "outdoor.tex"
    style_source = literature_root / "arXiv-Example" / "cvpr.sty"
    for path in (narrative_source, plot_source, style_source):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("content", encoding="utf-8")

    assert module._is_external_paper_text_source(narrative_source, literature_root)
    assert not module._is_external_paper_text_source(plot_source, literature_root)
    assert not module._is_external_paper_text_source(style_source, literature_root)
