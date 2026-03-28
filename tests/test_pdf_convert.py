import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from PIL import Image

from rtl_training.opencode_runtime import OpenCodeRunResult
from rtl_training.runtime import DEFAULT_CONVERTER_PROMPT
from rtl_training.runtime import prepare_converter_episode
from rtl_training.pdf_convert import (
    _assert_all_rendered_pages_read,
    _assert_no_full_page_figure_copies,
    _missing_read_page_numbers,
    _suspicious_full_page_figures,
    _terminate_process_tree,
    combine_chunk_output_dirs,
    convert_pdf_to_spec_dir,
    plan_pdf_page_ranges,
)


ROOT = Path(__file__).resolve().parents[1]


def test_prepare_converter_episode_stages_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "datasheet.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    episode = prepare_converter_episode(
        pdf,
        tmp_path / "converter_ws",
        template_root=ROOT,
    )

    assert episode.pdf_path == pdf.resolve()
    assert episode.request.agent == "converter"
    assert episode.workspace.pdf_path.read_bytes() == b"%PDF-1.4 fake"
    assert episode.workspace.pages_dir.is_dir()
    assert episode.workspace.output_dir.is_dir()
    assert (episode.workspace.root / "TASK.md").exists()
    assert (episode.workspace.root / "opencode.json").exists()
    staged_config = (episode.workspace.root / "opencode.json").read_text()
    assert '"converter"' in staged_config
    instructions = (episode.workspace.root / "TASK.md").read_text()
    assert "input/pages/" in instructions
    assert "read` tool on every `input/pages/page-*.png`" in instructions
    assert "output/figures/" in instructions
    assert "![Figure" in instructions
    assert "01_overview.md" in instructions
    assert "Be exhaustive" in instructions


def test_converter_prompt_documents_figure_contract() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "converter.md").read_text()
    assert "input/pages/" in prompt
    assert "Use the `read` tool on every `input/pages/page-*.png`" in prompt
    assert "output/figures/" in prompt
    assert "![Figure" in prompt
    assert "PIL" in prompt
    assert "x1, y1, x2, y2" in prompt
    assert "page by page" in prompt
    assert "01_overview.md" in prompt
    assert "Exhaustiveness is mandatory" in prompt
    assert "Do not copy a full rendered page into `output/figures/`" in prompt
    assert "Read TASK.md" in DEFAULT_CONVERTER_PROMPT
    assert "Use the read tool on each page image at least once" in DEFAULT_CONVERTER_PROMPT


def test_convert_pdf_to_spec_dir_copies_agent_output(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    output_dir = tmp_path / "spec_out"

    def fake_render(pdf_path, pages_dir, *, dpi=300):
        del pdf_path, dpi
        page = pages_dir / "page-1.png"
        Image.new("RGB", (100, 200), "white").save(page)
        return (page,)

    def fake_run_opencode(request, *, output_dir, pages_dir, timeout_s):
        del pages_dir, timeout_s
        out = request.workspace_root / "output"
        (out / "spec.md").write_text("# My Spec\n\nConverted content.")
        (out / "manifest.json").write_text(json.dumps({"files": ["spec.md"], "page_count": 1}))
        log_dir = request.workspace_root / ".xdg_data" / "opencode" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        page_path = request.workspace_root / "input" / "pages" / "page-1.png"
        (log_dir / "run.log").write_text(
            f"INFO service=permission permission=read pattern={page_path}\n"
        )
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr("rtl_training.pdf_convert._render_pdf_page_images", fake_render)
    monkeypatch.setattr("rtl_training.pdf_convert.run_converter_opencode", fake_run_opencode)

    result = convert_pdf_to_spec_dir(
        pdf,
        output_dir,
        template_root=ROOT,
    )

    assert result == output_dir.resolve()
    assert (output_dir / "spec.md").read_text() == "# My Spec\n\nConverted content."
    assert (output_dir / "manifest.json").exists()


def test_convert_pdf_to_spec_dir_raises_on_agent_failure(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    def fake_render(pdf_path, pages_dir, *, dpi=300):
        del pdf_path, dpi
        page = pages_dir / "page-1.png"
        Image.new("RGB", (100, 200), "white").save(page)
        return (page,)

    def fake_run_opencode(request, *, output_dir, pages_dir, timeout_s):
        del request, output_dir, pages_dir, timeout_s
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=1,
            stdout="",
            stderr="agent crashed",
        )

    monkeypatch.setattr("rtl_training.pdf_convert._render_pdf_page_images", fake_render)
    monkeypatch.setattr("rtl_training.pdf_convert.run_converter_opencode", fake_run_opencode)

    with pytest.raises(RuntimeError, match="converter agent failed"):
        convert_pdf_to_spec_dir(pdf, tmp_path / "out", template_root=ROOT)


def test_convert_pdf_to_spec_dir_rejects_success_without_markdown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    def fake_render(pdf_path, pages_dir, *, dpi=300):
        del pdf_path, dpi
        page = pages_dir / "page-1.png"
        Image.new("RGB", (100, 200), "white").save(page)
        return (page,)

    def fake_run_opencode(request, *, output_dir, pages_dir, timeout_s):
        del request, output_dir, pages_dir, timeout_s
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=0,
            stdout="ok",
            stderr="no files written",
        )

    monkeypatch.setattr("rtl_training.pdf_convert._render_pdf_page_images", fake_render)
    monkeypatch.setattr("rtl_training.pdf_convert.run_converter_opencode", fake_run_opencode)

    with pytest.raises(RuntimeError, match="without producing any markdown output"):
        convert_pdf_to_spec_dir(pdf, tmp_path / "out", template_root=ROOT)


