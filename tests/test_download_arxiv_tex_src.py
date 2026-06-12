import json

from scripts.download_arxiv_tex_src import load_manifest


def test_load_manifest_skips_reference_only_sources(tmp_path):
    manifest = tmp_path / "sources.jsonl"
    manifest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "title": "Example arXiv paper",
                        "arxiv_id": "1234.56789",
                        "tex_dir": "arXiv-Example",
                    }
                ),
                json.dumps(
                    {
                        "kind": "repository",
                        "title": "SLAM Handbook Public Release",
                        "source_url": ("https://github.com/SLAM-Handbook-contributors/slam-handbook-public-release"),
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    specs = load_manifest(manifest)

    assert len(specs) == 1
    assert specs[0].arxiv_id == "1234.56789"
