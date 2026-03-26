from pathlib import Path
import stat

from rtl_training.runtime import prepare_generator_episode, prepare_verifier_episode
from rtl_training.task_store import store_rtllm_tasks
from rtl_training.workspace import collect_candidate_files


ROOT = Path(__file__).resolve().parents[1]


def _create_task(tmp_path: Path) -> Path:
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Arithmetic" / "Adder" / "adder_8bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("8-bit adder")
    (task_dir / "verified_adder_8bit.v").write_text("module verified_adder_8bit; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")
    written = store_rtllm_tasks(source_root, tmp_path / "task_store", dataset_name="rtllm_v2_0")
    return written[0]


def test_prepare_generator_episode_points_opencode_at_staged_workspace(tmp_path: Path) -> None:
    task_root = _create_task(tmp_path)

    episode = prepare_generator_episode(
        task_root,
        tmp_path / "episode",
        template_root=ROOT,
    )

    assert episode.request.workspace_root == episode.workspace.root
    assert episode.request.agent == "generator"
    assert episode.workspace.submission_dir == episode.workspace.root / "submission"


def test_prepare_generator_episode_instructions_require_behavioral_spec_and_build_check(tmp_path: Path) -> None:
    task_root = _create_task(tmp_path)

    episode = prepare_generator_episode(
        task_root,
        tmp_path / "episode",
        template_root=ROOT,
    )

    instructions = episode.workspace.instructions_path.read_text()
    assert "task/spec/doc/" in instructions
    assert "requirement checklist" in instructions
    assert "Interface and compatibility are necessary but not sufficient" in instructions
    assert "compile sanity check" in instructions
    assert "required compile/elaboration check is `xrun`/Xcelium" in instructions
    assert "`yosys` does not satisfy" in instructions
    assert "`yosys` only as a fallback" in instructions
    assert "task-local SV packages or typedef files" in instructions
    assert "`submission/` must be a self-contained deliverable set" in instructions
    assert "Do not use `` `include `` paths that reach into `task/`" in instructions
    assert "compile check only counts if it elaborates the DUT top module" in instructions
    assert "helper interface or package alone does not count" in instructions


def test_prepare_verifier_episode_stages_candidate_dir(tmp_path: Path) -> None:
    task_root = _create_task(tmp_path)
    candidate_dir = tmp_path / "submission"
    candidate_dir.mkdir()
    (candidate_dir / "candidate.sv").write_text("module adder_8bit; endmodule\n")

    episode = prepare_verifier_episode(
        task_root,
        candidate_dir,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    assert episode.request.agent == "verifier"
    assert episode.workspace.candidate_input_dir is not None
    staged_files = collect_candidate_files(episode.workspace.candidate_input_dir)
    assert len(staged_files) == 1
    assert staged_files[0].read_text() == "module adder_8bit; endmodule\n"
    mode = stat.S_IMODE(staged_files[0].stat().st_mode)
    assert mode & stat.S_IWUSR == 0


def test_prepare_verifier_episode_instructions_call_for_native_sva_and_uvm(tmp_path: Path) -> None:
    task_root = _create_task(tmp_path)
    candidate_dir = tmp_path / "submission"
    candidate_dir.mkdir()
    (candidate_dir / "candidate.sv").write_text("module adder_8bit; endmodule\n")

    episode = prepare_verifier_episode(
        task_root,
        candidate_dir,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    instructions = episode.workspace.instructions_path.read_text()
    assert "native SVAs" in instructions
    assert "cocotb" in instructions
    assert "`xrun`" in instructions
    assert "`xrun -uvm`" in instructions


def test_verifier_prompt_mentions_xrun_sva_and_uvm() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "verifier.md").read_text()
    assert "native SystemVerilog/UVM execution under `xrun`" in prompt
    assert "Cocotb is also allowed" in prompt
    assert "@cocotb.test()" in prompt
    assert "For plain SystemVerilog and SVA simulation, prefer `xrun`" in prompt
    assert "For UVM environments that import `uvm_pkg`, prefer:" in prompt


def test_generator_prompt_mentions_behavioral_spec_and_compile_sanity() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "generator.md").read_text()
    assert "task/spec/doc/" in prompt
    assert "full functional behavior" in prompt
    assert "Interface and compatibility are necessary but not sufficient" in prompt
    assert "requirement checklist" in prompt
    assert "compile sanity check" in prompt
    assert "required compile sanity check is `xrun`/Xcelium" in prompt
    assert "`yosys` does not satisfy this requirement" in prompt
    assert "Do not rely on upstream/OpenTitan package imports" in prompt
    assert "task-local SV packages or typedef files" in prompt
    assert "`yosys` only as a fallback" in prompt
    assert "`submission/` as a self-contained deliverable set" in prompt
    assert "Do not `include` files from `task/` inside submission RTL" in prompt
    assert "compile check only counts if it elaborates the DUT top module" in prompt
    assert "If the compile check fails, `status` must not be `pass`" in prompt