def test_convert_pdf_to_spec_dir_salvages_existing_markdown_after_agent_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf = tmp_path / "spec.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    output_dir = tmp_path / "spec_out"

    def fake_render(pdf_path, pages_dir, *, dpi=300):
        del pdf_path, dpi
        page = pages_dir / "page-1.png"
        Image.new("RGB", (100, 200), "white").save(page)
        return (page,)

    def fake_run_opencode(request, *, output_dir, pages_dir, timeout_s):
        del pages_dir, timeout_s
        out = request.workspace_root / "output"
        (out / "spec.md").write_text("# Salvaged\n\nConverted content.")
        (out / "manifest.json").write_text(json.dumps({"files": ["spec.md"], "page_count": 1}))
        log_dir = request.workspace_root / ".xdg_data" / "opencode" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        page_path = request.workspace_root / "input" / "pages" / "page-1.png"
        (log_dir / "run.log").write_text(
            f"INFO service=permission permission=read pattern={page_path}\n"
        )
        return OpenCodeRunResult(
            command=("opencode",),
            returncode=1,
            stdout="partial",
            stderr="wrapper failed after writing output",
        )

    monkeypatch.setattr("rtl_training.pdf_convert._render_pdf_page_images", fake_render)
    monkeypatch.setattr("rtl_training.pdf_convert.run_converter_opencode", fake_run_opencode)

    result = convert_pdf_to_spec_dir(
        pdf,
        output_dir,
        template_root=ROOT,
    )

    assert result == output_dir.resolve()
    assert (output_dir / "spec.md").read_text() == "# Salvaged\n\nConverted content."
    assert json.loads((output_dir / "manifest.json").read_text())["files"] == ["spec.md"]


def test_missing_read_page_numbers_uses_workspace_logs(tmp_path: Path) -> None:
    pages_dir = tmp_path / "input" / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "page-1.png").write_bytes(b"png")
    (pages_dir / "page-2.png").write_bytes(b"png")

    log_dir = tmp_path / ".xdg_data" / "opencode" / "log"
    log_dir.mkdir(parents=True)
    (log_dir / "run.log").write_text(
        f"INFO service=permission permission=read pattern={pages_dir / 'page-1.png'}\n"
    )

    assert _missing_read_page_numbers(workspace_root=tmp_path, pages_dir=pages_dir) == (2,)


def test_assert_all_rendered_pages_read_rejects_missing_pages(tmp_path: Path) -> None:
    pages_dir = tmp_path / "input" / "pages"
    pages_dir.mkdir(parents=True)
    (pages_dir / "page-1.png").write_bytes(b"png")
    (pages_dir / "page-2.png").write_bytes(b"png")

    log_dir = tmp_path / ".xdg_data" / "opencode" / "log"
    log_dir.mkdir(parents=True)
    (log_dir / "run.log").write_text(
        f"INFO service=permission permission=read pattern={pages_dir / 'page-1.png'}\n"
    )

    with pytest.raises(RuntimeError, match="missing pages: 2"):
        _assert_all_rendered_pages_read(workspace_root=tmp_path, pages_dir=pages_dir)


