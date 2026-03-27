import json
from pathlib import Path

from rtl_training.task_store import load_stored_task, store_rtllm_tasks
from rtl_training.workspace import collect_candidate_files, stage_generator_workspace, stage_verifier_workspace


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

    assert (workspace.spec_dir / "spec.txt").read_text() == "8-bit adder"
    assert workspace.public_top_module_path.read_text().strip() == "adder_8bit"
    assert workspace.public_task_path.exists()
    assert workspace.submission_dir == workspace.root / "submission"
    assert workspace.result_path == workspace.root / "result" / "result.json"
    assert not (workspace.root / "oracle").exists()
    assert (workspace.root / ".opencode" / "skills" / "xrun" / "SKILL.md").exists()
    assert (workspace.root / "AGENTS.md").exists()
    instructions = workspace.instructions_path.read_text()
    assert "There is no oracle validator" in instructions
    assert "task/top_module.txt" in instructions
    assert "machine-readable metadata" in instructions
    assert "task/spec/interface/" in instructions
    assert "task/spec/doc/" in instructions
    assert "requirement checklist" in instructions
    assert "Interface and microarchitecture are necessary but not sufficient" in instructions
    assert "Use `xrun`/Xcelium for that check" in instructions
    assert "Do not depend on upstream or OpenTitan repository packages" in instructions
    assert "task-local SV packages or typedef files" in instructions
    assert "generated bus helper package" in instructions
    assert "source, size, param, and user fields" in instructions
    assert "complete public problem statement" in instructions
    assert "Do not assume access to upstream repo code" in instructions
    assert "`submission/` must be a self-contained deliverable set" in instructions
    assert "Do not use `` `include `` paths that reach into `task/`" in instructions
    assert "compile check only counts if it elaborates the DUT top module" in instructions

    config = json.loads((workspace.root / "opencode.json").read_text())
    assert config["permission"]["*"] == "allow"
    assert config["permission"]["external_directory"] == "deny"


def test_stage_verifier_workspace_copies_candidate_dir_but_not_oracle(tmp_path: Path) -> None:
    task = _create_stored_task(tmp_path)
    candidate_dir = tmp_path / "submission"
    candidate_dir.mkdir()
    (candidate_dir / "top.sv").write_text("module adder_8bit; endmodule\n")
    (candidate_dir / "helpers.sv").write_text("module helpers; endmodule\n")

    workspace = stage_verifier_workspace(
        task,
        candidate_dir,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    assert workspace.candidate_input_dir is not None
    staged_files = collect_candidate_files(workspace.candidate_input_dir)
    assert len(staged_files) == 2
    assert (workspace.candidate_input_dir / "top.sv").read_text() == "module adder_8bit; endmodule\n"
    assert not (workspace.root / "oracle").exists()
    instructions = workspace.instructions_path.read_text()
    assert "task/top_module.txt" in instructions
    assert "machine-readable public metadata" in instructions
    assert "task/spec/interface/" in instructions
    assert "cocotb" in instructions
    assert "Do not use `yosys`" in instructions
    assert "generated bus helper package" in instructions
    assert "complete public problem statement" in instructions
    assert "Do not assume access to upstream repo code" in instructions


def test_stage_verifier_workspace_accepts_single_file(tmp_path: Path) -> None:
    task = _create_stored_task(tmp_path)
    candidate = tmp_path / "candidate.sv"
    candidate.write_text("module adder_8bit; endmodule\n")

    workspace = stage_verifier_workspace(
        task,
        candidate,
        tmp_path / "verifier_episode",
        template_root=ROOT,
    )

    assert workspace.candidate_input_dir is not None
    staged_files = collect_candidate_files(workspace.candidate_input_dir)
    assert len(staged_files) == 1
    assert staged_files[0].read_text() == "module adder_8bit; endmodule\n"


def test_collect_candidate_files_finds_rtl_extensions(tmp_path: Path) -> None:
    (tmp_path / "top.sv").write_text("module top; endmodule\n")
    (tmp_path / "helpers.v").write_text("module helpers; endmodule\n")
    (tmp_path / "defs.svh").write_text("`define FOO 1\n")
    (tmp_path / "readme.txt").write_text("not rtl\n")

    files = collect_candidate_files(tmp_path)

    assert [f.name for f in files] == ["defs.svh", "helpers.v", "top.sv"]
