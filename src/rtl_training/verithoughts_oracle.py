"""Oracle for VeriThoughts tasks. Direct eqy equivalence between candidate and golden."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .oracle import SimulationPlan, SimulationRunResult


def validate_candidate(task, candidate_rtl_paths, *, work_root, timeout_s=120):
    oracle_meta = task.metadata.get("oracle", {})

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

    golden_file = task.root / str(oracle_meta.get("golden_file", "oracle/golden.v"))
    golden_text = golden_file.read_text()
    mod_match = re.search(r"module\s+(\w+)", golden_text)
    mod_name = mod_match.group(1) if mod_match else "top"

    golden_dest = work_dir / "golden.v"
    shutil.copy2(golden_file, golden_dest)
    candidate_dest = work_dir / "candidate.v"
    candidate_dest.write_text("\n".join(c.read_text() for c in candidates))

    plan = SimulationPlan(
        task=task, source_files=tuple(candidates), work_dir=work_dir,
        log_path=work_dir / "eval.log", preferred_simulator="eqy",
    )

    # Direct eqy comparison
    eqy_cfg = work_dir / "equiv.eqy"
    eqy_cfg.write_text(
        f"[gold]\nread_verilog -sv {golden_dest}\nprep -top {mod_name}\n\n"
        f"[gate]\nread_verilog -sv {candidate_dest}\nprep -top {mod_name}\n\n"
        f"[strategy sat]\nuse sat\ndepth 10\n"
    )

    eqy_cmd = ("eqy", "-f", str(eqy_cfg))
    try:
        result = subprocess.run(
            eqy_cmd, cwd=work_dir, capture_output=True, text=True,
            timeout=timeout_s, check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="eqy", plan=plan, command=eqy_cmd,
            returncode=-9, passed=False, stdout="", stderr="EQY TIMEOUT",
        )

    output = result.stdout + result.stderr
    passed = result.returncode == 0 and "PASS" in output

    return SimulationRunResult(
        simulator="eqy", plan=plan, command=eqy_cmd,
        returncode=result.returncode, passed=passed,
        stdout=result.stdout, stderr=result.stderr,
    )
