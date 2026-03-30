"""Oracle for Alex Forencich verilog-axi / verilog-ethernet / verilog-pcie tasks.

Copies the upstream test directory, rewrites Makefile paths, and runs ``make``.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .oracle import SimulationPlan, SimulationRunResult, _COCOTB_PASS_RE


def validate_candidate(
    task,
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    timeout_s: int = 300,
) -> SimulationRunResult:
    oracle_meta: dict[str, Any] = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "makefile_cocotb":
        raise ValueError(f"task {task.task_id} does not have a makefile_cocotb oracle")

    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        candidate_rtl_paths = sorted(
            f for f in (p.iterdir() if p.is_dir() else [p])
            if f.suffix in {".sv", ".v"}
        )
    resolved = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "makefile_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    oracle_dir = task.root / str(oracle_meta["test_dir"])
    shutil.copytree(oracle_dir, work_dir)

    rtl_dir = work_dir / "rtl"
    rtl_dir.mkdir(exist_ok=True)
    for cand in resolved:
        shutil.copy2(cand, rtl_dir / cand.name)

    gold_rtl_dir = task.root / str(oracle_meta.get("gold_rtl_dir", "oracle/rtl"))
    if gold_rtl_dir.is_dir():
        for f in sorted(gold_rtl_dir.iterdir()):
            dest = rtl_dir / f.name
            if not dest.exists() and f.suffix in {".v", ".sv"}:
                shutil.copy2(f, dest)

    makefile_path = work_dir / "Makefile"
    if makefile_path.exists():
        text = makefile_path.read_text()
        text = text.replace("../../rtl/", "./rtl/")
        text = re.sub(r"^WAVES\s*\?=\s*\d+", "WAVES := 0", text, flags=re.MULTILINE)
        text = re.sub(r"PLUSARGS\s*\+=\s*-fst\b", "", text)
        text = re.sub(r"COCOTB_PLUSARGS\s*\+=\s*-fst\b", "", text)
        makefile_path.write_text(text)

    for d in ("sim_build", "sim-build", "obj_dir", "__pycache__"):
        stale = work_dir / d
        if stale.exists():
            shutil.rmtree(stale)

    plan = SimulationPlan(
        task=task, source_files=tuple(resolved), work_dir=work_dir,
        log_path=work_dir / "sim.log", preferred_simulator="cocotb+icarus",
    )

    env = {**subprocess.os.environ, "SIM": "icarus", "WAVES": "0"}
    env.pop("PLUSARGS", None)

    try:
        completed = subprocess.run(
            ("make",), cwd=work_dir, capture_output=True, text=True,
            timeout=timeout_s, check=False, env=env,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="cocotb+icarus", plan=plan, command=("make",),
            returncode=-9, passed=False, stdout="", stderr="TIMEOUT",
        )

    output = completed.stdout + completed.stderr
    match = _COCOTB_PASS_RE.search(output)
    passed = match is not None and int(match.group(1)) > 0 and int(match.group(2)) == int(match.group(1)) and int(match.group(3)) == 0

    return SimulationRunResult(
        simulator="cocotb+icarus", plan=plan, command=("make",),
        returncode=completed.returncode, passed=passed,
        stdout=completed.stdout, stderr=completed.stderr,
    )
