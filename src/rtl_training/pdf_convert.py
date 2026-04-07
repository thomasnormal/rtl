"""Convert PDF specifications to markdown spec directories using an OpenCode agent."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time

from PIL import Image, ImageDraw

from .opencode_runtime import (
    OpenCodeRunRequest,
    OpenCodeRunResult,
    build_run_command,
    build_run_environment,
    ensure_opencode_available,
)
from .runtime import prepare_converter_episode


_OUTPUT_SETTLE_S = 3.0
_TERMINATE_GRACE_S = 10.0
_FULL_PAGE_DIMENSION_RATIO = 0.95
_PAGE_IMAGE_RE = re.compile(r"^page-(\d+)\.png$")
_PAGE_ARTIFACT_RE = re.compile(r"^page-\d+\.png$")
_READ_LOG_RE = re.compile(r"permission permission=read pattern=(\S+page-(\d+)\.png)")
_FIGURE_READ_LOG_RE = re.compile(r"permission permission=read pattern=(\S+\.png)")
_SECTION_MARKDOWN_RE = re.compile(r"^\d{2}_.+\.md$")
_CHUNK_MANIFEST_RE = re.compile(r"^chunk_\d{3}/")


def _markdown_files(output_dir: Path) -> tuple[Path, ...]:
    return tuple(sorted(p for p in output_dir.rglob("*.md") if p.is_file()))


def _copy_agent_output(agent_output: Path, destination: Path) -> Path:
    md_files = _markdown_files(agent_output)
    if not md_files:
        raise RuntimeError(
            f"converter agent did not produce any .md files in {agent_output}"
        )
    shutil.copytree(agent_output, destination)
    return destination.resolve()


def _manifest_files(output_dir: Path) -> tuple[str, ...]:
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        files = manifest.get("files")
        if isinstance(files, list) and all(isinstance(item, str) for item in files):
            return tuple(files)
    return tuple(str(path.relative_to(output_dir)) for path in _markdown_files(output_dir))


def _manifest_page_count(output_dir: Path) -> int:
    manifest_path = output_dir / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        page_count = manifest.get("page_count")
        if isinstance(page_count, int):
            return page_count
    return 0


def _output_ready(output_dir: Path) -> bool:
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        files = _manifest_files(output_dir)
    except json.JSONDecodeError:
        return False
    if not files:
        return False
    return all((output_dir / rel_path).is_file() for rel_path in files)


def _render_single_grid_overlay(
    page_path: Path,
    grid_path: Path,
    *,
    step_px: int = 200,
) -> Path:
    """Render a grid overlay for a single page image."""
    with Image.open(page_path) as image:
        overlay = image.convert("RGB")
    draw = ImageDraw.Draw(overlay)
    width, height = overlay.size

    for x in range(0, width, step_px):
        draw.line(((x, 0), (x, height)), fill=(220, 0, 0), width=2)
        label_x2 = min(x + 92, width - 1)
        draw.rectangle((x + 4, 4, label_x2, 28), fill=(255, 255, 255))
        draw.text((x + 8, 8), str(x), fill=(220, 0, 0))
    for y in range(0, height, step_px):
        draw.line(((0, y), (width, y)), fill=(220, 0, 0), width=2)
        label_y2 = min(y + 28, height - 1)
        draw.rectangle((4, y + 4, min(92, width - 1), label_y2), fill=(255, 255, 255))
        draw.text((8, y + 8), str(y), fill=(220, 0, 0))

    overlay.save(grid_path)
    return grid_path


def _render_pdf_page_images(
    pdf_path: Path,
    pages_dir: Path,
    *,
    dpi: int = 300,
    pages_grid_dir: Path | None = None,
) -> tuple[Path, ...]:
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True)
    if pages_grid_dir is not None:
        if pages_grid_dir.exists():
            shutil.rmtree(pages_grid_dir)
        pages_grid_dir.mkdir(parents=True)

    process = subprocess.Popen(
        ("pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(pages_dir / "page")),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    gridded: set[str] = set()
    while process.poll() is None:
        if pages_grid_dir is not None:
            for page in pages_dir.glob("page-*.png"):
                if page.name not in gridded:
                    grid_path = pages_grid_dir / page.name
                    try:
                        _render_single_grid_overlay(page, grid_path)
                        gridded.add(page.name)
                    except Exception:
                        pass  # file may still be written by pdftoppm
        time.sleep(0.5)

    if process.returncode != 0:
        raise RuntimeError(
            f"pdftoppm failed (exit {process.returncode}): {process.stderr.read()}"
        )

    # Final sweep: grid any pages that appeared after the last poll.
    if pages_grid_dir is not None:
        for page in sorted(pages_dir.glob("page-*.png")):
            if page.name not in gridded:
                _render_single_grid_overlay(page, pages_grid_dir / page.name)

    page_images = tuple(sorted(p for p in pages_dir.glob("page-*.png") if p.is_file()))
    if not page_images:
        raise RuntimeError(f"pdftoppm did not render any page images for {pdf_path}")
    return page_images


def _render_page_grid_overlays(
    pages_dir: Path,
    pages_grid_dir: Path,
    *,
    step_px: int = 200,
) -> tuple[Path, ...]:
    if pages_grid_dir.exists():
        shutil.rmtree(pages_grid_dir)
    pages_grid_dir.mkdir(parents=True)

    overlays: list[Path] = []
    for page in sorted(pages_dir.glob("page-*.png")):
        out_path = pages_grid_dir / page.name
        _render_single_grid_overlay(page, out_path, step_px=step_px)
        overlays.append(out_path)
    return tuple(overlays)


def _rendered_page_numbers(pages_dir: Path) -> tuple[int, ...]:
    page_numbers: list[int] = []
    for path in sorted(pages_dir.glob("page-*.png")):
        match = _PAGE_IMAGE_RE.match(path.name)
        if match:
            page_numbers.append(int(match.group(1)))
    return tuple(page_numbers)


def _opencode_log_paths(workspace_root: Path) -> tuple[Path, ...]:
    log_dir = workspace_root / ".xdg_data" / "opencode" / "log"
    if not log_dir.is_dir():
        return ()
    return tuple(sorted(p for p in log_dir.glob("*.log") if p.is_file()))


def _read_page_numbers_from_logs(
    *,
    workspace_root: Path,
    pages_dir: Path,
) -> tuple[int, ...]:
    pages_root = str(pages_dir.resolve())
    seen: set[int] = set()
    for log_path in _opencode_log_paths(workspace_root):
        for line in log_path.read_text().splitlines():
            match = _READ_LOG_RE.search(line)
            if not match:
                continue
            read_path = match.group(1)
            if not read_path.startswith(pages_root):
                continue
            seen.add(int(match.group(2)))
    return tuple(sorted(seen))


def _missing_read_page_numbers(
    *,
    workspace_root: Path,
    pages_dir: Path,
) -> tuple[int, ...]:
    expected = set(_rendered_page_numbers(pages_dir))
    if not expected:
        return ()
    seen = set(
        _read_page_numbers_from_logs(workspace_root=workspace_root, pages_dir=pages_dir)
    )
    return tuple(sorted(expected - seen))


def _figures_not_read_back(
    *,
    workspace_root: Path,
    output_dir: Path,
) -> tuple[Path, ...]:
    """Return figure PNGs that were written to output/figures/ but never read back.

    The agent is required to read each cropped figure with the read tool to
    verify the crop is correct.  This function surfaces any that were skipped.
    """
    figures_dir = output_dir / "figures"
    if not figures_dir.is_dir():
        return ()
    written = {p.resolve() for p in figures_dir.glob("*.png")}
    if not written:
        return ()

    read_back: set[Path] = set()
    for log_path in _opencode_log_paths(workspace_root):
        for line in log_path.read_text().splitlines():
            m = _FIGURE_READ_LOG_RE.search(line)
            if m:
                read_back.add(Path(m.group(1)).resolve())

    not_read = written - read_back
    return tuple(sorted(not_read))


_PDF_ARTIFACT_STRIP_RE = re.compile(
    r"^\s*\d+\s*$"
    r"|Technical Reference Manual"
    r"|© 20\d\d"
    r"|\(Ask a Question\)"
)


def _pdf_to_word_list(pdf_path: Path) -> tuple[list[str], list[tuple[int, int]]]:
    """Extract words from a PDF using pdftotext.

    Returns ``(words, page_spans)`` where ``page_spans[i]`` is the
    ``(start, end)`` word-index range for page ``i+1``.  Returns empty
    lists when pdftotext is not available or fails.
    """
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [], []
    words: list[str] = []
    page_spans: list[tuple[int, int]] = []
    for page_text in result.stdout.split("\f"):
        start = len(words)
        for line in page_text.splitlines():
            if _PDF_ARTIFACT_STRIP_RE.search(line):
                continue
            words.extend(re.findall(r"[a-z0-9_]+", line.lower()))
        page_spans.append((start, len(words)))
    return words, page_spans


def _md_dir_to_word_list(output_dir: Path) -> list[str]:
    combined = ""
    for f in sorted(output_dir.glob("*.md")):
        combined += f.read_text() + "\n"
    combined = re.sub(r"!\[.*?\]\(.*?\)", " ", combined)
    combined = re.sub(r"\[.*?\]\(.*?\)", " ", combined)
    combined = re.sub(r"[|#*`>_~!]", " ", combined)
    return re.findall(r"[a-z0-9_]+", combined.lower())


def _page_for_word_index(word_idx: int, page_spans: list[tuple[int, int]]) -> int:
    for page_num, (start, end) in enumerate(page_spans, start=1):
        if start <= word_idx < end:
            return page_num
    return len(page_spans)


def _compute_diff_gaps(
    pdf_path: Path,
    output_dir: Path,
    *,
    min_gap: int = 40,
) -> list[dict]:
    """Return a list of text chunks present in the PDF but absent from the markdown.

    Each entry is ``{"size": int, "page": int, "excerpt": str}``.
    Returns an empty list when pdftotext is unavailable.
    """
    import difflib

    pdf_words, page_spans = _pdf_to_word_list(pdf_path)
    if not pdf_words:
        return []
    md_words = _md_dir_to_word_list(output_dir)
    matcher = difflib.SequenceMatcher(None, pdf_words, md_words, autojunk=False)
    gaps = []
    for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
        if tag in ("delete", "replace") and (i2 - i1) >= min_gap:
            page = _page_for_word_index(i1, page_spans)
            excerpt = " ".join(pdf_words[i1 : i1 + 30])
            gaps.append({"size": i2 - i1, "page": page, "excerpt": excerpt})
    gaps.sort(key=lambda g: g["size"], reverse=True)
    return gaps


def _format_gap_review_prompt(gaps: list[dict], output_dir: Path, *, top_k: int = 12) -> str:
    existing = sorted(f.name for f in output_dir.glob("*.md"))
    lines = [
        "All page images have been read. However, a word-level diff between the PDF "
        "and the markdown output found text chunks that may be missing or incomplete.",
        "",
        "Work through each gap below:",
        "  1. Check whether the content is already present in the markdown (it may "
        "have been reformatted as a table, figure reference, or merged section).",
        "  2. If genuinely absent, locate the relevant page image "
        "(input/pages/page-NNN.png) and transcribe the missing content into the "
        "correct markdown file.",
        "  3. If the gap is a figure label, running header, or register table that "
        "pdftotext rendered differently, note that and move on.",
        "",
        f"Existing markdown files: {existing}",
        "",
        "--- GAPS (largest first) ---",
        "",
    ]
    for i, gap in enumerate(gaps[:top_k], start=1):
        lines.append(f"[{i}] ~{gap['size']} words, around PDF page {gap['page']}:")
        lines.append(f'    "{gap["excerpt"]}..."')
        lines.append("")
    return "\n".join(lines)


def _assert_all_rendered_pages_read(*, workspace_root: Path, pages_dir: Path) -> None:
    missing = _missing_read_page_numbers(workspace_root=workspace_root, pages_dir=pages_dir)
    if not missing:
        return
    formatted = ", ".join(str(page) for page in missing)
    raise RuntimeError(
        "converter agent did not read every pre-rendered page image with the read tool; "
        f"missing pages: {formatted}"
    )


def _figure_pngs(output_dir: Path) -> tuple[Path, ...]:
    figures_dir = output_dir / "figures"
    if not figures_dir.is_dir():
        return ()
    return tuple(sorted(p for p in figures_dir.rglob("*.png") if p.is_file()))


def _page_image_sizes(pages_dir: Path) -> tuple[tuple[int, int], ...]:
    sizes: list[tuple[int, int]] = []
    for page in sorted(pages_dir.glob("page-*.png")):
        with Image.open(page) as image:
            sizes.append(image.size)
    return tuple(sizes)


def _looks_like_full_page(
    figure_size: tuple[int, int],
    page_size: tuple[int, int],
) -> bool:
    if figure_size == page_size:
        return True
    return (
        figure_size[0] >= int(page_size[0] * _FULL_PAGE_DIMENSION_RATIO)
        and figure_size[1] >= int(page_size[1] * _FULL_PAGE_DIMENSION_RATIO)
    )


def _suspicious_full_page_figures(
    *,
    output_dir: Path,
    pages_dir: Path,
) -> tuple[str, ...]:
    page_sizes = _page_image_sizes(pages_dir)
    suspicious: list[str] = []
    for figure in _figure_pngs(output_dir):
        with Image.open(figure) as image:
            figure_size = image.size
        if any(_looks_like_full_page(figure_size, page_size) for page_size in page_sizes):
            suspicious.append(str(figure.relative_to(output_dir)))
    return tuple(suspicious)


def _assert_no_full_page_figure_copies(*, output_dir: Path, pages_dir: Path) -> None:
    suspicious = _suspicious_full_page_figures(output_dir=output_dir, pages_dir=pages_dir)
    if not suspicious:
        return
    formatted = ", ".join(suspicious)
    raise RuntimeError(
        "converter agent produced figure assets that look like full-page copies instead "
        f"of cropped figures: {formatted}"
    )


def _page_png_artifacts(output_dir: Path) -> tuple[str, ...]:
    artifacts = [
        str(path.relative_to(output_dir))
        for path in sorted(output_dir.rglob("*.png"))
        if _PAGE_ARTIFACT_RE.match(path.name)
    ]
    return tuple(artifacts)


def _chunk_manifest_entries(output_dir: Path) -> tuple[str, ...]:
    return tuple(path for path in _manifest_files(output_dir) if _CHUNK_MANIFEST_RE.match(path))


def _markdown_layout_violations(
    output_dir: Path,
    *,
    page_count: int,
) -> tuple[str, ...]:
    violations: list[str] = []
    manifest_files = _manifest_files(output_dir)
    if not manifest_files:
        return ("manifest.json does not list any markdown files",)

    markdown_files = [path for path in manifest_files if path.endswith(".md")]
    if not markdown_files:
        return ("manifest.json does not list any markdown files",)

    for rel_path in markdown_files:
        path = Path(rel_path)
        if path.parent != Path("."):
            violations.append(
                f"markdown file must live at the output root, found nested path: {rel_path}"
            )
            continue
        if not _SECTION_MARKDOWN_RE.match(path.name):
            violations.append(
                "markdown file does not follow the required section/chapter naming "
                f"`NN_title.md`: {rel_path}"
            )

    if page_count > 1 and len(markdown_files) < 2:
        violations.append(
            "multi-page PDFs must be split into chapter/high-level section markdown files, "
            f"not a single file: {', '.join(markdown_files)}"
        )

    return tuple(violations)


def assert_converted_spec_layout(
    output_dir: str | Path,
    *,
    page_count: int,
) -> None:
    out = Path(output_dir).resolve()

    page_artifacts = _page_png_artifacts(out)
    if page_artifacts:
        formatted = ", ".join(page_artifacts)
        raise RuntimeError(
            "converter agent left rendered page artifacts in the final output instead of "
            f"only section markdown and figure crops: {formatted}"
        )

    chunk_entries = _chunk_manifest_entries(out)
    if chunk_entries:
        formatted = ", ".join(chunk_entries)
        raise RuntimeError(
            "converter agent output is chunked by arbitrary page ranges instead of chapter/"
            f"section files: {formatted}"
        )

    violations = _markdown_layout_violations(out, page_count=page_count)
    if violations:
        raise RuntimeError("invalid converted spec layout:\n- " + "\n- ".join(violations))


def _process_group_id(process: subprocess.Popen[str]) -> int | None:
    try:
        return os.getpgid(process.pid)
    except ProcessLookupError:
        return None


def _signal_process_tree(process: subprocess.Popen[str], sig: signal.Signals) -> None:
    pgid = _process_group_id(process)
    if pgid is not None:
        try:
            os.killpg(pgid, sig)
            return
        except ProcessLookupError:
            return
    try:
        if sig == signal.SIGKILL:
            process.kill()
        else:
            process.send_signal(sig)
    except ProcessLookupError:
        return


def _terminate_process_tree(
    process: subprocess.Popen[str],
    *,
    grace_s: float = _TERMINATE_GRACE_S,
) -> tuple[str, str]:
    _signal_process_tree(process, signal.SIGTERM)
    try:
        return process.communicate(timeout=grace_s)
    except subprocess.TimeoutExpired:
        _signal_process_tree(process, signal.SIGKILL)
        return process.communicate(timeout=grace_s)


def run_converter_opencode(
    request,
    *,
    output_dir: Path,
    pages_dir: Path,
    timeout_s: int,
) -> OpenCodeRunResult:
    ensure_opencode_available()
    command = build_run_command(request)
    env = build_run_environment(request)
    # stdout is discarded (opencode --format json produces large output that
    # is never used by callers and would deadlock the pipe buffer if not drained).
    # stderr is captured for error diagnostics.
    process = subprocess.Popen(
        command,
        cwd=request.workspace_root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    stderr_buf: list[str] = []
    stderr_thread = threading.Thread(
        target=lambda: stderr_buf.append(process.stderr.read()),  # type: ignore[union-attr]
        daemon=True,
    )
    stderr_thread.start()
    start = time.monotonic()
    ready_since: float | None = None

    def _stderr() -> str:
        stderr_thread.join(timeout=10)
        return "".join(stderr_buf)

    while True:
        returncode = process.poll()
        ready = _output_ready(output_dir)
        reads_complete = not _missing_read_page_numbers(
            workspace_root=request.workspace_root,
            pages_dir=pages_dir,
        )
        if returncode is not None:
            stderr = _stderr()
            return OpenCodeRunResult(
                command=command,
                returncode=returncode,
                stdout="",
                stderr=stderr,
            )

        if ready and reads_complete:
            if ready_since is None:
                ready_since = time.monotonic()
            elif time.monotonic() - ready_since >= _OUTPUT_SETTLE_S:
                _terminate_process_tree(process)
                return OpenCodeRunResult(
                    command=command,
                    returncode=0,
                    stdout="",
                    stderr=_stderr(),
                )
        else:
            ready_since = None

        if time.monotonic() - start >= timeout_s:
            _terminate_process_tree(process)
            stderr = _stderr()
            if (ready or _output_ready(output_dir)) and reads_complete:
                return OpenCodeRunResult(
                    command=command,
                    returncode=0,
                    stdout="",
                    stderr=stderr,
                )
            raise subprocess.TimeoutExpired(
                command,
                timeout_s,
                output="",
                stderr=stderr,
            )

        time.sleep(1)


def plan_pdf_page_ranges(page_count: int, pages_per_chunk: int) -> tuple[tuple[int, int], ...]:
    if page_count < 1:
        raise ValueError(f"page_count must be positive, got {page_count}")
    if pages_per_chunk < 1:
        raise ValueError(f"pages_per_chunk must be positive, got {pages_per_chunk}")

    ranges: list[tuple[int, int]] = []
    start = 1
    while start <= page_count:
        end = min(start + pages_per_chunk - 1, page_count)
        ranges.append((start, end))
        start = end + 1
    return tuple(ranges)


def pdf_page_count(pdf_path: str | Path) -> int:
    pdf = Path(pdf_path).resolve()
    completed = subprocess.run(
        ("pdfinfo", str(pdf)),
        check=True,
        capture_output=True,
        text=True,
    )
    for line in completed.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"pdfinfo did not report a page count for {pdf}")


def extract_pdf_page_range(
    pdf_path: str | Path,
    output_path: str | Path,
    *,
    start_page: int,
    end_page: int,
) -> Path:
    pdf = Path(pdf_path).resolve()
    out = Path(output_path).resolve()
    if start_page < 1 or end_page < start_page:
        raise ValueError(f"invalid page range {start_page}-{end_page}")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(str(pdf))
        if reader.is_encrypted:
            reader.decrypt("")
        writer = PdfWriter()
        for page_idx in range(start_page - 1, min(end_page, len(reader.pages))):
            writer.add_page(reader.pages[page_idx])
        writer.write(str(out))
    except ImportError:
        # Fallback to pdfseparate/pdfunite for environments without pypdf.
        temp_dir = out.parent / f".pages_{out.stem}"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True)
        try:
            subprocess.run(
                (
                    "pdfseparate",
                    "-f",
                    str(start_page),
                    "-l",
                    str(end_page),
                    str(pdf),
                    str(temp_dir / "page-%04d.pdf"),
                ),
                check=True,
                capture_output=True,
                text=True,
            )
            page_files = tuple(sorted(temp_dir.glob("page-*.pdf")))
            if not page_files:
                raise RuntimeError(
                    f"pdfseparate did not extract pages {start_page}-{end_page} from {pdf}"
                )
            subprocess.run(
                ("pdfunite", *(str(path) for path in page_files), str(out)),
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    return out


def combine_chunk_output_dirs(
    chunk_output_dirs: tuple[Path, ...] | list[Path],
    output_dir: str | Path,
) -> Path:
    out = Path(output_dir).resolve()
    if out.exists():
        raise FileExistsError(f"output directory already exists: {out}")

    out.mkdir(parents=True)
    files: list[str] = []
    total_pages = 0
    for index, chunk_dir in enumerate(chunk_output_dirs, start=1):
        chunk_path = Path(chunk_dir).resolve()
        dest_name = f"chunk_{index:03d}"
        dest_path = out / dest_name
        shutil.copytree(chunk_path, dest_path)
        files.extend(f"{dest_name}/{path}" for path in _manifest_files(dest_path))
        total_pages += _manifest_page_count(dest_path)

    manifest = {
        "files": files,
        "page_count": total_pages,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return out


def convert_pdf_to_spec_dir(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    workspace_root: str | Path | None = None,
    model: str | None = None,
    template_root: str | Path | None = None,
    timeout_s: int = 1200,
) -> Path:
    """Convert *pdf_path* to a markdown spec directory at *output_dir*."""
    pdf = Path(pdf_path).resolve()
    out = Path(output_dir).resolve()
    if out.exists():
        raise FileExistsError(f"output directory already exists: {out}")

    ws_root = Path(workspace_root) if workspace_root else pdf.parent / f".convert_{pdf.stem}"
    episode = prepare_converter_episode(
        pdf,
        ws_root,
        template_root=template_root,
        model=model,
    )
    agent_output = episode.workspace.output_dir
    _render_pdf_page_images(
        episode.workspace.pdf_path,
        episode.workspace.pages_dir,
        pages_grid_dir=episode.workspace.pages_grid_dir,
    )
    page_count = len(_rendered_page_numbers(episode.workspace.pages_dir))
    max_continuations = 10
    for attempt in range(1, max_continuations + 1):
        missing = _missing_read_page_numbers(
            workspace_root=episode.workspace.root,
            pages_dir=episode.workspace.pages_dir,
        )
        if attempt == 1:
            request = episode.request
        else:
            existing_md = [f.name for f in _markdown_files(agent_output)]
            missing_str = ", ".join(str(p) for p in missing[:20])
            if len(missing) > 20:
                missing_str += f", ... ({len(missing)} total)"
            unverified_figs = _figures_not_read_back(
                workspace_root=episode.workspace.root,
                output_dir=agent_output,
            )
            fig_note = ""
            if unverified_figs:
                fig_names = [f.name for f in unverified_figs]
                fig_note = (
                    f" Also, these figures were saved but never read back to verify "
                    f"the crop: {fig_names}. Read each one with the read tool and "
                    f"re-crop if the result is wrong."
                )
            continuation_prompt = (
                f"Continue converting the PDF to markdown. "
                f"You already wrote these files: {existing_md}. "
                f"You still need to read and transcribe these page images: {missing_str}. "
                f"Read each remaining input/pages/page-*.png with the read tool, "
                f"transcribe the content into markdown, and update output/manifest.json when done."
                f"{fig_note}"
            )
            request = OpenCodeRunRequest(
                workspace_root=episode.request.workspace_root,
                agent=episode.request.agent,
                prompt=continuation_prompt,
                model=episode.request.model,
                output_format=episode.request.output_format,
                extra_args=episode.request.extra_args,
            )
        try:
            result = run_converter_opencode(
                request,
                output_dir=agent_output,
                pages_dir=episode.workspace.pages_dir,
                timeout_s=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            if _markdown_files(agent_output):
                missing = _missing_read_page_numbers(
                    workspace_root=episode.workspace.root,
                    pages_dir=episode.workspace.pages_dir,
                )
                if not missing:
                    break
            raise RuntimeError(
                f"converter agent timed out after {timeout_s}s for {pdf}"
            ) from exc

        missing = _missing_read_page_numbers(
            workspace_root=episode.workspace.root,
            pages_dir=episode.workspace.pages_dir,
        )
        if not missing and _markdown_files(agent_output):
            break
        if attempt == max_continuations:
            if not _markdown_files(agent_output):
                raise RuntimeError(
                    "converter agent exited without producing any markdown output "
                    f"after {max_continuations} attempts:\n{result.stderr[:2000]}"
                )
            if missing:
                formatted = ", ".join(str(p) for p in missing)
                raise RuntimeError(
                    "converter agent did not read every pre-rendered page image "
                    f"after {max_continuations} attempts; missing pages: {formatted}"
                )

    _assert_all_rendered_pages_read(
        workspace_root=episode.workspace.root,
        pages_dir=episode.workspace.pages_dir,
    )

    # Gap-review pass: diff pdftotext output against markdown to find missed content.
    # Run up to 3 review sessions; stop early when gaps stop shrinking or fall below
    # the trigger threshold.
    _GAP_MIN_WORDS = 40      # minimum gap size to include in the review prompt
    _GAP_TRIGGER = 150       # only run a review session if the largest gap is this big
    _GAP_REVIEW_ATTEMPTS = 3
    prev_top_gap = None
    for _gap_attempt in range(_GAP_REVIEW_ATTEMPTS):
        gaps = _compute_diff_gaps(pdf, agent_output, min_gap=_GAP_MIN_WORDS)
        top_gap = gaps[0]["size"] if gaps else 0
        # Stop if no gap is large enough to be worth reviewing, or if the previous
        # review session made no meaningful improvement.
        if top_gap < _GAP_TRIGGER:
            break
        if prev_top_gap is not None and top_gap >= prev_top_gap * 0.9:
            # Largest gap barely changed — likely a persistent false positive
            # (e.g. a large register table pdftotext renders differently).
            break
        prev_top_gap = top_gap
        gap_prompt = _format_gap_review_prompt(gaps, agent_output)
        gap_request = OpenCodeRunRequest(
            workspace_root=episode.request.workspace_root,
            agent=episode.request.agent,
            prompt=gap_prompt,
            model=episode.request.model,
            output_format=episode.request.output_format,
            extra_args=episode.request.extra_args,
        )
        run_converter_opencode(
            gap_request,
            output_dir=agent_output,
            pages_dir=episode.workspace.pages_dir,
            timeout_s=timeout_s,
        )

    _assert_no_full_page_figure_copies(
        output_dir=agent_output,
        pages_dir=episode.workspace.pages_dir,
    )
    assert_converted_spec_layout(agent_output, page_count=page_count)

    return _copy_agent_output(agent_output, out)
