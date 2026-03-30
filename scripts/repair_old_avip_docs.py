#!/usr/bin/env python3
"""Repair older AVIP doc conversions in task_library/avip.

This repairs the main failures from earlier PDF conversions:
- full-page rendered PNGs saved as figure assets
- repeated reuse of a single page render for multiple figures on the same page
- stale markdown references that point at missing figure filenames
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
AVIP_DOC_ROOT = REPO_ROOT / "task_library" / "avip"
PAGE_RE = re.compile(r"<!-- page (\d+) -->")
IMG_RE = re.compile(r"!\[([^\]]*)\]\((figures/[^)]+\.png)\)")


@dataclass(frozen=True)
class FigureRef:
    md_path: Path
    line_index: int
    page: int | None
    alt_text: str
    asset_rel: str


@dataclass(frozen=True)
class Block:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def _active_doc_dirs() -> list[Path]:
    docs: list[Path] = []
    for doc in sorted(AVIP_DOC_ROOT.glob("*/doc/*")):
        if doc.is_dir() and not doc.name.endswith(".old"):
            docs.append(doc)
    return docs


def _is_full_page_render(image_path: Path) -> bool:
    width, height = Image.open(image_path).size
    return width >= 2000 and height >= 2500


def _tokenize_stem(stem: str) -> list[str]:
    return [tok for tok in re.split(r"[^a-z0-9]+", stem.lower()) if tok and tok != "transfer"]


def _rewrite_missing_refs(doc_dir: Path, lines_by_file: dict[Path, list[str]]) -> None:
    figures_dir = doc_dir / "figures"
    if not figures_dir.is_dir():
        return
    existing = sorted(figures_dir.glob("*.png"))
    existing_by_stem = {p.stem: p for p in existing}
    for md_path, lines in lines_by_file.items():
        for index, line in enumerate(lines):
            match = IMG_RE.search(line)
            if not match:
                continue
            ref = match.group(2)
            asset_path = doc_dir / ref
            if asset_path.is_file():
                continue
            wanted_tokens = _tokenize_stem(Path(ref).stem)
            best: Path | None = None
            best_score = -1
            for candidate in existing_by_stem.values():
                score = len(set(wanted_tokens) & set(_tokenize_stem(candidate.stem)))
                if score > best_score:
                    best = candidate
                    best_score = score
            if best is not None and best_score > 1:
                lines[index] = line.replace(ref, f"figures/{best.name}")


def _parse_refs(doc_dir: Path) -> tuple[dict[Path, list[str]], list[FigureRef]]:
    lines_by_file: dict[Path, list[str]] = {}
    refs: list[FigureRef] = []
    for md_path in sorted(doc_dir.glob("*.md")):
        lines = md_path.read_text().splitlines()
        lines_by_file[md_path] = lines
        current_page: int | None = None
        for index, line in enumerate(lines):
            page_match = PAGE_RE.search(line)
            if page_match:
                current_page = int(page_match.group(1))
            img_match = IMG_RE.search(line)
            if img_match:
                refs.append(
                    FigureRef(
                        md_path=md_path,
                        line_index=index,
                        page=current_page,
                        alt_text=img_match.group(1),
                        asset_rel=img_match.group(2),
                    )
                )
    _rewrite_missing_refs(doc_dir, lines_by_file)
    refs = []
    for md_path, lines in lines_by_file.items():
        current_page = None
        for index, line in enumerate(lines):
            page_match = PAGE_RE.search(line)
            if page_match:
                current_page = int(page_match.group(1))
            img_match = IMG_RE.search(line)
            if img_match:
                refs.append(
                    FigureRef(
                        md_path=md_path,
                        line_index=index,
                        page=current_page,
                        alt_text=img_match.group(1),
                        asset_rel=img_match.group(2),
                    )
                )
    return lines_by_file, refs


def _row_blocks(image_path: Path) -> list[Block]:
    gray = Image.open(image_path).convert("L")
    width, height = gray.size
    pixels = gray.load()
    row_threshold = max(24, int(width * 0.012))
    col_threshold = 8
    rows: list[int] = []
    for y in range(height):
        count = 0
        for x in range(width):
            if pixels[x, y] < 245:
                count += 1
        if count >= row_threshold:
            rows.append(y)
    if not rows:
        return []
    raw_blocks: list[tuple[int, int]] = []
    start = rows[0]
    prev = rows[0]
    for row in rows[1:]:
        if row - prev <= 8:
            prev = row
            continue
        raw_blocks.append((start, prev))
        start = prev = row
    raw_blocks.append((start, prev))

    blocks: list[Block] = []
    for y0, y1 in raw_blocks:
        x_hits: list[int] = []
        for x in range(width):
            count = 0
            for y in range(y0, y1 + 1):
                if pixels[x, y] < 245:
                    count += 1
            if count >= col_threshold:
                x_hits.append(x)
        if not x_hits:
            continue
        block = Block(min(x_hits), y0, max(x_hits) + 1, y1 + 1)
        if block.width >= width * 0.25 and block.height >= max(20, int(height * 0.015)):
            blocks.append(block)
    return blocks


def _is_primary_block(block: Block, width: int, height: int) -> bool:
    return block.width >= width * 0.35 and block.height >= height * 0.05


def _union(blocks: Iterable[Block]) -> Block:
    blocks = list(blocks)
    return Block(
        min(block.x0 for block in blocks),
        min(block.y0 for block in blocks),
        max(block.x1 for block in blocks),
        max(block.y1 for block in blocks),
    )


def _expand(block: Block, width: int, height: int) -> Block:
    pad_x = max(24, int(width * 0.02))
    pad_y = max(24, int(height * 0.02))
    return Block(
        max(0, block.x0 - pad_x),
        max(0, block.y0 - pad_y),
        min(width, block.x1 + pad_x),
        min(height, block.y1 + pad_y),
    )


def _extract_blocks_for_refs(image_path: Path, ref_count: int) -> list[Block]:
    image = Image.open(image_path)
    width, height = image.size
    blocks = _row_blocks(image_path)
    if not blocks:
        return []

    merged: list[Block] = []
    for block in blocks:
        if not merged:
            merged.append(block)
            continue
        previous = merged[-1]
        gap = block.y0 - previous.y1
        if gap <= max(48, int(height * 0.02)):
            merged[-1] = _union((previous, block))
        else:
            merged.append(block)

    groups = [
        _expand(block, width, height)
        for block in merged
        if block.width >= width * 0.25 and block.height >= max(48, int(height * 0.03))
    ]
    if ref_count > 1:
        if groups:
            return groups[: min(ref_count, len(groups))]
        return []
    if groups:
        best = max(
            (block for block in groups if block.y0 < height * 0.85),
            key=lambda block: (block.width * block.height, -block.y0),
            default=None,
        )
        if best is not None:
            return [best]
    return []


def _save_crop(source: Path, dest: Path, block: Block) -> None:
    image = Image.open(source)
    image.crop((block.x0, block.y0, block.x1, block.y1)).save(dest)


def _repair_doc_dir(doc_dir: Path) -> None:
    lines_by_file, refs = _parse_refs(doc_dir)
    refs_by_asset: dict[str, list[FigureRef]] = {}
    for ref in refs:
        refs_by_asset.setdefault(ref.asset_rel, []).append(ref)

    for asset_rel, asset_refs in refs_by_asset.items():
        asset_path = doc_dir / asset_rel
        if not asset_path.is_file() or not _is_full_page_render(asset_path):
            continue
        blocks = _extract_blocks_for_refs(asset_path, len(asset_refs))
        if not blocks:
            continue
        if len(asset_refs) == 1:
            _save_crop(asset_path, asset_path, blocks[0])
            continue

        used_paths: list[Path] = []
        for index, ref in enumerate(asset_refs):
            md_lines = lines_by_file[ref.md_path]
            if index >= len(blocks):
                md_lines[ref.line_index] = ""
                continue
            new_name = f"{asset_path.stem}-{index + 1}{asset_path.suffix}"
            new_rel = f"figures/{new_name}"
            new_path = asset_path.with_name(new_name)
            _save_crop(asset_path, new_path, blocks[index])
            md_lines[ref.line_index] = md_lines[ref.line_index].replace(asset_rel, new_rel)
            used_paths.append(new_path)
        asset_path.unlink()

    for md_path, lines in lines_by_file.items():
        cleaned = "\n".join(line for line in lines if line != "")
        md_path.write_text(cleaned.rstrip() + "\n")


def main() -> int:
    for doc_dir in _active_doc_dirs():
        _repair_doc_dir(doc_dir)
        print(doc_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
