"""Oracle for Alex Forencich verilog-axi / verilog-ethernet tasks.

These projects use standard cocotb Makefiles with icarus.  The oracle
copies the upstream test directory, rewrites ``VERILOG_SOURCES`` paths
to point at the candidate RTL, and runs ``make``.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Sequence

from rtl_training.oracle import SimulationPlan, SimulationRunResult, _COCOTB_PASS_RE
from rtl_training.task_store import StoredTask


def validate_candidate(
    task: StoredTask,
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    timeout_s: int = 300,
) -> SimulationRunResult:
    """Validate candidate RTL using the upstream cocotb Makefile.

    The oracle metadata must have ``kind: makefile_cocotb`` and the
    following fields:

    * ``test_dir`` — path (relative to task root) of the cocotb test
      directory containing ``Makefile`` and ``test_*.py``.
    * ``gold_rtl_dir`` — path to directory holding gold RTL files that
      the candidate is NOT replacing (sub-module deps).
    * ``dut_source_files`` — list of filenames (relative to ``rtl/``)
      that constitute the DUT.  The candidate is expected to supply
      replacements for these.
    """
    oracle_meta: dict[str, Any] = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "makefile_cocotb":
        raise ValueError(f"task {task.task_id} does not have a makefile_cocotb oracle")

    # Resolve candidate paths
    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        if p.is_dir():
            candidate_rtl_paths = sorted(
                f for f in p.iterdir()
                if f.is_file() and f.suffix in {".sv", ".v"}
            )
        else:
            candidate_rtl_paths = [p]
    resolved_candidates = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "makefile_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    # Copy the full oracle test directory tree (Makefile, test_*.py)
    oracle_dir = task.root / str(oracle_meta["test_dir"])
    shutil.copytree(oracle_dir, work_dir)

    # Create a local rtl/ directory that the rewritten Makefile will use
    rtl_dir = work_dir / "rtl"
    rtl_dir.mkdir(exist_ok=True)

    # Copy candidate files into rtl/
    for cand in resolved_candidates:
        shutil.copy2(cand, rtl_dir / cand.name)

    # Copy gold RTL deps (sub-modules the candidate isn't replacing)
    gold_rtl_dir = task.root / str(oracle_meta.get("gold_rtl_dir", "oracle/rtl"))
    if gold_rtl_dir.is_dir():
        for f in sorted(gold_rtl_dir.iterdir()):
            dest = rtl_dir / f.name
            if not dest.exists() and f.suffix in {".v", ".sv"}:
                shutil.copy2(f, dest)

    # Rewrite Makefile: ../../rtl/ → ./rtl/, force WAVES=0, strip FST plusarg
    makefile_path = work_dir / "Makefile"
    if makefile_path.exists():
        text = makefile_path.read_text()
        text = text.replace("../../rtl/", "./rtl/")
        text = re.sub(r"^WAVES\s*\?=\s*\d+", "WAVES := 0", text, flags=re.MULTILINE)
        # Remove -fst plusarg (crashes when iverilog lacks zlib)
        text = re.sub(r"PLUSARGS\s*\+=\s*-fst\b", "", text)
        text = re.sub(r"COCOTB_PLUSARGS\s*\+=\s*-fst\b", "", text)
        makefile_path.write_text(text)

    # Clean any stale build artifacts
    for d in ("sim_build", "obj_dir", "__pycache__"):
        stale = work_dir / d
        if stale.exists():
            shutil.rmtree(stale)

    plan = SimulationPlan(
        task=task,
        source_files=tuple(resolved_candidates),
        work_dir=work_dir,
        log_path=work_dir / "sim.log",
        preferred_simulator="cocotb+icarus",
    )

    env = {**subprocess.os.environ, "SIM": "icarus", "WAVES": "0"}
    env.pop("PLUSARGS", None)

    try:
        completed = subprocess.run(
            ("make",),
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="cocotb+icarus",
            plan=plan,
            command=("make",),
            returncode=-9,
            passed=False,
            stdout="",
            stderr="TIMEOUT",
        )

    output = completed.stdout + completed.stderr
    passed = _judge_cocotb(completed.returncode, output)

    return SimulationRunResult(
        simulator="cocotb+icarus",
        plan=plan,
        command=("make",),
        returncode=completed.returncode,
        passed=passed,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _judge_cocotb(returncode: int, output_text: str) -> bool:
    if returncode != 0:
        return False
    match = _COCOTB_PASS_RE.search(output_text)
    if match is None:
        return False
    total = int(match.group(1))
    passed = int(match.group(2))
    failed = int(match.group(3))
    return total > 0 and passed == total and failed == 0
