from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from task_library.opentitan.helper import OpenTitanDvsimRunResult, validate_opentitan_candidate
from .opencode_runtime import OpenCodeRunRequest
from task_library.cvdp.helper import validate_candidate_cocotb
from .oracle import SimulationRunResult, validate_candidate
from .task_store import StoredTask, load_stored_task
from .workspace import (
    ConverterWorkspace,
    StagedWorkspace,
    collect_candidate_files,
    stage_converter_workspace,
    stage_generator_workspace,
    stage_verifier_workspace,
)


DEFAULT_CONVERTER_PROMPT = (
    "Read TASK.md and convert the PDF in input/source.pdf to markdown. "
    "Pre-rendered page images are available under input/pages/ and gridded reference copies are available under input/pages_grid/. "
    "Use the read tool on each page image at least once, inspect the PDF page by page with the multimodal model, "
    "use the gridded copies to choose conservative crop coordinates, crop actual figures from input/pages/, "
    "extract figures into output/figures/ when needed, and write exhaustive markdown split by chapter "
    "or other high-level section, with figures referenced using paths like ![Figure ...](figures/figure-042.png). Do not split chapters by page range or collapse a multi-page PDF into spec.md or full.md. "
    "A slightly undercropped image is better than an overcropped one. "
    "Write output/manifest.json when done."
)

DEFAULT_GENERATOR_PROMPT = (
    "Read TASK.md and complete the generator task. "
    "Read task/task.json first; field `top_module` is the authoritative top-module name. "
    "Before writing RTL, read the behavioral spec under task/spec/, especially task/spec/README.md "
    "and task/spec/doc/ when present, and turn it into a requirement checklist saved under result/. "
    "If task/spec/doc/registers.md, task/spec/doc/programmers_guide.md, task/spec/dv/README.md, or "
    "task/spec/data/*testplan*.hjson exist, use them to identify software-visible side effects, "
    "documented register-map offsets, and high-risk behaviors that your local checks must cover. "
    "Treat task/spec/interface/ as the concrete SV declaration of the public DUT boundary and "
    "use any task-local SV packages or typedef files there as the public type source instead of "
    "upstream repository packages. If task/spec/interface/ includes a generated bus helper package, "
    "use its field helpers instead of hard-coded bit slicing and preserve semantically relevant "
    "request/response metadata such as source, size, param, and user fields. "
    "Treat the staged task directory as the complete public problem statement and do not assume "
    "access to upstream repo code, hidden packages, or hidden hierarchy outside the workspace. "
    "Treat task/task.json as lightweight machine-readable metadata, but interface and microarchitecture are necessary "
    "not sufficient: implement the full functional behavior from the spec, not a stub. "
    "Do not make the solution depend on importing upstream repository packages just to satisfy the "
    "public task boundary. "
    "If task/spec/micro_arch/ exists, treat it as a mandatory SV microarchitecture ABI and ensure the "
    "candidate RTL compiles against it exactly, including required named instances or bind points. "
    "If task/spec/micro_arch/README.md exists, read it and turn each exported microarchitecture signal "
    "into an explicit requirement in result/requirements.md; do not infer a signal's meaning from its name alone. "
    "Treat `submission/` as a self-contained deliverable set and do not `include` files from `task/` "
    "inside submission RTL. If you need task-local public typedefs or packages, mirror them into "
    "normal compilation-unit files under `submission/` and `import` them there. "
    "Do not spend the whole run in analysis; after the first requirement pass, start writing RTL and "
    "executable checks early so you can iterate with evidence. "
    "Before finishing, write at least one self-checking executable check of your own under "
    "`result/evidence/`. Prefer a SystemVerilog smoke bench or directed test that instantiates the "
    "DUT top and checks concrete behaviors from the requirement checklist. For timing-sensitive, "
    "sequential, or protocol behavior, dump a waveform under `result/evidence/` and inspect it with "
    "`vcdcat`; use waveform review as supporting evidence, not as a substitute for self-checking "
    "tests or assertions. If task/spec/micro_arch/ exists, include at least one executable check for "
    "every exported microarchitecture signal. If a microarchitecture signal could differ from a public "
    "pin, status bit, or other visible output because of masking, gating, latching, or pulse generation, "
    "add a directed negative test that forces those values to differ and checks the distinction explicitly. "
    "Record which requirements were covered by each generated test, bench, assertion, or waveform review "
    "in `result/requirements.md`. "
    "Before finishing, run at least one compile sanity check when the workspace has enough context "
    "to do so. Use `xrun`/Xcelium for that compile sanity check. The compile "
    "check only counts if it elaborates the DUT top module named in task/task.json field `top_module`, or a smoke test "
    "that instantiates that DUT top; a helper interface or package alone does not count. If you use "
    "`xrun`, select the DUT top explicitly with `-top <dut>` or instantiate it in a tiny smoke bench. "
    "When you need waveform evidence, generate the dump from your own temporary bench, keep it under "
    "`result/evidence/`, and inspect focused signals with `vcdcat -l` / `vcdcat -x`. If `vcdcat` is "
    "unavailable or broken, record the exact failure and use a small local parser or script to inspect "
    "the same focused signals instead of skipping waveform review. "
    "If the task exposes a documented CSR/register map, do not stop at a happy-path smoke test. Add "
    "at least one executable check for documented side effects such as write-only registers, RW1C "
    "behavior, interrupt-clear behavior, or bad-access error handling before claiming `status: pass`. "
    "If `xrun` runtime simulation is unavailable and you fall back to another simulator, that evidence "
    "only supports `status: pass` if the fallback tests explicitly cover every high-risk requirement "
    "and every exported microarchitecture signal; otherwise record the gaps and do not claim `pass`. "
    "If the compile check fails, or the implementation is intentionally partial, result/result.json "
    "must not claim `status: pass`. Then ensure at least one .sv or .v file exists under submission/ "
    "and result/result.json is present. As soon as result/result.json is written and matches the "
    "current evidence, stop the run. Do not spend extra steps on optional cleanup, disk-usage "
    "inspection, or prose polish after result/result.json exists unless that work is required to "
    "keep the result bundle truthful."
)

