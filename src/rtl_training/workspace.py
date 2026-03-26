from __future__ import annotations

from dataclasses import dataclass
import stat
from pathlib import Path
import shutil

from .task_store import StoredTask


@dataclass(frozen=True)
class StagedWorkspace:
    root: Path
    agent_name: str
    task_dir: Path
    spec_path: Path
    public_task_path: Path
    submission_dir: Path
    candidate_output_path: Path | None
    candidate_input_path: Path | None
    result_dir: Path
    result_path: Path
    instructions_path: Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def stage_generator_workspace(
    task: StoredTask,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
) -> StagedWorkspace:
    workspace = _stage_public_workspace(
        task,
        workspace_root,
        agent_name="generator",
        template_root=template_root,
    )
    task_note = "\n".join(
        [
            "# Generator Task",
            "",
            "- Read `task/spec.txt` and `task/task.json`.",
            "- Treat `task/task.json` as the authoritative public contract for the top module, interface hints, and deliverables.",
            "- Ensure `submission/candidate.sv` defines the top module named by `task/task.json`.",
            "- Write the candidate RTL to `submission/candidate.sv`.",
            "- Write a machine-readable summary to `result/result.json`.",
            "- There is no oracle validator in this workspace.",
        ]
    )
    workspace.instructions_path.write_text(task_note + "\n")
    return StagedWorkspace(
        root=workspace.root,
        agent_name=workspace.agent_name,
        task_dir=workspace.task_dir,
        spec_path=workspace.spec_path,
        public_task_path=workspace.public_task_path,
        submission_dir=workspace.submission_dir,
        candidate_output_path=workspace.submission_dir / "candidate.sv",
        candidate_input_path=None,
        result_dir=workspace.result_dir,
        result_path=workspace.result_path,
        instructions_path=workspace.instructions_path,
    )


def stage_verifier_workspace(
    task: StoredTask,
    candidate_rtl_path: str | Path,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
) -> StagedWorkspace:
    workspace = _stage_public_workspace(
        task,
        workspace_root,
        agent_name="verifier",
        template_root=template_root,
    )
    candidate_dir = workspace.root / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    candidate_input = candidate_dir / Path(candidate_rtl_path).name
    shutil.copy2(candidate_rtl_path, candidate_input)
    candidate_input.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    task_note = "\n".join(
        [
            "# Verifier Task",
            "",
            "- Read `task/spec.txt`, `task/task.json`, and `candidate/current.sv`.",
            "- Treat `task/task.json` as the authoritative public contract for the expected top module and interface hints.",
            "- Treat the candidate RTL as immutable input. Do not edit files under `candidate/`.",
            "- Turn the spec into a concrete requirement checklist before judging the RTL.",
            "- Use the available tools to gather evidence.",
            "- Do not stop at code inspection. Write executable checks: prefer native SVAs, bind files, and self-checking SystemVerilog benches under `xrun`, and escalate to native UVM under `xrun -uvm` when the protocol is non-trivial.",
            "- Save the requirement checklist and the generated verification artifacts under `result/evidence/`.",
            "- Write the final verdict bundle to `result/result.json`.",
            "- Put larger evidence artifacts under `result/evidence/`.",
            "- There is no hidden oracle in this workspace.",
        ]
    )
    workspace.instructions_path.write_text(task_note.replace("candidate/current.sv", str(candidate_input.relative_to(workspace.root))) + "\n")
    return StagedWorkspace(
        root=workspace.root,
        agent_name=workspace.agent_name,
        task_dir=workspace.task_dir,
        spec_path=workspace.spec_path,
        public_task_path=workspace.public_task_path,
        submission_dir=workspace.submission_dir,
        candidate_output_path=None,
        candidate_input_path=candidate_input,
        result_dir=workspace.result_dir,
        result_path=workspace.result_path,
        instructions_path=workspace.instructions_path,
    )


@dataclass(frozen=True)
class _BaseWorkspace:
    root: Path
    agent_name: str
    task_dir: Path
    spec_path: Path
    public_task_path: Path
    submission_dir: Path
    result_dir: Path
    result_path: Path
    instructions_path: Path


def _stage_public_workspace(
    task: StoredTask,
    workspace_root: str | Path,
    *,
    agent_name: str,
    template_root: str | Path | None,
) -> _BaseWorkspace:
    workspace_path = Path(workspace_root)
    workspace_path.mkdir(parents=True, exist_ok=False)
    task_dir = workspace_path / "task"
    shutil.copytree(task.public_dir, task_dir)
    submission_dir = workspace_path / "submission"
    submission_dir.mkdir(parents=True, exist_ok=True)
    result_dir = workspace_path / "result"
    result_dir.mkdir(parents=True, exist_ok=True)

    _copy_opencode_templates(template_root=Path(template_root) if template_root else project_root(), workspace_root=workspace_path)
    instructions_path = workspace_path / "TASK.md"
    return _BaseWorkspace(
        root=workspace_path,
        agent_name=agent_name,
        task_dir=task_dir,
        spec_path=task_dir / task.spec_path.name,
        public_task_path=task_dir / task.public_task_path.name,
        submission_dir=submission_dir,
        result_dir=result_dir,
        result_path=result_dir / "result.json",
        instructions_path=instructions_path,
    )


def _copy_opencode_templates(*, template_root: Path, workspace_root: Path) -> None:
    config_path = template_root / "opencode.json"
    if config_path.exists():
        shutil.copy2(config_path, workspace_root / "opencode.json")

    opencode_dir = template_root / ".opencode"
    if opencode_dir.exists():
        shutil.copytree(opencode_dir, workspace_root / ".opencode")

    (workspace_root / "AGENTS.md").write_text(
        "\n".join(
            [
                "# Workspace Rules",
                "",
                "- Use bash freely inside this workspace.",
                "- Do not assume hidden validators or hidden files exist here.",
                "- Read the skill docs in `.opencode/skills/` before using the main hardware tools for the first time.",
                "- Keep the primary deliverables in `submission/` and `result/`.",
                "- Clean up large generated files before finishing.",
            ]
        )
        + "\n"
    )
