import json
from pathlib import Path
import stat

from rtl_training.runtime import (
    prepare_generator_episode,
    prepare_verifier_episode,
    validate_generator_episode,
)
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


def _create_minimal_opentitan_task(tmp_path: Path) -> Path:
    task_root = tmp_path / "task_store" / "opentitan" / "rv_timer"
    (task_root / "public" / "spec").mkdir(parents=True)
    (task_root / "public" / "spec" / "README.md").write_text("rv_timer spec\n")
    (task_root / "public" / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan",
                "task_id": "rv_timer",
                "top_module": "rv_timer",
                "deliverables": {
                    "rtl": "submission/",
                    "summary": "result/result.json",
                },
            },
            indent=2,
        )
        + "\n"
    )
    (task_root / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan",
                "task_id": "rv_timer",
                "public": {
                    "directory": "public",
                    "spec": "public/spec/",
                    "task": "public/task.json",
                },
                "oracle": {
                    "kind": "opentitan_dvsim",
                    "cfg": "hw/ip/rv_timer/dv/rv_timer_sim_cfg.hjson",
                    "test": "rv_timer_random",
                    "tool": "xcelium",
                    "golden_rtl_dir": "golden_rtl",
                    "overlay_rel_dir": "hw/ip/rv_timer/rtl",
                },
            },
            indent=2,
        )
        + "\n"
    )
    return task_root


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
    assert episode.request.timeout_closeout_prompt is not None
    assert "Time budget is exhausted" in episode.request.timeout_closeout_prompt


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
    assert "Interface and microarchitecture are necessary but not sufficient" in instructions
    assert "task/spec/doc/registers.md" in instructions
    assert "task/spec/doc/programmers_guide.md" in instructions
    assert "compile sanity check" in instructions
    assert "Use `xrun`/Xcelium for that check" in instructions
    assert "self-checking" in instructions
    assert "result/evidence/" in instructions
    assert "waveform" in instructions
    assert "`vcdcat`" in instructions
    assert "documented CSR/register map" in instructions
    assert "write-only registers" in instructions
    assert "task-local SV packages or typedef files" in instructions
    assert "generated bus helper package" in instructions
    assert "source, size, param, and user fields" in instructions
    assert "task/spec/micro_arch/README.md" in instructions
    assert "exported microarchitecture signal" in instructions
    assert "Do not infer a signal's meaning from its name alone" in instructions
    assert "masking, gating, latching, or pulse generation" in instructions
    assert "forces those values to differ" in instructions
    assert "zero-argument helper functions" in instructions
    assert "Use `always_comb`" in instructions
    assert "actual request-valid handshake" in instructions
    assert "raw address decode alone" in instructions
    assert "complete public problem statement" in instructions
    assert "Do not assume access to upstream repo code" in instructions
    assert "task/task.json" in instructions
    assert "field `top_module`" in instructions
    assert "`submission/` must be a self-contained deliverable set" in instructions
    assert "Do not use `` `include `` paths that reach into `task/`" in instructions
    assert "compile check only counts if it elaborates the DUT top module" in instructions
    assert "If `vcdcat` is unavailable or broken" in instructions
    assert "fall back to another simulator" in instructions
    assert "every high-risk requirement and every exported microarchitecture signal" in instructions
    assert "Do not silently redefine the meaning of a public microarchitecture signal" in instructions
    assert "helper interface or package alone does not count" in instructions
    assert "As soon as `result/result.json` is written" in instructions
    assert "stop the run" in instructions
    assert "Do not spend extra steps on optional cleanup" in instructions
    assert "Write `result/result.json` early" in instructions
    assert "update it later" in instructions
    assert "If you are past roughly 60% of your step budget" in instructions
    assert "Immediately after the first requirement pass" in instructions
    assert "update the existing `result/result.json` stub" in instructions


def test_validate_generator_episode_dispatches_opentitan_oracle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    task_root = _create_minimal_opentitan_task(tmp_path)
    episode = prepare_generator_episode(
        task_root,
        tmp_path / "episode",
        template_root=ROOT,
    )
    candidate_path = episode.workspace.submission_dir / "rv_timer.sv"
    candidate_path.write_text("module rv_timer; endmodule\n")

    calls: list[tuple[Path, Path, int]] = []

    def fake_validate_opentitan_candidate(task, *, candidate_dir, work_root, timeout_s):
        calls.append((Path(candidate_dir), Path(work_root), timeout_s))
        return type(
            "FakeOpenTitanResult",
            (),
            {
                "passed": True,
                "plan": type("FakePlan", (), {"log_path": Path(work_root) / "dvsim.log"})(),
            },
        )()

    monkeypatch.setattr(
        "rtl_training.runtime.validate_opentitan_candidate",
        fake_validate_opentitan_candidate,
    )

    result = validate_generator_episode(
        episode,
        work_root=tmp_path / "oracle_work",
        preferred_simulator="xrun",
        timeout_s=123,
    )

    assert result.passed is True
    assert calls == [
        (
            episode.workspace.submission_dir,
            (tmp_path / "oracle_work").resolve(),
            123,
        )
    ]


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
    assert "After changing DUT inputs in a bench" in instructions
    assert "delta cycle" in instructions
    assert "edge-triggered register updates" in instructions
    assert "separate read transaction for readback" in instructions
    assert "generated bus helper package" in instructions
    assert "source, size, param, and user" in instructions
    assert "complete public problem statement" in instructions
    assert "Do not assume access to upstream repo code" in instructions
    assert "task/task.json" in instructions
    assert "field `top_module`" in instructions
    assert "As soon as `result/result.json` is written" in instructions
    assert "stop the run" in instructions
    assert "concrete critical spec violation" in instructions
    assert "sufficient evidence for `verdict: bad`" in instructions
    assert episode.request.timeout_closeout_prompt is not None
    assert "Time budget is exhausted" in episode.request.timeout_closeout_prompt
    assert "timeout_closeout_pass1_stdout.log" in episode.request.timeout_closeout_prompt


