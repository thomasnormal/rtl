from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import shutil
import subprocess
import sys

from .task_store import StoredTask


_REPO_COPY_IGNORE = shutil.ignore_patterns(
    ".git",
    "scratch",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
)


@dataclass(frozen=True)
class OpenTitanDvsimOracle:
    cfg: str
    test: str
    tool: str
    golden_rtl_dir: Path
    overlay_rel_dir: str
    source_root: Path

    @classmethod
    def from_task(cls, task: StoredTask) -> "OpenTitanDvsimOracle":
        raw = task.metadata.get("oracle")
        if not isinstance(raw, dict) or raw.get("kind") != "opentitan_dvsim":
            raise ValueError(f"task {task.task_id} does not have an OpenTitan dvsim oracle")

        if task.shared_private_ref is not None:
            source_root = task.shared_private_ref.bundle_root()
        else:
            source_root_value = task.metadata.get("source", {}).get("source_root")
            if not source_root_value:
                raise ValueError(f"task {task.task_id} is missing source_root for OpenTitan oracle")
            source_root = Path(str(source_root_value)).resolve()

        return cls(
            cfg=str(raw["cfg"]),
            test=str(raw["test"]),
            tool=str(raw.get("tool", "xcelium")),
            golden_rtl_dir=task.root / "oracle" / str(raw["golden_rtl_dir"]),
            overlay_rel_dir=str(raw["overlay_rel_dir"]),
            source_root=source_root,
        )


@dataclass(frozen=True)
class OpenTitanDvsimPlan:
    task: StoredTask
    oracle: OpenTitanDvsimOracle
    work_dir: Path
    repo_root: Path
    scratch_root: Path
    log_path: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class OpenTitanDvsimRunResult:
    plan: OpenTitanDvsimPlan
    returncode: int
    passed: bool
    stdout: str
    stderr: str


def build_opentitan_gold_selftest_plan(
    task: StoredTask,
    *,
    work_root: str | Path,
) -> OpenTitanDvsimPlan:
    oracle = OpenTitanDvsimOracle.from_task(task)

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "opentitan_gold_selftest"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    repo_root = work_dir / "repo"
    _copy_repo_tree(oracle.source_root, repo_root)

    overlay_dir = repo_root / oracle.overlay_rel_dir
    overlay_dir.parent.mkdir(parents=True, exist_ok=True)
    if overlay_dir.exists():
        shutil.rmtree(overlay_dir)
    shutil.copytree(oracle.golden_rtl_dir, overlay_dir)

    scratch_root = work_dir / "scratch"
    command = (
        sys.executable,
        "util/dvsim/dvsim.py",
        oracle.cfg,
        "-i",
        oracle.test,
        "-t",
        oracle.tool,
        "--proj-root",
        str(repo_root),
        "--scratch-root",
        str(scratch_root),
        "--purge",
        "--fixed-seed",
        "1",
        "--reseed",
        "1",
    )
    return OpenTitanDvsimPlan(
        task=task,
        oracle=oracle,
        work_dir=work_dir,
        repo_root=repo_root,
        scratch_root=scratch_root,
        log_path=work_dir / "dvsim.log",
        command=command,
    )


def run_opentitan_dvsim_plan(
    plan: OpenTitanDvsimPlan,
    *,
    timeout_s: int = 1800,
) -> OpenTitanDvsimRunResult:
    completed = subprocess.run(
        plan.command,
        cwd=plan.repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    plan.log_path.write_text(completed.stdout + completed.stderr)
    return OpenTitanDvsimRunResult(
        plan=plan,
        returncode=completed.returncode,
        passed=completed.returncode == 0,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def validate_opentitan_gold_reference(
    task: StoredTask,
    *,
    work_root: str | Path,
    timeout_s: int = 1800,
) -> OpenTitanDvsimRunResult:
    plan = build_opentitan_gold_selftest_plan(task, work_root=work_root)
    return run_opentitan_dvsim_plan(plan, timeout_s=timeout_s)


def _copy_repo_tree(source_root: Path, destination_root: Path) -> None:
    shutil.copytree(
        source_root,
        destination_root,
        symlinks=True,
        copy_function=_link_or_copy_file,
        ignore=_REPO_COPY_IGNORE,
    )


def _link_or_copy_file(src: str, dst: str) -> None:
    try:
        os.link(src, dst)
    except OSError as err:
        if err.errno not in {errno.EXDEV, errno.EPERM, errno.ENOTSUP, errno.EACCES}:
            raise
        shutil.copy2(src, dst)
