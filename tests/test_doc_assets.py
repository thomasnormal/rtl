from __future__ import annotations

from pathlib import Path
import re

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
DIRECT_PAGE_REF_RE = re.compile(r"(^|/)(pages/page-\d+\.png|output/pages/page-\d+\.png)$")


def _active_doc_roots() -> list[Path]:
    docs: list[Path] = []
    for doc in sorted((REPO_ROOT / "task_library" / "avip").glob("*/doc/*")):
        if doc.is_dir() and not doc.name.endswith(".old"):
            docs.append(doc)
    for doc in sorted((REPO_ROOT / "task_library" / "riscv_hardware_specs").glob("task_*/doc")):
        if doc.is_dir():
            docs.append(doc)
    return docs


def test_task_library_doc_image_refs_exist_and_do_not_point_to_staging_pages() -> None:
    problems: list[str] = []
    for doc in _active_doc_roots():
        for md in sorted(doc.glob("*.md")):
            seen: set[str] = set()
            for ref in IMAGE_REF_RE.findall(md.read_text(errors="ignore")):
                if ref.startswith(("http://", "https://")):
                    continue
                if DIRECT_PAGE_REF_RE.search(ref):
                    problems.append(
                        f"stale staged-page reference in {md.relative_to(REPO_ROOT)}: {ref}"
                    )
                if ref in seen:
                    problems.append(
                        f"duplicate image reference in {md.relative_to(REPO_ROOT)}: {ref}"
                    )
                seen.add(ref)
                if not (md.parent / ref).exists():
                    problems.append(
                        f"missing image asset in {md.relative_to(REPO_ROOT)}: {ref}"
                    )
    assert not problems, "\n".join(problems)


def test_task_library_figure_assets_are_not_full_page_renders() -> None:
    suspicious: list[str] = []
    for doc in _active_doc_roots():
        figures_dir = doc / "figures"
        if not figures_dir.is_dir():
            continue
        for png in sorted(figures_dir.glob("*.png")):
            width, height = Image.open(png).size
            if width >= 2000 and height >= 2500:
                suspicious.append(f"{png.relative_to(REPO_ROOT)} {width}x{height}")
    assert not suspicious, "\n".join(suspicious)
