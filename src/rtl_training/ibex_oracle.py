"""Oracle for Ibex tasks. Tries circt-lec first, falls back to sv2v+eqy."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .oracle import SimulationPlan, SimulationRunResult

# Tool paths
SV2V_BIN = "/tmp/sv2v-linux/sv2v-Linux/sv2v"
EQY_BIN = "/opt/yosys-oss/bin/eqy"
YOSYS_DIR = "/opt/yosys-oss/bin"
CIRCT_VERILOG_BIN = os.path.expanduser(
    "~/circt-worktrees/aot-resume-sv-20260329/build-cwd-local/bin/circt-verilog"
)
CIRCT_LEC_BIN = os.path.expanduser(
    "~/circt-worktrees/circt-formal-real-20260331/build-circt/bin/circt-lec"
)
Z3_BIN = os.path.expanduser("~/.local/bin/z3")

# Include dirs for ibex dependencies
_SHARED = Path(os.path.expanduser(
    "~/rtl/data/shared_sources/bundles/opentitan_ip_docs-d6c1f630c1c8"
))
PRIM_DIR = str(_SHARED / "hw/ip/prim/rtl")
FCOV_DIR = str(_SHARED / "hw/dv/sv/dv_utils")
IBEX_PKG = str(_SHARED / "hw/vendor/lowrisc_ibex/rtl/ibex_pkg.sv")


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
        log_path=work_dir / "eval.log", preferred_simulator="lec",
    )

    # Try circt-lec first (better SV support), fall back to sv2v+eqy
    if _circt_available():
        result = _try_circt_lec(
            golden_file, candidates, module_name, work_dir, plan, timeout_s,
        )
        if result is not None:
            return result

    return _try_eqy(
        golden_file, candidates, module_name, deps_dir, work_dir, plan, timeout_s,
    )


def _circt_available():
    return (
        Path(CIRCT_VERILOG_BIN).is_file()
        and Path(CIRCT_LEC_BIN).is_file()
        and Path(Z3_BIN).is_file()
    )


def _try_circt_lec(golden_file, candidates, module_name, work_dir, plan, timeout_s):
    """Try circt-verilog -> circt-lec --emit-smtlib -> z3. Returns None on tool error."""
    include_flags = [f"-I{PRIM_DIR}", f"-I{FCOV_DIR}"]

    # Convert gold SV -> MLIR
    gold_mlir = work_dir / "gold.mlir"
    cmd = [CIRCT_VERILOG_BIN, "--ir-hw", *include_flags, IBEX_PKG, str(golden_file)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return None
    gold_mlir.write_text(r.stdout)

    # Convert candidate SV -> MLIR
    candidate_code = "\n".join(c.read_text() for c in candidates)
    candidate_sv = work_dir / "candidate.sv"
    candidate_sv.write_text(candidate_code)

    gate_mlir = work_dir / "gate.mlir"
    cmd = [CIRCT_VERILOG_BIN, "--ir-hw", *include_flags, IBEX_PKG, str(candidate_sv)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        return SimulationRunResult(
            simulator="circt-verilog", plan=plan, command=tuple(cmd),
            returncode=r.returncode, passed=False,
            stdout=r.stdout, stderr=r.stderr,
        )
    gate_mlir.write_text(r.stdout)

    # Run circt-lec -> z3
    lec_cmd = [
        CIRCT_LEC_BIN, "--emit-smtlib",
        f"--c1={module_name}", f"--c2={module_name}",
        str(gold_mlir), str(gate_mlir),
    ]
    try:
        lec_proc = subprocess.Popen(
            lec_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        z3_proc = subprocess.Popen(
            [Z3_BIN, "-in"], stdin=lec_proc.stdout, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        lec_proc.stdout.close()
        z3_stdout, z3_stderr = z3_proc.communicate(timeout=timeout_s)
        lec_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        lec_proc.kill()
        z3_proc.kill()
        return None
    except Exception:
        return None

    lec_stderr = lec_proc.stderr.read() if lec_proc.stderr else ""
    lec_proc.stderr.close()

    if lec_proc.returncode != 0 or not z3_stdout.strip():
        # circt-lec failed (unsupported ops, etc.) — fall back to eqy
        return None

    passed = z3_stdout.strip() == "unsat"
    return SimulationRunResult(
        simulator="circt-lec", plan=plan, command=tuple(lec_cmd),
        returncode=0 if passed else 1, passed=passed,
        stdout=z3_stdout, stderr=lec_stderr,
    )


def _try_eqy(golden_file, candidates, module_name, deps_dir, work_dir, plan, timeout_s):
    """Fall back to sv2v + eqy equivalence checking."""
    dep_files = sorted(deps_dir.glob("*.sv")) if deps_dir.is_dir() else []
    include_dirs = [str(deps_dir)] if deps_dir.is_dir() else []
    sv2v_includes = [f"-I{d}" for d in include_dirs]

    def _sv2v(src_path, out_path):
        cmd = [
            SV2V_BIN, "-D", "SYNTHESIS", *sv2v_includes,
            *[str(f) for f in dep_files], str(src_path),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        except subprocess.TimeoutExpired:
            return SimulationRunResult(
                simulator="sv2v", plan=plan, command=tuple(cmd),
                returncode=-9, passed=False, stdout="", stderr="SV2V TIMEOUT",
            )
        if r.returncode != 0 or not r.stdout.strip():
            return SimulationRunResult(
                simulator="sv2v", plan=plan, command=tuple(cmd),
                returncode=r.returncode, passed=False,
                stdout=r.stdout, stderr=r.stderr,
            )
        out_path.write_text(r.stdout)
        return None

    # Convert gold
    gold_v = work_dir / "gold.v"
    err = _sv2v(golden_file, gold_v)
    if err:
        return err

    # Convert candidate
    candidate_code = "\n".join(c.read_text() for c in candidates)
    candidate_sv = work_dir / "candidate.sv"
    candidate_sv.write_text(candidate_code)
    gate_v = work_dir / "gate.v"
    err = _sv2v(candidate_sv, gate_v)
    if err:
        return err

    # Run eqy
    eqy_cfg = work_dir / "equiv.eqy"
    eqy_cfg.write_text(
        f"[gold]\nread_verilog gold.v\nprep -top {module_name}\n\n"
        f"[gate]\nread_verilog gate.v\nprep -top {module_name}\n\n"
        f"[strategy sat]\nuse sat\ndepth 10\n\n"
        f"[strategy formal]\nuse sby\ndepth 10\n"
    )

    env = dict(os.environ)
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
