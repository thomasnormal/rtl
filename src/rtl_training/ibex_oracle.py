"""Oracle for Ibex tasks. sv2v conversion + eqy equivalence checking."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .oracle import SimulationPlan, SimulationRunResult

SV2V_BIN = "/tmp/sv2v-linux/sv2v-Linux/sv2v"
EQY_BIN = "/opt/yosys-oss/bin/eqy"
YOSYS_DIR = "/opt/yosys-oss/bin"


def validate_candidate(task, candidate_rtl_paths, *, work_root, timeout_s=120):
    oracle_meta = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "ibex_eqy":
        raise ValueError(f"task {task.task_id} is not an ibex_eqy oracle")

    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        candidate_rtl_paths = [p] if p.is_file() else sorted(
            f for f in p.iterdir() if f.suffix in {".sv", ".v"}
        )
    candidates = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "equiv_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    golden_file = task.root / str(oracle_meta["golden_file"])
    deps_dir = task.root / str(oracle_meta.get("deps_dir", "oracle/deps"))
    module_name = str(oracle_meta["module"])

    plan = SimulationPlan(
        task=task, source_files=tuple(candidates), work_dir=work_dir,
        log_path=work_dir / "eval.log", preferred_simulator="eqy",
    )

    # Collect dependency files (ibex_pkg.sv, include dirs)
    dep_files = sorted(deps_dir.glob("*.sv")) if deps_dir.is_dir() else []
    include_dirs = [str(deps_dir)] if deps_dir.is_dir() else []
    sv2v_includes = [f"-I{d}" for d in include_dirs]

    # Step 1: sv2v conversion of gold
    gold_v = work_dir / "gold.v"
    sv2v_gold_cmd = [
        SV2V_BIN, "-D", "SYNTHESIS",
        *sv2v_includes,
        *[str(f) for f in dep_files],
        str(golden_file),
    ]
    try:
        sv2v_result = subprocess.run(
            sv2v_gold_cmd, capture_output=True, text=True, timeout=30, check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="sv2v", plan=plan, command=tuple(sv2v_gold_cmd),
            returncode=-9, passed=False, stdout="", stderr="SV2V GOLD TIMEOUT",
        )
    if sv2v_result.returncode != 0 or not sv2v_result.stdout.strip():
        return SimulationRunResult(
            simulator="sv2v", plan=plan, command=tuple(sv2v_gold_cmd),
            returncode=sv2v_result.returncode, passed=False,
            stdout=sv2v_result.stdout, stderr=sv2v_result.stderr,
        )
    gold_v.write_text(sv2v_result.stdout)

    # Step 2: sv2v conversion of candidate
    candidate_code = "\n".join(c.read_text() for c in candidates)
    candidate_sv = work_dir / "candidate.sv"
    candidate_sv.write_text(candidate_code)

    gate_v = work_dir / "gate.v"
    sv2v_gate_cmd = [
        SV2V_BIN, "-D", "SYNTHESIS",
        *sv2v_includes,
        *[str(f) for f in dep_files],
        str(candidate_sv),
    ]
    try:
        sv2v_result = subprocess.run(
            sv2v_gate_cmd, capture_output=True, text=True, timeout=30, check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="sv2v", plan=plan, command=tuple(sv2v_gate_cmd),
            returncode=-9, passed=False, stdout="", stderr="SV2V CANDIDATE TIMEOUT",
        )
    if sv2v_result.returncode != 0 or not sv2v_result.stdout.strip():
        return SimulationRunResult(
            simulator="sv2v", plan=plan, command=tuple(sv2v_gate_cmd),
            returncode=sv2v_result.returncode, passed=False,
            stdout=sv2v_result.stdout, stderr=sv2v_result.stderr,
        )
    gate_v.write_text(sv2v_result.stdout)

    # Step 3: eqy equivalence check
    eqy_cfg = work_dir / "equiv.eqy"
    eqy_cfg.write_text(
        f"[gold]\nread_verilog gold.v\nprep -top {module_name}\n\n"
        f"[gate]\nread_verilog gate.v\nprep -top {module_name}\n\n"
        f"[strategy sat]\nuse sat\ndepth 10\n\n"
        f"[strategy formal]\nuse sby\ndepth 10\n"
    )

    env = dict(__import__("os").environ)
    env["PATH"] = f"{YOSYS_DIR}:{env.get('PATH', '')}"

    eqy_cmd = (EQY_BIN, "-f", str(eqy_cfg))
    try:
        eqy_result = subprocess.run(
            eqy_cmd, cwd=work_dir, capture_output=True, text=True,
            timeout=timeout_s, check=False, env=env,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="eqy", plan=plan, command=eqy_cmd,
            returncode=-9, passed=False, stdout="", stderr="EQY TIMEOUT",
        )

    output = eqy_result.stdout + eqy_result.stderr
    passed = eqy_result.returncode == 0 and "PASS" in output

    return SimulationRunResult(
        simulator="eqy", plan=plan, command=eqy_cmd,
        returncode=eqy_result.returncode, passed=passed,
        stdout=eqy_result.stdout, stderr=eqy_result.stderr,
    )
