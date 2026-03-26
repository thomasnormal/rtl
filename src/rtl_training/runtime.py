from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .opencode_runtime import OpenCodeRunRequest
from .oracle import SimulationRunResult, validate_candidate
from .task_store import StoredTask, load_stored_task
from .workspace import StagedWorkspace, stage_generator_workspace, stage_verifier_workspace


DEFAULT_GENERATOR_PROMPT = (
    "Read TASK.md and complete the generator task. "
    "When finished, ensure submission/candidate.sv and result/result.json both exist."
)

DEFAULT_VERIFIER_PROMPT = (
    "Read TASK.md and complete the verifier task. "
    "Treat it as an evidence-gathering verification episode, not just a code review: "
    "derive a requirement checklist from the spec, write executable checks "
    "(prefer native SystemVerilog assertions, bind files, and self-checking SV testbenches under "
    "`xrun`, and escalate to native UVM under `xrun -uvm` when the interface complexity justifies "
    "it), then return a final verdict of `good` or `bad` in result/result.json. The candidate RTL "
    "is immutable input: do not edit files under candidate/."
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
    candidate_rtl_path: str | Path,
    workspace_root: str | Path,
    *,
    template_root: str | Path | None = None,
    model: str | None = None,
    prompt: str = DEFAULT_VERIFIER_PROMPT,
) -> VerifierEpisode:
    task = load_stored_task(task_root)
    workspace = stage_verifier_workspace(
        task,
        candidate_rtl_path,
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
    candidate_path = episode.workspace.candidate_output_path
    if candidate_path is None:
        raise ValueError("generator workspace does not define a candidate output path")
    return validate_candidate(
        episode.task,
        candidate_path,
        work_root=work_root,
        preferred_simulator=preferred_simulator,
        timeout_s=timeout_s,
    )