def test_verifier_prompt_mentions_xrun_sva_and_uvm() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "verifier.md").read_text()
    assert "native SystemVerilog/UVM execution under `xrun`" in prompt
    assert "Cocotb is also allowed" in prompt
    assert "@cocotb.test()" in prompt
    assert "For plain SystemVerilog and SVA simulation, prefer `xrun`" in prompt
    assert "For UVM environments that import `uvm_pkg`, prefer:" in prompt
    assert "After changing DUT inputs in a bench" in prompt
    assert "delta cycle" in prompt
    assert "edge-triggered register updates" in prompt
    assert "separate read transaction for readback" in prompt
    assert "generated bus helper package" in prompt
    assert "source / size / param / user fields" in prompt
    assert "complete public problem statement" in prompt
    assert "Do not assume access to upstream repo code" in prompt


def test_generator_prompt_mentions_behavioral_spec_and_compile_sanity() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "generator.md").read_text()
    assert "task/task.json" in prompt
    assert "field `top_module`" in prompt
    assert "task/spec/doc/" in prompt
    assert "full functional behavior" in prompt
    assert "Interface and microarchitecture are necessary but not sufficient" in prompt
    assert "requirement checklist" in prompt
    assert "task/spec/doc/registers.md" in prompt
    assert "task/spec/doc/programmers_guide.md" in prompt
    assert "compile sanity check" in prompt
    assert "Use `xrun`/Xcelium for this check" in prompt
    assert "self-checking" in prompt
    assert "result/evidence/" in prompt
    assert "waveform" in prompt
    assert "`vcdcat`" in prompt
    assert "documented CSR/register map" in prompt
    assert "write-only registers" in prompt
    assert "Do not rely on upstream/OpenTitan package imports" in prompt
    assert "task-local SV packages or typedef files" in prompt
    assert "generated bus helper package" in prompt
    assert "source, size, param, and user fields" in prompt
    assert "task/spec/micro_arch/README.md" in prompt
    assert "exported microarchitecture signal" in prompt
    assert "Do not infer a signal's meaning from its name alone" in prompt
    assert "masking, gating, latching, or pulse generation" in prompt
    assert "forces those values to differ" in prompt
    assert "zero-argument helper functions" in prompt
    assert "Use `always_comb`" in prompt
    assert "actual request-valid handshake" in prompt
    assert "raw address decode alone" in prompt
    assert "complete public problem statement" in prompt
    assert "Do not assume access to upstream repo code" in prompt
    assert "Use `xrun`/Xcelium for compile and elaboration checks" in prompt
    assert "`submission/` as a self-contained deliverable set" in prompt
    assert "Do not `include` files from `task/` inside submission RTL" in prompt
    assert "compile check only counts if it elaborates the DUT top module" in prompt
    assert "If the compile check fails, `status` must not be `pass`" in prompt
    assert "If `vcdcat` is unavailable or broken" in prompt
    assert "fall back to another simulator" in prompt
    assert "every high-risk requirement and every exported microarchitecture signal" in prompt
    assert "As soon as `result/result.json` is written" in prompt
    assert "stop the run" in prompt
    assert "Do not spend extra steps on optional cleanup" in prompt
    assert "Write `result/result.json` EARLY" in prompt
    assert "update it later" in prompt
    assert "If you are past roughly 60% of your step budget" in prompt
    assert "existing `result/result.json` stub" in prompt
    assert "Immediately after the first requirement pass" in prompt


def test_verifier_prompt_requires_immediate_stop_after_result_bundle() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "verifier.md").read_text()
    assert "As soon as `result/result.json` is written" in prompt
    assert "stop the run" in prompt
    assert "existing `result/result.json` stub" in prompt
    assert "concrete spec violation" in prompt
    assert "sufficient evidence for `verdict: bad`" in prompt


def test_verifier_prompt_forbids_yosys() -> None:
    prompt = (ROOT / ".opencode" / "prompts" / "verifier.md").read_text()
    assert "task/task.json" in prompt
    assert "field `top_module`" in prompt
    assert "Do not use `yosys`" in prompt or "`yosys`" not in prompt