def test_suspicious_full_page_figures_flags_page_sized_copies(tmp_path: Path) -> None:
    pages_dir = tmp_path / "input" / "pages"
    pages_dir.mkdir(parents=True)
    page = pages_dir / "page-1.png"
    Image.new("RGB", (100, 200), "white").save(page)

    output_dir = tmp_path / "output"
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True)
    full_page = figures_dir / "figure-001.png"
    small_crop = figures_dir / "figure-002.png"
    Image.new("RGB", (100, 200), "white").save(full_page)
    Image.new("RGB", (60, 80), "white").save(small_crop)

    suspicious = _suspicious_full_page_figures(output_dir=output_dir, pages_dir=pages_dir)

    assert suspicious == ("figures/figure-001.png",)


def test_assert_no_full_page_figure_copies_rejects_page_sized_assets(tmp_path: Path) -> None:
    pages_dir = tmp_path / "input" / "pages"
    pages_dir.mkdir(parents=True)
    output_dir = tmp_path / "output"
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True)
    Image.new("RGB", (120, 240), "white").save(pages_dir / "page-1.png")
    Image.new("RGB", (120, 240), "white").save(figures_dir / "figure-001.png")

    with pytest.raises(RuntimeError, match="full-page copies"):
        _assert_no_full_page_figure_copies(output_dir=output_dir, pages_dir=pages_dir)


def test_terminate_process_tree_kills_child_holding_stdio(tmp_path: Path) -> None:
    script = tmp_path / "spawn_child.py"
    child_pid_path = tmp_path / "child.pid"
    script.write_text(
        """
import signal
import subprocess
import sys
import time
from pathlib import Path

child_pid_path = Path(sys.argv[1])
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
child_pid_path.write_text(str(child.pid))
signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
print("ready", flush=True)
while True:
    time.sleep(1)
"""
    )

    process = subprocess.Popen(
        (sys.executable, str(script), str(child_pid_path)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    deadline = time.monotonic() + 5
    while not child_pid_path.exists():
        if time.monotonic() >= deadline:
            raise AssertionError("child pid file was not created")
        time.sleep(0.05)
    child_pid = int(child_pid_path.read_text())

    stdout, stderr = _terminate_process_tree(process, grace_s=1)

    assert "ready" in stdout
    assert stderr == ""
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


def test_plan_pdf_page_ranges_chunks_long_documents() -> None:
    assert plan_pdf_page_ranges(1, 50) == ((1, 1),)
    assert plan_pdf_page_ranges(50, 50) == ((1, 50),)
    assert plan_pdf_page_ranges(120, 50) == ((1, 50), (51, 100), (101, 120))


def test_plan_pdf_page_ranges_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="page_count"):
        plan_pdf_page_ranges(0, 50)
    with pytest.raises(ValueError, match="pages_per_chunk"):
        plan_pdf_page_ranges(10, 0)


def test_combine_chunk_output_dirs_builds_top_level_manifest(tmp_path: Path) -> None:
    chunk1 = tmp_path / "chunk1"
    chunk1.mkdir()
    (chunk1 / "spec.md").write_text("# Chunk 1")
    (chunk1 / "manifest.json").write_text(
        json.dumps({"files": ["spec.md"], "page_count": 3})
    )

    chunk2 = tmp_path / "chunk2"
    chunk2.mkdir()
    (chunk2 / "sub.md").write_text("# Chunk 2")
    (chunk2 / "manifest.json").write_text(
        json.dumps({"files": ["sub.md"], "page_count": 2})
    )

    combined = combine_chunk_output_dirs((chunk1, chunk2), tmp_path / "combined")

    manifest = json.loads((combined / "manifest.json").read_text())
    assert manifest["files"] == ["chunk_001/spec.md", "chunk_002/sub.md"]
    assert manifest["page_count"] == 5