DEFAULT_VERIFIER_PROMPT = (
    "Read TASK.md and complete the verifier task. "
    "Read task/task.json first; field `top_module` is the authoritative expected DUT top-module name. "
    "Treat it as an evidence-gathering verification episode, not just a code review: "
    "derive a requirement checklist from the spec, write executable checks "
    "(using task/spec/interface/ as the concrete SV form of the public DUT interface when it exists), "
    "(and using generated public bus helper packages when they exist so checks cover metadata fields "
    "such as source/size/param/user rather than only data and error), "
    "(and, if task/spec/micro_arch/ exists, use the microarchitecture SV files as part of the deep-DV contract), "
    "Treat the staged task directory as the complete public problem statement and do not assume access "
    "to upstream repo code, hidden packages, or hidden hierarchy outside the workspace. "
    "(prefer native SystemVerilog assertions, bind files, and self-checking SV testbenches under "
    "`xrun`, use cocotb when a Python reference model or scoreboard is clearer, and escalate to "
    "native UVM under `xrun -uvm` when the interface complexity justifies it), then return a final "
    "verdict of `good` or `bad` in result/result.json. Do not use `yosys`; use `xrun`/Xcelium for "
    "all compile, elaboration, SVA, and smoke-test checks. The candidate RTL under candidate/ is "
    "immutable input: do not edit files under candidate/. As soon as result/result.json is written "
    "and the referenced evidence files exist, stop the run instead of spending steps on optional "
    "cleanup or extra polish."
)


@dataclass(frozen=True)
class GeneratorEpisode:
    task: StoredTask
    workspace: StagedWorkspace
    request: OpenCodeRunRequest


@dataclass(frozen=True)
class VerifierEpisode:
    task: StoredTask
    workspace: StagedWorkspace
    request: OpenCodeRunRequest


@dataclass(frozen=True)
class ConverterEpisode:
    pdf_path: Path
    workspace: ConverterWorkspace
    request: OpenCodeRunRequest


def prepare_converter_episode(
    pdf_path: str | Path,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
    model: str | None = None,
    prompt: str = DEFAULT_CONVERTER_PROMPT,
) -> ConverterEpisode:
    resolved_pdf = Path(pdf_path).resolve()
    workspace = stage_converter_workspace(
        resolved_pdf,
        workspace_root,
        template_root=template_root,
    )
    request = OpenCodeRunRequest(
        workspace_root=workspace.root,
        agent="converter",
        prompt=prompt,
        model=model,
    )
    return ConverterEpisode(pdf_path=resolved_pdf, workspace=workspace, request=request)


def prepare_generator_episode(
    task_root: str | Path,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
    model: str | None = None,
    prompt: str = DEFAULT_GENERATOR_PROMPT,
) -> GeneratorEpisode:
    task = load_stored_task(task_root)
    workspace = stage_generator_workspace(task, workspace_root, template_root=template_root)
    request = OpenCodeRunRequest(
        workspace_root=workspace.root,
        agent="generator",
        prompt=prompt,
        model=model,
    )
    return GeneratorEpisode(task=task, workspace=workspace, request=request)


def prepare_verifier_episode(
    task_root: str | Path,
    candidate_rtl_dir: str | Path,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
    model: str | None = None,
    prompt: str = DEFAULT_VERIFIER_PROMPT,
) -> VerifierEpisode:
    task = load_stored_task(task_root)
    workspace = stage_verifier_workspace(
        task,
        candidate_rtl_dir,
        workspace_root,
        template_root=template_root,
    )
    request = OpenCodeRunRequest(
        workspace_root=workspace.root,
        agent="verifier",
        prompt=prompt,
        model=model,
    )
    return VerifierEpisode(task=task, workspace=workspace, request=request)


def validate_generator_episode(
    episode: GeneratorEpisode,
    *,
    work_root: str | Path,
    preferred_simulator: str | None = "xrun",
    timeout_s: int = 30,
) -> SimulationRunResult | OpenTitanDvsimRunResult:
    candidate_files = collect_candidate_files(episode.workspace.submission_dir)
    if not candidate_files:
        raise ValueError("generator did not produce any RTL files under submission/")

    oracle_meta = episode.task.metadata.get("oracle", {})
    if oracle_meta.get("kind") == "opentitan_dvsim":
        return validate_opentitan_candidate(
            episode.task,
            candidate_dir=episode.workspace.submission_dir,
            work_root=work_root,
            timeout_s=timeout_s,
        )
    if oracle_meta.get("kind") == "cocotb":
        return validate_candidate_cocotb(
            episode.task,
            candidate_files,
            work_root=work_root,
            timeout_s=timeout_s,
        )

    return validate_candidate(
        episode.task,
        candidate_files,
        work_root=work_root,
        preferred_simulator=preferred_simulator,
        timeout_s=timeout_s,
    )
