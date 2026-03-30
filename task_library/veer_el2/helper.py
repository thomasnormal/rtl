"""Oracle for VeeR EL2 RISC-V block-level cocotb tests.

VeeR block tests use cocotb 1.8 + pyuvm with verilator. The oracle
copies the test directory and supporting infrastructure, replaces the
DUT source, and runs ``make SIM=verilator WAVES=0``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from rtl_training.oracle import SimulationPlan, SimulationRunResult, _COCOTB_PASS_RE


def validate_candidate(
    task,  # StoredTask
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    timeout_s: int = 300,
) -> SimulationRunResult:
    oracle_meta = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "veer_cocotb":
        raise ValueError(f"task {task.task_id} is not a veer_cocotb oracle")

    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        candidate_rtl_paths = sorted(
            f for f in (p.iterdir() if p.is_dir() else [p])
            if f.suffix in {".sv", ".v"}
        )
    candidates = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "veer_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    # Copy the oracle directory tree (test dir + common + snapshots + design deps)
    oracle_dir = task.root / "oracle"
    shutil.copytree(oracle_dir, work_dir)

    # Fix paths in the test Makefile: SRCDIR points ../../design relative
    # to the original verification/block/<test>/ layout, but our oracle
    # stores it at oracle/design/ (one level up from oracle/test/).
    test_subdir = work_dir / "test"
    test_mk = test_subdir / "Makefile"
    if test_mk.exists():
        mk_text = test_mk.read_text()
        mk_text = mk_text.replace(
            "$(abspath $(TEST_DIR)/../../design)",
            "$(abspath $(TEST_DIR)/../design)",
        )
        # Also fix the original four-level path if present
        mk_text = mk_text.replace(
            "$(abspath $(TEST_DIR)../../../../design)",
            "$(abspath $(TEST_DIR)/../design)",
        )
        test_mk.write_text(mk_text)

    # Fix common.mk paths: configs and common python dir
    common_mk = work_dir / "common.mk"
    if common_mk.exists():
        mk_text = common_mk.read_text()
        mk_text = mk_text.replace(
            "$(abspath $(CURDIR)/../../configs)",
            "$(abspath $(CURDIR)/configs)",
        )
        # PYTHONPATH for common test modules
        mk_text = mk_text.replace(
            "PYTHONPATH := $(CURDIR)/common",
            "PYTHONPATH := $(CURDIR)/../common",
        )
        common_mk.write_text(mk_text)

    # Clean stale build artifacts
    for stale in ("sim-build", "sim_build", "__pycache__", "results.xml"):
        p = test_subdir / stale
        if p.exists():
            shutil.rmtree(p) if p.is_dir() else p.unlink()

    # Replace DUT source with candidate
    design_dir = work_dir / "design"
    for cand in candidates:
        # Find the right subdirectory in design/
        # Try flat first, then search subdirs
        dest = design_dir / cand.name
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True)
        shutil.copy2(cand, dest)
        # Also copy into subdirectories that might reference it
        for subdir in design_dir.rglob("*.sv"):
            if subdir.name == cand.name and subdir != dest:
                shutil.copy2(cand, subdir)

    plan = SimulationPlan(
        task=task,
        source_files=tuple(candidates),
        work_dir=test_subdir,
        log_path=test_subdir / "sim.log",
        preferred_simulator="verilator",
    )

    env = {
        **subprocess.os.environ,
        "SIM": "verilator",
        "WAVES": "0",
    }

    try:
        completed = subprocess.run(
            ("make",),
            cwd=test_subdir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="verilator",
            plan=plan,
            command=("make",),
            returncode=-9,
            passed=False,
            stdout="",
            stderr="TIMEOUT",
        )

    output = completed.stdout + completed.stderr
    match = _COCOTB_PASS_RE.search(output)
    passed = (
        match is not None
        and int(match.group(1)) > 0
        and int(match.group(2)) == int(match.group(1))
        and int(match.group(3)) == 0
    )

    return SimulationRunResult(
        simulator="verilator",
        plan=plan,
        command=("make",),
        returncode=completed.returncode,
        passed=passed,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
