"""Oracle for NotSoTiny tasks (TuRTLe benchmark).

Each task provides a full Verilog project with one module removed.
The candidate replaces the missing module.  The oracle checks:
1. Syntax: ``iverilog`` compilation of the full project + candidate
2. Equivalence: ``eqy`` (Yosys) comparing candidate module vs golden module
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from rtl_training.oracle import SimulationPlan, SimulationRunResult


def validate_candidate(
    task,  # StoredTask
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    timeout_s: int = 120,
) -> SimulationRunResult:
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

    # Get the project context (everything except the missing module)
    context_file = task.root / str(oracle_meta["context_file"])
    golden_file = task.root / str(oracle_meta["golden_file"])
    task_module = str(oracle_meta["task_module"])

    # Write the full project: replace the marker in context with candidate code
    context_text = context_file.read_text()
    candidate_code = "\n".join(c.read_text() for c in candidates)

    # The context has the target module as a stub with markers:
    #   module <name>(...);
    #   // >>> Module Implementation Begin
    #   // <<< Module Implementation End
    #   endmodule
    # The candidate is a complete module (with header + endmodule).
    # Replace the entire stub module with the candidate.
    #
    # Extract the actual Verilog module name from the golden file
    # (task_module may be a task name like "task_alu", not the Verilog name "alu")
    import re as _re
    golden_text = golden_file.read_text()
    verilog_mod_match = _re.search(r"module\s+(\w+)", golden_text)
    verilog_module_name = verilog_mod_match.group(1) if verilog_mod_match else task_module

    module_pattern = _re.compile(
        r"module\s+" + _re.escape(verilog_module_name) + r"\b.*?endmodule",
        _re.DOTALL,
    )
    if module_pattern.search(context_text):
        full_text = module_pattern.sub(candidate_code, context_text, count=1)
    else:
        # Fallback: just concatenate
        full_text = context_text + "\n" + candidate_code

    full_project = work_dir / "full_project.v"
    full_project.write_text(full_text)

    # Write golden for equivalence
    golden_dest = work_dir / "golden.v"
    shutil.copy2(golden_file, golden_dest)

    # Write candidate module standalone
    candidate_dest = work_dir / "candidate.v"
    candidate_dest.write_text(candidate_code)

    plan = SimulationPlan(
        task=task,
        source_files=tuple(candidates),
        work_dir=work_dir,
        log_path=work_dir / "eval.log",
        preferred_simulator="iverilog",
    )

    # Step 1: Syntax check with iverilog
    syntax_cmd = ("iverilog", "-g2012", "-o", "/dev/null", str(full_project))
    try:
        syntax_result = subprocess.run(
            syntax_cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="iverilog",
            plan=plan,
            command=syntax_cmd,
            returncode=-9,
            passed=False,
            stdout="",
            stderr="SYNTAX CHECK TIMEOUT",
        )

    if syntax_result.returncode != 0:
        return SimulationRunResult(
            simulator="iverilog",
            plan=plan,
            command=syntax_cmd,
            returncode=syntax_result.returncode,
            passed=False,
            stdout=syntax_result.stdout,
            stderr=syntax_result.stderr,
        )

    # Step 2: Equivalence check with eqy (yosys)
    # Write eqy config
    eqy_cfg = work_dir / "equiv.eqy"
    eqy_cfg.write_text(f"""[gold]
read_verilog -sv {golden_dest}
prep -top {verilog_module_name}

[gate]
read_verilog -sv {candidate_dest}
prep -top {verilog_module_name}

[strategy sat]
use sat
depth 10
""")

    eqy_cmd = ("eqy", "-f", str(eqy_cfg))
    try:
        eqy_result = subprocess.run(
            eqy_cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SimulationRunResult(
            simulator="eqy",
            plan=plan,
            command=eqy_cmd,
            returncode=-9,
            passed=False,
            stdout="",
            stderr="EQY TIMEOUT",
        )

    output = eqy_result.stdout + eqy_result.stderr
    passed = eqy_result.returncode == 0 and "PASS" in output

    return SimulationRunResult(
        simulator="eqy",
        plan=plan,
        command=eqy_cmd,
        returncode=eqy_result.returncode,
        passed=passed,
        stdout=eqy_result.stdout,
        stderr=eqy_result.stderr,
    )
