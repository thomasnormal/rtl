"""Oracle for PULP Platform common_cells tasks. Uses xrun with assert-based TBs."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .oracle import SimulationPlan, SimulationRunResult

_ERROR_RE = re.compile(r"\*E,|\$error|\$fatal|Error:")


def validate_candidate(task, candidate_rtl_paths, *, work_root, timeout_s=120):
    oracle_meta = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "pulp_xrun":
        raise ValueError(f"task {task.task_id} is not a pulp_xrun oracle")

    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        candidate_rtl_paths = sorted(
            f for f in (p.iterdir() if p.is_dir() else [p]) if f.suffix in {".sv", ".v"}
        )
    candidates = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "xrun_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    dep_dir = task.root / str(oracle_meta.get("dep_dir", "oracle/deps"))
    tb_path = task.root / str(oracle_meta["testbench"])
    include_dir = task.root / str(oracle_meta.get("include_dir", "oracle/include"))

    source_files = []
    for f in sorted(dep_dir.glob("*_pkg.sv")):
        source_files.append(str(f))
    for f in sorted(dep_dir.iterdir()):
        if f.suffix == ".sv" and str(f) not in source_files:
            source_files.append(str(f))
    source_files.extend(str(f) for f in candidates)
    source_files.append(str(tb_path))

    tb_top = oracle_meta.get("tb_top", tb_path.stem)
    cmd = [
        "xrun", "-64bit", "-q", "-sv", f"+incdir+{include_dir}",
        "-top", tb_top, "-l", str(work_dir / "xrun.log"),
        "-xmlibdirname", str(work_dir / "xcelium.d"), *source_files,
    ]

    plan = SimulationPlan(
        task=task, source_files=tuple(Path(f) for f in source_files),
        work_dir=work_dir, log_path=work_dir / "xrun.log", preferred_simulator="xrun",
    )

    try:
        completed = subprocess.run(
            cmd, cwd=work_dir, capture_output=True, text=True, timeout=timeout_s, check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="xrun", plan=plan, command=tuple(cmd),
            returncode=-9, passed=False, stdout="", stderr="TIMEOUT",
        )

    output = completed.stdout + completed.stderr
    passed = completed.returncode == 0 and not _ERROR_RE.search(output)
    return SimulationRunResult(
        simulator="xrun", plan=plan, command=tuple(cmd),
        returncode=completed.returncode, passed=passed,
        stdout=completed.stdout, stderr=completed.stderr,
    )
