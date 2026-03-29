#!/usr/bin/env python3
"""Convert and promote all AVIP public-spec PDFs into markdown directories."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rtl_training.pdf_convert import (  # noqa: E402
    combine_chunk_output_dirs,
    convert_pdf_to_spec_dir,
    extract_pdf_page_range,
    pdf_page_count,
    plan_pdf_page_ranges,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_LIBRARY_ROOT = REPO_ROOT / "task_library" / "avip"
DEFAULT_WORK_ROOT = Path("/tmp/avip-batch-convert")
DEFAULT_MODEL = "openai/gpt-5.4-mini"
DEFAULT_TIMEOUT_S = 1800
DEFAULT_CHUNK_THRESHOLD = 80
DEFAULT_PAGES_PER_CHUNK = 50


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.is_file():
        return
    for raw_line in dotenv_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _all_avip_pdfs() -> tuple[Path, ...]:
    pdfs = []
    for pdf in sorted((REPO_ROOT / "data" / "task_store" / "avip").glob("*/public/spec/**/*.pdf")):
        if "public/spec" not in str(pdf):
            continue
        pdfs.append(pdf.resolve())
    return tuple(pdfs)


def _safe_key(pdf: Path) -> str:
    rel = pdf.relative_to(REPO_ROOT / "data" / "task_store" / "avip")
    return "__".join(rel.with_suffix("").parts)


def _task_spec_root(pdf: Path) -> Path:
    parts = pdf.parts
    for index in range(len(parts) - 1):
        if parts[index] == "public" and parts[index + 1] == "spec":
            return Path(*parts[: index + 2])
    raise ValueError(f"could not locate public/spec root for {pdf}")


def _final_output_dir(pdf: Path) -> Path:
    avip_root = REPO_ROOT / "data" / "task_store" / "avip"
    task_name = pdf.relative_to(avip_root).parts[0]
    return TASK_LIBRARY_ROOT / task_name / "doc" / pdf.stem


def _next_backup_path(path: Path) -> Path:
    candidate = path.parent / f"{path.name}.old"
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = path.parent / f"{path.name}.old{index}"
        if not candidate.exists():
            return candidate
        index += 1


def _promote_output(temp_output: Path, final_output: Path) -> Path:
    final_output.parent.mkdir(parents=True, exist_ok=True)
    if final_output.exists():
        backup = _next_backup_path(final_output)
        shutil.move(str(final_output), str(backup))
        print(f"  backed up existing output -> {backup}")
    shutil.move(str(temp_output), str(final_output))
    return final_output


def _chunked_convert(
    pdf: Path,
    final_output: Path,
    *,
    work_root: Path,
    model: str,
    timeout_s: int,
    allow_page_chunks: bool,
    chunk_threshold: int,
    pages_per_chunk: int,
) -> Path:
    page_count = pdf_page_count(pdf)
    pdf_key = _safe_key(pdf)
    job_root = work_root / pdf_key
    job_root.mkdir(parents=True, exist_ok=True)

    temp_final = job_root / "combined_output"
    if temp_final.exists():
        shutil.rmtree(temp_final)

    if not allow_page_chunks or page_count <= chunk_threshold:
        temp_output = job_root / "single_output"
        if temp_output.exists():
            shutil.rmtree(temp_output)
        workspace_root = job_root / "single_workspace"
        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        convert_pdf_to_spec_dir(
            pdf,
            temp_output,
            workspace_root=workspace_root,
            model=model,
            template_root=REPO_ROOT,
            timeout_s=timeout_s,
        )
        return _promote_output(temp_output, final_output)

    chunk_output_dirs: list[Path] = []
    for index, (start_page, end_page) in enumerate(
        plan_pdf_page_ranges(page_count, pages_per_chunk),
        start=1,
    ):
        print(f"  chunk {index}: pages {start_page}-{end_page}")
        chunk_dir = job_root / f"chunk_{index:03d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)

        chunk_pdf = chunk_dir / f"{pdf.stem}_{start_page:04d}_{end_page:04d}.pdf"
        if not chunk_pdf.exists():
            extract_pdf_page_range(
                pdf,
                chunk_pdf,
                start_page=start_page,
                end_page=end_page,
            )

        chunk_output = chunk_dir / "output"
        if not chunk_output.exists():
            workspace_root = chunk_dir / "workspace"
            if workspace_root.exists():
                shutil.rmtree(workspace_root)
            convert_pdf_to_spec_dir(
                chunk_pdf,
                chunk_output,
                workspace_root=workspace_root,
                model=model,
                template_root=REPO_ROOT,
                timeout_s=timeout_s,
            )
        chunk_output_dirs.append(chunk_output)

    combine_chunk_output_dirs(chunk_output_dirs, temp_final)
    return _promote_output(temp_final, final_output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument(
        "--allow-page-chunks",
        action="store_true",
        help=(
            "Allow fallback chunking by arbitrary page ranges for very large PDFs. "
            "This is structurally worse than chapter-based conversion and is disabled by default."
        ),
    )
    parser.add_argument("--chunk-threshold", type=int, default=DEFAULT_CHUNK_THRESHOLD)
    parser.add_argument("--pages-per-chunk", type=int, default=DEFAULT_PAGES_PER_CHUNK)
    parser.add_argument(
        "--only",
        nargs="*",
        help="Optional list of PDF stem names to convert.",
    )
    args = parser.parse_args()
    _load_dotenv(REPO_ROOT / ".env")

    work_root = args.work_root.resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    report_path = work_root / "report.jsonl"

    pdfs = _all_avip_pdfs()
    if args.only:
        allowed = set(args.only)
        pdfs = tuple(pdf for pdf in pdfs if pdf.stem in allowed)

    print(f"Converting {len(pdfs)} AVIP PDFs with model={args.model}")
    start_all = time.monotonic()

    for index, pdf in enumerate(pdfs, start=1):
        final_output = _final_output_dir(pdf)
        page_count = pdf_page_count(pdf)
        print(f"[{index}/{len(pdfs)}] {pdf} ({page_count} pages)")
        started = time.monotonic()
        status = "ok"
        error = None
        try:
            promoted = _chunked_convert(
                pdf,
                final_output,
                work_root=work_root,
                model=args.model,
                timeout_s=args.timeout_s,
                allow_page_chunks=args.allow_page_chunks,
                chunk_threshold=args.chunk_threshold,
                pages_per_chunk=args.pages_per_chunk,
            )
            print(f"  promoted -> {promoted}")
        except Exception as exc:  # pragma: no cover - operational path
            status = "error"
            error = str(exc)
            print(f"  ERROR: {exc}")

        record = {
            "pdf": str(pdf),
            "pages": page_count,
            "status": status,
            "error": error,
            "elapsed_s": round(time.monotonic() - started, 1),
        }
        with report_path.open("a") as handle:
            handle.write(json.dumps(record) + "\n")

        if status != "ok":
            return 1

    print(f"Done in {round(time.monotonic() - start_all, 1)}s")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
