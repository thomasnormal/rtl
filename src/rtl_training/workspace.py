from __future__ import annotations

from dataclasses import dataclass
import json
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
            "- If `task/spec/doc/registers.md`, `task/spec/doc/programmers_guide.md`, `task/spec/dv/README.md`, or `task/spec/data/*testplan*.hjson` exist, use them to identify software-visible side effects, documented register-map offsets, and high-risk behaviors that your local checks must cover.",
            "- Write the requirement checklist to `result/requirements.md` and use it to drive the implementation.",
            "- Treat `task/spec/interface/` as the concrete SV form of the public top-level interface when it exists.",
            "- If `task/spec/interface/` contains task-local SV packages or typedef files, those are the public type definitions to use. Do not reach for upstream repository packages when the task-local interface collateral already defines the boundary.",
            "- If `task/spec/interface/` contains a generated bus helper package, use its accessors instead of hard-coded bit slicing and preserve semantically relevant request/response metadata such as source, size, param, and user fields.",
            "- The staged `task/` directory is the complete public problem statement. Do not assume access to upstream repo code, hidden packages, or hidden hierarchy outside this workspace.",
            "- Treat `task/task.json` as lightweight machine-readable metadata for task identity, the DUT top module, and deliverables.",
            "- If `task/spec/micro_arch/` exists, treat the SV files there as a mandatory microarchitecture ABI. The generated RTL must compile against that ABI and satisfy any required named interfaces or bind points it defines exactly.",
            "- If `task/spec/micro_arch/README.md` exists, read it and turn each exported microarchitecture signal into an explicit requirement in `result/requirements.md`. Do not infer a signal's meaning from its name alone.",
            "- Interface and microarchitecture are necessary but not sufficient. The candidate must implement the full functional behavior described by the spec, not just a stub that satisfies ports or shallow ABI checks.",
            "- Do not depend on upstream or OpenTitan repository packages just to satisfy the public task boundary. If the task leaks repo-specific package types, treat that as a task-definition problem rather than patching `submission/` with package scaffolding.",
            "- Do not spend the whole run in analysis. After the first requirement pass, start writing RTL and executable checks early so you can iterate with evidence.",
            "- Immediately after the first requirement pass, update the existing `result/result.json` stub with the current best evidence-backed status, output file plan, summary, and assumptions.",
            "- Write candidate RTL files to `submission/`. The top module must match `task/task.json` field `top_module` exactly.",
            "- You may produce one or more `.sv`/`.v` files under `submission/`.",
            "- `submission/` must be a self-contained deliverable set. Do not use `` `include `` paths that reach into `task/` from the submission RTL.",
            "- If you need task-local public typedefs or packages, mirror them into normal compilation-unit files under `submission/` and `import` them there rather than relying on workspace-relative include paths.",
            "- Before finishing, write at least one executable check of your own under `result/evidence/`.",
            "- Prefer a self-checking SystemVerilog smoke bench or directed test that instantiates the DUT top and checks concrete behaviors from the requirement checklist.",
            "- If `task/spec/micro_arch/` exists, include at least one executable check for every exported microarchitecture signal listed in the public ABI.",
            "- If a microarchitecture signal could differ from a public pin, status bit, or other visible output because of masking, gating, latching, or pulse generation, add a directed negative test that forces those values to differ and checks the distinction explicitly.",
            "- For derived combinational outputs or status words, do not hide dependencies behind zero-argument helper functions used from continuous assigns or `always @*`. Use `always_comb` or pass every dependency as an explicit function argument so commercial simulators reevaluate the logic when any input changes.",
            "- For request/response interfaces, qualify read side effects, pulses, and response metadata with the actual request-valid handshake. Do not let raw address decode alone assert outputs such as claim pulses, done flags, or response-valid signals outside a real transaction.",
            "- For timing-sensitive, sequential, or protocol behavior, dump a waveform under `result/evidence/` and inspect it with `vcdcat` before claiming the implementation matches the spec.",
            "- Use waveform review as supporting evidence, not as a substitute for self-checking tests or assertions.",
            "- Record which requirements were covered by each generated test, bench, assertion, or waveform review in `result/requirements.md`.",
            "- Before finishing, run at least one compile sanity check against the generated RTL and the public task collateral when the workspace contains enough SV/package context to do so. Use `xrun`/Xcelium for that check and record the command and outcome in `result/requirements.md`.",
            "- The compile check only counts if it elaborates the DUT top module named in `task/task.json` field `top_module`, or a smoke test that instantiates that DUT top. A helper interface or package alone does not count.",
            "- If you use `xrun`, select the DUT top explicitly with `-top <dut>` or instantiate it in a tiny smoke bench.",
            "- When you need waveform evidence, generate the dump from your own temporary bench, keep it under `result/evidence/`, and inspect focused signals with `vcdcat -l` / `vcdcat -x`.",
            "- If `vcdcat` is unavailable or broken in the workspace, record the exact failure and use a small local parser or script to inspect the same focused signals instead of skipping waveform review.",
            "- If the task exposes a documented CSR/register map, do not stop at a happy-path smoke test. Add at least one executable check for documented side effects such as write-only registers, RW1C behavior, interrupt-clear behavior, or bad-access error handling before claiming `status: pass`.",
            "- If `xrun` runtime simulation is unavailable and you fall back to another simulator, that evidence only supports `status: pass` if the fallback tests explicitly cover every high-risk requirement and every exported microarchitecture signal. Otherwise record the gaps and do not claim `pass`.",
            "- Update the existing `result/result.json` stub with a machine-readable summary.",
            "- Write `result/result.json` early once you have a first evidence-backed implementation state, and update it later if additional checks materially change the conclusion.",
            "- If you are past roughly 60% of your step budget and `result/result.json` does not exist yet, stop and write the best truthful summary bundle you can from the current evidence.",
            "- As soon as `result/result.json` is written and matches the evidence on disk, stop the run.",
            "- Do not spend extra steps on optional cleanup, disk-usage inspection, or prose polish after `result/result.json` exists unless that work is required to keep the result bundle truthful.",
            "- If the compile check fails, `result/result.json` must not claim `status: pass`.",
            "- If the implementation is partial, minimal, or intentionally omits major spec behavior, `result/result.json` must not claim `status: pass`.",
            "- Do not silently redefine the meaning of a public microarchitecture signal by assumption. If a signal might represent a raw source state rather than a gated or transformed public output, write an executable check that distinguishes those cases before claiming `status: pass`.",
            "- For combinational helper logic, avoid zero-argument functions with hidden global dependencies in continuous assigns or `always @*`; compute the value in `always_comb` or pass dependencies explicitly.",
            "- For request/response task interfaces, make side effects depend on a real valid transaction, not just decoded address values.",
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
            "- If `task/spec/interface/` contains a generated bus helper package, use its accessors instead of ad hoc bit slicing so your checks cover metadata fields such as source, size, param, and user as well as data and error.",
            "- The staged `task/` directory is the complete public problem statement. Do not assume access to upstream repo code, hidden packages, or hidden hierarchy outside this workspace.",
            "- Treat `task/task.json` as lightweight machine-readable public metadata, including the expected DUT top module in field `top_module`.",
            "- If `task/spec/micro_arch/` exists, treat the SV files there as the task's deep-DV microarchitecture ABI and use them when evaluating whether the candidate is compatible with deeper verification.",
            "- Treat the candidate RTL as immutable input. Do not edit files under `candidate/`.",
            "- Turn the spec into a concrete requirement checklist before judging the RTL.",
            "- Use the available tools to gather evidence.",
            "- Do not stop at code inspection. Write executable checks: prefer native SVAs, bind files, and self-checking SystemVerilog benches under `xrun`, use cocotb when a Python reference model or scoreboard is clearer, and escalate to native UVM under `xrun -uvm` when the protocol is non-trivial.",
            "- After changing DUT inputs in a bench, especially combinational control or data inputs, advance at least one delta cycle (`#1step`, `#0`, or a tiny local delay such as `#1ps`) before sampling derived outputs. Do not write same-timestep checks that rely on zero-delta propagation through `always_comb` or continuous assigns.",
            "- Do not use `yosys`; use `xrun`/Xcelium for compile, elaboration, SVA, and smoke-test checks.",
            "- Save the requirement checklist and the generated verification artifacts under `result/evidence/`.",
            "- If a reproducible executable check shows a concrete critical spec violation, that is already sufficient evidence for `verdict: bad`; update `result/result.json` immediately instead of continuing to search for more failures.",
            "- Update the existing `result/result.json` stub with the final verdict bundle.",
            "- As soon as `result/result.json` is written and the referenced evidence files exist, stop the run.",
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
    pages_dir: Path
    pages_grid_dir: Path
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
    pages_dir = input_dir / "pages"
    pages_dir.mkdir()
    pages_grid_dir = input_dir / "pages_grid"
    pages_grid_dir.mkdir()

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
        "- Pre-rendered page images are available under `input/pages/`; inspect those images page by page.\n"
        "- Gridded reference copies of the same pages are available under `input/pages_grid/`; use them to choose conservative crop coordinates.\n"
        "- Use the `read` tool on every `input/pages/page-*.png` at least once before finishing. The control plane validates this.\n"
        "- Write markdown files to `output/`, split by chapter or other high-level section.\n"
        "- Use descriptive ordered names such as `01_overview.md`, `02_architecture.md`, and `03_timing.md`.\n"
        "- Put extracted figure images under `output/figures/`.\n"
        "- Reference extracted figures from markdown with paths like `![Figure 3-2](figures/figure-042.png)`.\n"
        "- Use Python and PIL only when you need to crop figure regions from a pre-rendered page image.\n"
        "- Read gridded page copies to decide crop boxes, but crop actual figure assets from the raw pages in `input/pages/`, not from the gridded copies.\n"
        "- A slightly undercropped figure is better than an overcropped one. Keep captions, labels, and a little surrounding context when in doubt.\n"
        "- Be exhaustive. Do not skip any page content, even if it is repetitive, mostly visual, or mostly a caption/table.\n"
        "- Every source page must be covered somewhere in the markdown output, but the files should follow document structure rather than page boundaries.\n"
        "- See the converter agent prompt for the full conversion workflow.\n"
    )

    return ConverterWorkspace(
        root=workspace_path,
        input_dir=input_dir,
        pdf_path=staged_pdf,
        pages_dir=pages_dir,
        pages_grid_dir=pages_grid_dir,
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
    result_path = result_dir / "result.json"
    _write_initial_result_stub(result_path, agent_name=agent_name)

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
        result_path=result_path,
        instructions_path=instructions_path,
    )


def _write_initial_result_stub(path: Path, *, agent_name: str) -> None:
    payload = {
        "status": "in_progress",
        "agent": agent_name,
        "summary": "Update this file with the current evidence-backed status before finishing.",
    }
    if agent_name == "generator":
        payload.update(
            {
                "output_file": "",
                "assumptions": [],
            }
        )
    elif agent_name == "verifier":
        payload.update(
            {
                "verdict": "",
                "confidence": "",
                "requirements_checked": [],
                "evidence_files": [],
            }
        )
    path.write_text(json.dumps(payload, indent=2) + "\n")


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
