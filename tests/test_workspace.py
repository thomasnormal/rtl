import json
from pathlib import Path

from rtl_training.task_store import load_stored_task, store_rtllm_tasks
from rtl_training.workspace import stage_generator_workspace, stage_verifier_workspace


ROOT = Path(__file__).resolve().parents[1]


def _create_stored_task(tmp_path: Path):
    source_root = tmp_path / "RTLLM"
    task_dir = source_root / "Arithmetic" / "Adder" / "adder_8bit"
    task_dir.mkdir(parents=True)
    (task_dir / "design_description.txt").write_text("8-bit adder")
    (task_dir / "verified_adder_8bit.v").write_text("module verified_adder_8bit; endmodule\n")
    (task_dir / "testbench.v").write_text("module testbench; endmodule\n")
    written = store_rtllm_tasks(source_root, tmp_path / "task_store", dataset_name="rtllm_v2_0")
    return load_stored_task(written[0])


def test_stage_generator_workspace_exposes_only_public_task_material(tmp_path: Path) -> None:
    task = _create_stored_task(tmp_path)

    workspace = stage_generator_workspace(
        task,
        tmp_path / "episode",
        template_root=ROOT,
    )

    assert workspace.spec_path.read_text() == "8-bit adder"
    assert workspace.public_task_path.exists()
    assert workspace.candidate_output_path == workspace.root / "submission" / "candidate.sv"
    assert workspace.result_path == workspace.root / "result" / "result.json"
    assert not (workspace.root / "oracle").exists()
    assert (workspace.root / ".opencode" / "skills" / "xrun" / "SKILL.md").exists()
    assert (workspace.root / "AGENTS.md").exists()
    assert "There is no oracle validator" in workspace.instructions_path.read_text()
    assert "authoritative public contract" in workspace.instructions_path.read_text()

    config = json.loads((workspace.root / "opencode.json").read_text())
    assert config["permission"]["*"] == "allow"
    assert config["permission"]["external_directory"] == "deny"


def test_stage_verifier_workspace_copies_candidate_but_not_oracle(tmp_path: Path) -> None:
    task = _create_stored_task(tmp_path)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module adder_8bit; endmodule\n")

    workspace = stage_verifier_workspace(
        task,
        candidate,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    assert workspace.candidate_input_path is not None
    assert workspace.candidate_input_path.read_text() == "module adder_8bit; endmodule\n"
    assert workspace.candidate_output_path is None
    assert not (workspace.root / "oracle").exists()
    assert "authoritative public contract" in workspace.instructions_path.read_text()
