"""Oracle for NotSoTiny tasks. Syntax check (iverilog) + equivalence (eqy)."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .oracle import SimulationPlan, SimulationRunResult


def validate_candidate(task, candidate_rtl_paths, *, work_root, timeout_s=120):
    oracle_meta = task.metadata.get("oracle", {})
    if oracle_meta.get("kind") != "notsotiny_equiv":
        raise ValueError(f"task {task.task_id} is not a notsotiny_equiv oracle")

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

    context_file = task.root / str(oracle_meta["context_file"])
    golden_file = task.root / str(oracle_meta["golden_file"])
    task_module = str(oracle_meta["task_module"])

    context_text = context_file.read_text()
    candidate_code = "\n".join(c.read_text() for c in candidates)
    golden_text = golden_file.read_text()

    # Extract actual Verilog module name from golden (may differ from task_module)
    verilog_mod_match = re.search(r"module\s+(\w+)", golden_text)
    verilog_module_name = verilog_mod_match.group(1) if verilog_mod_match else task_module

    # Replace the stub module in context with the candidate
    module_pattern = re.compile(
        r"module\s+" + re.escape(verilog_module_name) + r"\b.*?endmodule",
        re.DOTALL,
    )
    if module_pattern.search(context_text):
        full_text = module_pattern.sub(candidate_code, context_text, count=1)
    else:
        full_text = context_text + "\n" + candidate_code

    full_project = work_dir / "full_project.v"
    full_project.write_text(full_text)
    golden_dest = work_dir / "golden.v"
    shutil.copy2(golden_file, golden_dest)
    candidate_dest = work_dir / "candidate.v"
    candidate_dest.write_text(candidate_code)

    plan = SimulationPlan(
        task=task, source_files=tuple(candidates), work_dir=work_dir,
        log_path=work_dir / "eval.log", preferred_simulator="iverilog",
    )

    # Step 1: Syntax check
    syntax_cmd = ("iverilog", "-g2012", "-o", "/dev/null", str(full_project))
    try:
        syntax_result = subprocess.run(
            syntax_cmd, cwd=work_dir, capture_output=True, text=True, timeout=30, check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="iverilog", plan=plan, command=syntax_cmd,
            returncode=-9, passed=False, stdout="", stderr="SYNTAX TIMEOUT",
        )

    if syntax_result.returncode != 0:
        return SimulationRunResult(
            simulator="iverilog", plan=plan, command=syntax_cmd,
            returncode=syntax_result.returncode, passed=False,
            stdout=syntax_result.stdout, stderr=syntax_result.stderr,
        )

    # Step 2: Equivalence check with eqy
    eqy_cfg = work_dir / "equiv.eqy"
    eqy_cfg.write_text(
        f"[gold]\nread_verilog -sv {golden_dest}\nprep -top {verilog_module_name}\n\n"
        f"[gate]\nread_verilog -sv {candidate_dest}\nprep -top {verilog_module_name}\n\n"
        f"[strategy sat]\nuse sat\ndepth 10\n"
    )

    eqy_cmd = ("eqy", "-f", str(eqy_cfg))
    try:
        eqy_result = subprocess.run(
            eqy_cmd, cwd=work_dir, capture_output=True, text=True,
            timeout=timeout_s, check=False,
        )
    except subprocess.TimeoutExpired:
        # Syntax passed, eqy timed out — count as syntax-only pass
        return SimulationRunResult(
            simulator="eqy", plan=plan, command=eqy_cmd,
            returncode=-9, passed=False, stdout="", stderr="EQY TIMEOUT (syntax passed)",
        )

    output = eqy_result.stdout + eqy_result.stderr
    passed = eqy_result.returncode == 0 and "PASS" in output

    return SimulationRunResult(
        simulator="eqy", plan=plan, command=eqy_cmd,
        returncode=eqy_result.returncode, passed=passed,
        stdout=eqy_result.stdout, stderr=eqy_result.stderr,
    )
