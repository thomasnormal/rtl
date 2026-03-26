from __future__ import annotations

from dataclasses import dataclass
import stat
from pathlib import Path
import shutil

from .task_store import StoredTask

_RTL_EXTENSIONS = frozenset({".sv", ".v", ".svh", ".vh"})


@dataclass(frozen=True)
class StagedWorkspace:
    root: Path
    agent_name: str
    task_dir: Path
    spec_dir: Path
    public_task_path: Path
    submission_dir: Path
    candidate_input_dir: Path | None
    result_dir: Path
    result_path: Path
    instructions_path: Path


def collect_candidate_files(directory: Path) -> tuple[Path, ...]:
    """Return all RTL source files (.sv, .v, .svh, .vh) under *directory*, sorted by name."""
    if not directory.is_dir():
        return ()
    return tuple(
        sorted(
            (p for p in directory.iterdir() if p.is_file() and p.suffix in _RTL_EXTENSIONS),
            key=lambda p: p.name,
        )
    )


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
            "- Read `task/task.json` and the spec files under `task/spec/` before writing RTL.",
            "- If `task/spec/README.md` exists, read it first. If `task/spec/doc/` exists, read the functional spec files there and derive a requirement checklist before coding.",
            "- Write the requirement checklist to `result/requirements.md` and use it to drive the implementation.",
            "- Treat `task/spec/interface/` as the concrete SV form of the public top-level interface when it exists.",
            "- If `task/spec/interface/` contains task-local SV packages or typedef files, those are the public type definitions to use. Do not reach for upstream repository packages when the task-local interface collateral already defines the boundary.",
            "- Treat `task/task.json` as the authoritative machine-readable contract for the top module, interface hints, and deliverables.",
            "- If `task/spec/compat/` exists, treat the SV files there as a mandatory compatibility ABI. The generated RTL must compile against that ABI and satisfy any required named interfaces or bind points it defines exactly.",
            "- Interface and compatibility are necessary but not sufficient. The candidate must implement the full functional behavior described by the spec, not just a stub that satisfies ports or shallow compatibility checks.",
            "- Do not depend on upstream or OpenTitan repository packages just to satisfy the public task boundary. If the task leaks repo-specific package types, treat that as a task-definition problem rather than patching `submission/` with package scaffolding.",
            "- Write candidate RTL files to `submission/`. The top module must match `task/task.json`.",
            "- You may produce one or more `.sv`/`.v` files under `submission/`.",
            "- Before finishing, run at least one compile sanity check against the generated RTL and the public task collateral when the workspace contains enough SV/package context to do so. Record the command and outcome in `result/requirements.md`.",
            "- For OpenTitan-style tasks and any task with package-typed ports, interfaces, compat SV, or UVM-style collateral, the required compile/elaboration check is `xrun`/Xcelium. In those cases, `yosys` does not satisfy the compile-check requirement.",
            "- Use `yosys` only as a fallback for small standalone RTL where vendor/package context is not needed.",
            "- Write a machine-readable summary to `result/result.json`.",
            "- There is no oracle validator in this workspace.",
        ]
    )
    workspace.instructions_path.write_text(task_note + "\n")
    return StagedWorkspace(
        root=workspace.root,
        agent_name=workspace.agent_name,
        task_dir=workspace.task_dir,
        spec_dir=workspace.spec_dir,
        public_task_path=workspace.public_task_path,
        submission_dir=workspace.submission_dir,
        candidate_input_dir=None,
        result_dir=workspace.result_dir,
        result_path=workspace.result_path,
        instructions_path=workspace.instructions_path,
    )


def stage_verifier_workspace(
    task: StoredTask,
    candidate_rtl_dir: str | Path,
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
    source_dir = Path(candidate_rtl_dir)
    if source_dir.is_dir():
        for src_file in sorted(source_dir.iterdir()):
            if src_file.is_file():
                dest = candidate_dir / src_file.name
                shutil.copy2(src_file, dest)
                dest.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    else:
        # Single file path for convenience.
        dest = candidate_dir / source_dir.name
        shutil.copy2(source_dir, dest)
        dest.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    task_note = "\n".join(
        [
            "# Verifier Task",
            "",
            "- Read the spec files under `task/spec/`, `task/task.json`, and the candidate RTL files under `candidate/`.",
            "- Treat `task/spec/interface/` as the concrete SV form of the public top-level interface when it exists.",
            "- Treat `task/task.json` as the authoritative machine-readable public contract for the expected top module and interface hints.",
            "- If `task/spec/compat/` exists, treat the SV files there as the task's deep-DV compatibility ABI and use them when evaluating whether the candidate is compatible with deeper verification.",
            "- Treat the candidate RTL as immutable input. Do not edit files under `candidate/`.",
            "- Turn the spec into a concrete requirement checklist before judging the RTL.",
            "- Use the available tools to gather evidence.",
            "- Do not stop at code inspection. Write executable checks: prefer native SVAs, bind files, and self-checking SystemVerilog benches under `xrun`, use cocotb when a Python reference model or scoreboard is clearer, and escalate to native UVM under `xrun -uvm` when the protocol is non-trivial.",
            "- Save the requirement checklist and the generated verification artifacts under `result/evidence/`.",
            "- Write the final verdict bundle to `result/result.json`.",
            "- Put larger evidence artifacts under `result/evidence/`.",
            "- There is no hidden oracle in this workspace.",
        ]
    )
    workspace.instructions_path.write_text(task_note + "\n")
    return StagedWorkspace(
        root=workspace.root,
        agent_name=workspace.agent_name,
        task_dir=workspace.task_dir,
        spec_dir=workspace.spec_dir,
        public_task_path=workspace.public_task_path,
        submission_dir=workspace.submission_dir,
        candidate_input_dir=candidate_dir,
        result_dir=workspace.result_dir,
        result_path=workspace.result_path,
        instructions_path=workspace.instructions_path,
    )


@dataclass(frozen=True)
class ConverterWorkspace:
    root: Path
    input_dir: Path
    pdf_path: Path
    output_dir: Path
    instructions_path: Path


def stage_converter_workspace(
    pdf_path: str | Path,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
) -> ConverterWorkspace:
    """Stage a workspace for the PDF-to-markdown converter agent."""
    workspace_path = Path(workspace_root)
    workspace_path.mkdir(parents=True, exist_ok=False)

    input_dir = workspace_path / "input"
    input_dir.mkdir()
    staged_pdf = input_dir / "source.pdf"
    shutil.copy2(pdf_path, staged_pdf)

    output_dir = workspace_path / "output"
    output_dir.mkdir()

    _copy_opencode_templates(
        template_root=Path(template_root) if template_root else project_root(),
        workspace_root=workspace_path,
    )

    instructions_path = workspace_path / "TASK.md"
    instructions_path.write_text(
        "# Converter Task\n\n"
        "- Convert the PDF in `input/source.pdf` to markdown.\n"
        "- Write all output files to `output/`.\n"
        "- See the converter agent prompt for detailed instructions.\n"
    )

    return ConverterWorkspace(
        root=workspace_path,
        input_dir=input_dir,
        pdf_path=staged_pdf,
        output_dir=output_dir,
        instructions_path=instructions_path,
    )


@dataclass(frozen=True)
class _BaseWorkspace:
    root: Path
    agent_name: str
    task_dir: Path
    spec_dir: Path
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
        spec_dir=task_dir / "spec",
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
