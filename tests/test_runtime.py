from pathlib import Path
import stat

from rtl_training.runtime import prepare_generator_episode, prepare_verifier_episode
from rtl_training.task_store import store_rtllm_tasks


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
    assert episode.workspace.candidate_output_path == episode.workspace.root / "submission" / "candidate.sv"


def test_prepare_verifier_episode_stages_candidate_separately(tmp_path: Path) -> None:
    task_root = _create_task(tmp_path)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module adder_8bit; endmodule\n")

    episode = prepare_verifier_episode(
        task_root,
        candidate,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    assert episode.request.agent == "verifier"
    assert episode.workspace.candidate_input_path is not None
    assert episode.workspace.candidate_input_path.read_text() == "module adder_8bit; endmodule\n"
    mode = stat.S_IMODE(episode.workspace.candidate_input_path.stat().st_mode)
    assert mode & stat.S_IWUSR == 0


def test_prepare_verifier_episode_instructions_call_for_native_sva_and_uvm(tmp_path: Path) -> None:
    task_root = _create_task(tmp_path)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module adder_8bit; endmodule\n")

    episode = prepare_verifier_episode(
        task_root,
        candidate,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    instructions = episode.workspace.instructions_path.read_text()
    assert "native SVAs" in instructions
    assert "`xrun`" in instructions
    assert "`xrun -uvm`" in instructions


def test_verifier_prompt_mentions_xrun_sva_and_uvm() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "verifier.md").read_text()
    assert "native SystemVerilog/UVM execution under `xrun`" in prompt
    assert "For plain SystemVerilog and SVA simulation, prefer `xrun`" in prompt
    assert "For UVM environments that import `uvm_pkg`, prefer:" in prompt
