"""Oracle for VeeR EL2 block-level cocotb+pyuvm tests with verilator."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .oracle import SimulationPlan, SimulationRunResult, _COCOTB_PASS_RE


def validate_candidate(task, candidate_rtl_paths, *, work_root, timeout_s=300):
    oracle_meta = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "veer_cocotb":
        raise ValueError(f"task {task.task_id} is not a veer_cocotb oracle")

    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        candidate_rtl_paths = sorted(
            f for f in (p.iterdir() if p.is_dir() else [p]) if f.suffix in {".sv", ".v"}
        )
    candidates = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "veer_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    oracle_dir = task.root / "oracle"
    shutil.copytree(oracle_dir, work_dir)

    test_subdir = work_dir / "test"

    # Fix Makefile paths (oracle layout differs from original repo layout)
    test_mk = test_subdir / "Makefile"
    if test_mk.exists():
        mk = test_mk.read_text()
        mk = mk.replace("$(abspath $(TEST_DIR)/../../design)", "$(abspath $(TEST_DIR)/../design)")
        mk = mk.replace("$(abspath $(TEST_DIR)../../../../design)", "$(abspath $(TEST_DIR)/../design)")
        test_mk.write_text(mk)

    common_mk = work_dir / "common.mk"
    if common_mk.exists():
        mk = common_mk.read_text()
        mk = mk.replace("$(abspath $(CURDIR)/../../configs)", "$(abspath $(CURDIR)/configs)")
        mk = mk.replace("PYTHONPATH := $(CURDIR)/common", "PYTHONPATH := $(CURDIR)/../common")
        common_mk.write_text(mk)

    # Clean stale build artifacts
    for stale in ("sim-build", "sim_build", "__pycache__", "results.xml"):
        p = test_subdir / stale
        if p.exists():
            shutil.rmtree(p) if p.is_dir() else p.unlink()

    # Replace DUT source with candidate
    design_dir = work_dir / "design"
    for cand in candidates:
        dest = design_dir / cand.name
        if not dest.parent.exists():
            dest.parent.mkdir(parents=True)
        shutil.copy2(cand, dest)
        for sub in design_dir.rglob("*.sv"):
            if sub.name == cand.name and sub != dest:
                shutil.copy2(cand, sub)

    plan = SimulationPlan(
        task=task, source_files=tuple(candidates), work_dir=test_subdir,
        log_path=test_subdir / "sim.log", preferred_simulator="verilator",
    )

    env = {**subprocess.os.environ, "SIM": "verilator", "WAVES": "0"}

    try:
        completed = subprocess.run(
            ("make",), cwd=test_subdir, capture_output=True, text=True,
            timeout=timeout_s, check=False, env=env,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="verilator", plan=plan, command=("make",),
            returncode=-9, passed=False, stdout="", stderr="TIMEOUT",
        )

    output = completed.stdout + completed.stderr
    match = _COCOTB_PASS_RE.search(output)
    passed = match is not None and int(match.group(1)) > 0 and int(match.group(2)) == int(match.group(1)) and int(match.group(3)) == 0

    return SimulationRunResult(
        simulator="verilator", plan=plan, command=("make",),
        returncode=completed.returncode, passed=passed,
        stdout=completed.stdout, stderr=completed.stderr,
    )
