from __future__ import annotations

from pathlib import Path
import re

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
AVIP_DOC_ROOT = REPO_ROOT / "task_library" / "avip"
IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\((figures/[^)]+\.png)\)")
AHB_DOC_ROOT = AVIP_DOC_ROOT / "ahb_slave" / "doc" / "AhbAvipArchitectureDocument"


def _active_doc_dirs() -> list[Path]:
    docs: list[Path] = []
    for doc in sorted(AVIP_DOC_ROOT.glob("*/doc/*")):
        if doc.is_dir() and not doc.name.endswith(".old"):
            docs.append(doc)
    return docs


def test_active_avip_figure_assets_are_not_full_page_renders() -> None:
    suspicious: list[str] = []
    for doc_dir in _active_doc_dirs():
        figures_dir = doc_dir / "figures"
        if not figures_dir.is_dir():
            continue
        for png in sorted(figures_dir.glob("*.png")):
            width, height = Image.open(png).size
            if width >= 2000 and height >= 2500:
                suspicious.append(f"{png.relative_to(REPO_ROOT)} {width}x{height}")
    assert not suspicious, "\n".join(suspicious)


def test_active_avip_markdown_uses_distinct_existing_figure_assets() -> None:
    problems: list[str] = []
    for doc_dir in _active_doc_dirs():
        for md in sorted(doc_dir.glob("*.md")):
            refs = IMAGE_REF_RE.findall(md.read_text())
            seen: set[str] = set()
            for ref in refs:
                if ref in seen:
                    problems.append(f"duplicate image reference in {md.relative_to(REPO_ROOT)}: {ref}")
                seen.add(ref)
                if not (doc_dir / ref).is_file():
                    problems.append(f"missing figure asset for {md.relative_to(REPO_ROOT)}: {ref}")
    assert not problems, "\n".join(problems)


def test_ahb_architecture_figure_2_1_is_tightly_cropped() -> None:
    png = (
        AVIP_DOC_ROOT
        / "ahb_slave"
        / "doc"
        / "AhbAvipArchitectureDocument"
        / "figures"
        / "figure-009.png"
    )
    width, height = Image.open(png).size
    assert width <= 1900 and height <= 950, f"{png.relative_to(REPO_ROOT)} {width}x{height}"


def test_ahb_architecture_figure_2_1_has_visible_caption() -> None:
    md = (
        AHB_DOC_ROOT
        / "02_architecture.md"
    )
    text = md.read_text()
    assert "*Figure 2.1: AHB-AVIP Architecture*" in text


def test_ahb_chapters_have_no_page_dump_artifacts() -> None:
    problems: list[str] = []
    for md in sorted(AHB_DOC_ROOT.glob("[0-9][0-9]_*.md")):
        if md.name == "00_front_matter.md":
            continue
        text = md.read_text()
        if "<!-- page " in text:
            problems.append(f"page markers remain in {md.relative_to(REPO_ROOT)}")
        if re.search(r"AHB_AVIP\s+\d+", text):
            problems.append(f"footer text remains in {md.relative_to(REPO_ROOT)}")
        if re.search(r"^Chapter \d+$", text, re.M):
            problems.append(f"duplicate chapter heading remains in {md.relative_to(REPO_ROOT)}")
    assert not problems, "\n".join(problems)


def test_ahb_chapters_have_visible_captions_for_embedded_figures() -> None:
    problems: list[str] = []
    for md in sorted(AHB_DOC_ROOT.glob("[0-9][0-9]_*.md")):
        text = md.read_text()
        refs = re.findall(r"!\[Figure\s*([0-9.]+):\s*([^\]]+)\]\((figures/[^)]+\.png)\)", text)
        for num, title, _ in refs:
            caption = f"*Figure {num}: {title}*"
            if caption not in text:
                problems.append(f"missing visible caption in {md.relative_to(REPO_ROOT)}: {caption}")
    assert not problems, "\n".join(problems)


def test_ahb_chapters_embed_figures_they_name() -> None:
    problems: list[str] = []
    fig_label_re = re.compile(r"Fig\.?\s*([0-9]+)\s*\.\s*([0-9]+)")
    for md in sorted(AHB_DOC_ROOT.glob("[0-9][0-9]_*.md")):
        if md.name == "00_front_matter.md":
            continue
        text = md.read_text()
        refs = {f"{major}.{minor}" for major, minor in re.findall(r"!\[Figure\s*([0-9]+)\.([0-9]+):", text)}
        labels = {f"{major}.{minor}" for major, minor in fig_label_re.findall(text)}
        missing = sorted(label for label in labels if label not in refs)
        if missing:
            problems.append(f"{md.relative_to(REPO_ROOT)} missing embeds for: {', '.join(missing)}")
    assert not problems, "\n".join(problems)
