from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .opencode_runtime import OpenCodeRunRequest
from .oracle import SimulationRunResult, validate_candidate, validate_candidate_cocotb
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
    "Render pages to images, read each image, and write the full transcription "
    "to output/. Write output/manifest.json when done."
)

DEFAULT_GENERATOR_PROMPT = (
    "Read TASK.md and complete the generator task. "
    "If task/spec/interface/ exists, treat it as the concrete SV declaration of the public DUT "
    "boundary. "
    "If task/spec/compat/ exists, treat it as a mandatory SV compatibility ABI and ensure the "
    "candidate RTL compiles against it. "
    "When finished, ensure at least one .sv or .v file exists under submission/ "
    "and result/result.json is present."
)

DEFAULT_VERIFIER_PROMPT = (
    "Read TASK.md and complete the verifier task. "
    "Treat it as an evidence-gathering verification episode, not just a code review: "
    "derive a requirement checklist from the spec, write executable checks "
    "(using task/spec/interface/ as the concrete SV form of the public DUT interface when it exists), "
    "(and, if task/spec/compat/ exists, use the compatibility SV files as part of the deep-DV contract), "
    "(prefer native SystemVerilog assertions, bind files, and self-checking SV testbenches under "
    "`xrun`, use cocotb when a Python reference model or scoreboard is clearer, and escalate to "
    "native UVM under `xrun -uvm` when the interface complexity justifies it), then return a final "
    "verdict of `good` or `bad` in result/result.json. The candidate RTL under candidate/ is "
    "immutable input: do not edit files under candidate/."
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
) -> SimulationRunResult:
    candidate_files = collect_candidate_files(episode.workspace.submission_dir)
    if not candidate_files:
        raise ValueError("generator did not produce any RTL files under submission/")

    oracle_meta = episode.task.metadata.get("oracle", {})
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
