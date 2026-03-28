"""Convert PDF specifications to markdown spec directories using an OpenCode agent."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

from PIL import Image

from .opencode_runtime import (
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
_READ_LOG_RE = re.compile(r"permission permission=read pattern=(\S+page-(\d+)\.png)")


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


def _render_pdf_page_images(
    pdf_path: Path,
    pages_dir: Path,
    *,
    dpi: int = 300,
) -> tuple[Path, ...]:
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    pages_dir.mkdir(parents=True)
    subprocess.run(
        ("pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(pages_dir / "page")),
        check=True,
        capture_output=True,
        text=True,
    )
    page_images = tuple(sorted(p for p in pages_dir.glob("page-*.png") if p.is_file()))
    if not page_images:
        raise RuntimeError(f"pdftoppm did not render any page images for {pdf_path}")
    return page_images


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
    process = subprocess.Popen(
        command,
        cwd=request.workspace_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    start = time.monotonic()
    ready_since: float | None = None

    while True:
        returncode = process.poll()
        ready = _output_ready(output_dir)
        reads_complete = not _missing_read_page_numbers(
            workspace_root=request.workspace_root,
            pages_dir=pages_dir,
        )
        if returncode is not None:
            stdout, stderr = process.communicate()
            return OpenCodeRunResult(
                command=command,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )

        if ready and reads_complete:
            if ready_since is None:
                ready_since = time.monotonic()
            elif time.monotonic() - ready_since >= _OUTPUT_SETTLE_S:
                stdout, stderr = _terminate_process_tree(process)
                return OpenCodeRunResult(
                    command=command,
                    returncode=0,
                    stdout=stdout,
                    stderr=stderr,
                )
        else:
            ready_since = None

        if time.monotonic() - start >= timeout_s:
            stdout, stderr = _terminate_process_tree(process)
            if (ready or _output_ready(output_dir)) and reads_complete:
                return OpenCodeRunResult(
                    command=command,
                    returncode=0,
                    stdout=stdout,
                    stderr=stderr,
                )
            raise subprocess.TimeoutExpired(
                command,
                timeout_s,
                output=stdout,
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
    _render_pdf_page_images(episode.workspace.pdf_path, episode.workspace.pages_dir)
    try:
        result = run_converter_opencode(
            episode.request,
            output_dir=agent_output,
            pages_dir=episode.workspace.pages_dir,
            timeout_s=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        if _markdown_files(agent_output):
            _assert_all_rendered_pages_read(
                workspace_root=episode.workspace.root,
                pages_dir=episode.workspace.pages_dir,
            )
            _assert_no_full_page_figure_copies(
                output_dir=agent_output,
                pages_dir=episode.workspace.pages_dir,
            )
            return _copy_agent_output(agent_output, out)
        raise RuntimeError(
            f"converter agent timed out after {timeout_s}s for {pdf}"
        ) from exc
    if result.returncode != 0 and not _markdown_files(agent_output):
        raise RuntimeError(
            f"converter agent failed (exit {result.returncode}):\n{result.stderr[:2000]}"
        )
    if not _markdown_files(agent_output):
        raise RuntimeError(
            "converter agent exited without producing any markdown output:\n"
            f"{result.stderr[:2000]}"
        )
    _assert_all_rendered_pages_read(
        workspace_root=episode.workspace.root,
        pages_dir=episode.workspace.pages_dir,
    )
    _assert_no_full_page_figure_copies(
        output_dir=agent_output,
        pages_dir=episode.workspace.pages_dir,
    )

    return _copy_agent_output(agent_output, out)
