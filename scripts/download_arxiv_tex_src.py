"""Download arXiv e-print source bundles listed in a JSONL manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.request import urlopen

_COPY_CHUNK_SIZE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class ArxivSourceSpec:
    """One manifest entry describing how to fetch arXiv assets."""

    arxiv_id: str
    tex_dir: str
    source_url: str
    pdf_url: str | None = None
    pdf_file: str | None = None
    title: str | None = None

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> ArxivSourceSpec:
        """Build one spec from one JSON object."""

        arxiv_id = _require_non_empty_string(payload, "arxiv_id")
        tex_dir = _require_non_empty_string(payload, "tex_dir")
        source_url = _optional_non_empty_string(payload, "source_url") or f"https://arxiv.org/e-print/{arxiv_id}"
        pdf_url = _optional_non_empty_string(payload, "pdf_url") or f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        pdf_file = _optional_non_empty_string(payload, "pdf_file")
        title = _optional_non_empty_string(payload, "title")
        return cls(
            arxiv_id=arxiv_id,
            tex_dir=tex_dir,
            source_url=source_url,
            pdf_url=pdf_url,
            pdf_file=pdf_file,
            title=title,
        )


def _require_non_empty_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"Manifest entry must provide a non-empty string for {key!r}."
        raise ValueError(msg)
    return value.strip()


def _optional_non_empty_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        msg = f"Manifest entry field {key!r} must be omitted or set to a non-empty string."
        raise ValueError(msg)
    return value.strip()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to the JSONL manifest.")
    parser.add_argument(
        "--tex-root",
        type=Path,
        default=Path("docs/literature/tex-src"),
        help="Directory where extracted TeX source trees will be written.",
    )
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=Path("docs/literature/pdf"),
        help="Directory where PDFs will be written when --download-pdfs is set.",
    )
    parser.add_argument(
        "--download-pdfs",
        action="store_true",
        help="Also download PDFs for entries that define pdf_file.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace already-downloaded target directories and PDFs.",
    )
    return parser.parse_args(argv)


def load_manifest(path: Path) -> list[ArxivSourceSpec]:
    """Load a JSONL manifest into typed source specs."""

    specs: list[ArxivSourceSpec] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            msg = f"Invalid JSON on line {line_number} of {path}: {exc.msg}"
            raise ValueError(msg) from exc
        if not isinstance(payload, dict):
            msg = f"Manifest line {line_number} in {path} must decode to a JSON object."
            raise ValueError(msg)
        try:
            specs.append(ArxivSourceSpec.from_json(payload))
        except ValueError as exc:
            msg = f"Invalid manifest entry on line {line_number} of {path}: {exc}"
            raise ValueError(msg) from exc
    return specs


def download_file(url: str, destination: Path) -> Path:
    """Download one URL to one local path."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, destination.open("wb") as sink:  # noqa: S310
        while True:
            chunk = response.read(_COPY_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            sink.write(chunk)
    return destination


def safe_extract_tarball(archive_path: Path, target_dir: Path) -> None:
    """Extract a tar archive while rejecting unsafe paths."""

    with tarfile.open(archive_path, mode="r:*") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        if not members:
            msg = f"Archive {archive_path} did not contain any regular files."
            raise ValueError(msg)
        for member in members:
            normalized = normalize_member_path(member.name)
            destination = target_dir / Path(*normalized)
            destination.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            if extracted is None:
                msg = f"Could not extract archive member {member.name!r} from {archive_path}."
                raise ValueError(msg)
            with extracted, destination.open("wb") as sink:
                shutil.copyfileobj(extracted, sink)


def normalize_member_path(member_name: str) -> tuple[str, ...]:
    """Normalize one archive member path and reject traversal segments."""

    pure_path = PurePosixPath(member_name)
    if pure_path.is_absolute():
        msg = f"Unsafe archive member path: {member_name!r}"
        raise ValueError(msg)
    parts = tuple(part for part in pure_path.parts if part not in {"", "."})
    if not parts or any(part == ".." for part in parts):
        msg = f"Unsafe archive member path: {member_name!r}"
        raise ValueError(msg)
    return parts


def fetch_tex_source(spec: ArxivSourceSpec, tex_root: Path, *, overwrite: bool) -> Path:
    """Download and extract one arXiv TeX source tree."""

    target_dir = tex_root / spec.tex_dir
    if target_dir.exists():
        if not overwrite:
            print(f"Skipping existing TeX source tree: {target_dir}")
            return target_dir
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="arxiv-tex-src-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        bundle_path = download_file(spec.source_url, temp_dir / "source.bundle")
        safe_extract_tarball(bundle_path, target_dir)

    print(f"Fetched {spec.arxiv_id} source into {target_dir}")
    return target_dir


def fetch_pdf(spec: ArxivSourceSpec, pdf_root: Path, *, overwrite: bool) -> Path | None:
    """Download one PDF if the manifest entry requests it."""

    if spec.pdf_file is None:
        print(f"Skipping PDF for {spec.arxiv_id}: manifest entry has no pdf_file")
        return None
    if spec.pdf_url is None:
        msg = f"Manifest entry for {spec.arxiv_id} requested a PDF target but does not define a PDF URL."
        raise ValueError(msg)

    target_path = pdf_root / spec.pdf_file
    if target_path.exists() and not overwrite:
        print(f"Skipping existing PDF: {target_path}")
        return target_path

    download_file(spec.pdf_url, target_path)
    print(f"Fetched {spec.arxiv_id} PDF into {target_path}")
    return target_path


def run(argv: Sequence[str] | None = None) -> int:
    """Run the downloader CLI."""

    args = parse_args(argv)
    manifest_path = args.manifest.resolve()
    specs = load_manifest(manifest_path)

    tex_root = args.tex_root.resolve()
    pdf_root = args.pdf_root.resolve()
    tex_root.mkdir(parents=True, exist_ok=True)
    if args.download_pdfs:
        pdf_root.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        fetch_tex_source(spec, tex_root, overwrite=args.overwrite)
        if args.download_pdfs:
            fetch_pdf(spec, pdf_root, overwrite=args.overwrite)

    return 0


def main() -> int:
    """CLI entrypoint."""

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
