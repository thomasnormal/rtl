"""Oracle for CVDP-style cocotb tasks.

Parses CVDP ``test_runner.py`` to extract HDL parameters and iteration
counts, then drives ``iverilog`` + ``vvp`` + cocotb directly (bypassing
``cocotb_tools.runner`` which drops env vars).

Requires ``cocotb``, ``iverilog``, and ``vvp`` to be installed.
"""

from __future__ import annotations

import ast
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import Any, Sequence

from rtl_training.oracle import SimulationPlan, SimulationRunResult, _COCOTB_PASS_RE
from rtl_training.task_store import StoredTask


# ---------------------------------------------------------------------------
# cocotb harness helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CocotbRunConfig:
    """One compile+simulate invocation."""
    hdl_parameters: dict[str, int]
    plusargs: tuple[str, ...]


_PLUSARG_NAME_RE = re.compile(r"""\+(\w+)=""")


def parse_test_runner(runner_path: Path) -> list[CocotbRunConfig]:
    """Extract run configurations from a CVDP test_runner.py.

    Returns one :class:`CocotbRunConfig` per simulation invocation that the
    original ``pytest`` parametrization would produce.
    """
    source = runner_path.read_text()
    configs: list[CocotbRunConfig] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [CocotbRunConfig(hdl_parameters={}, plusargs=())]

    # Collect parametrize axes and HDL parameter names
    param_axes: dict[str, list[Any]] = {}
    hdl_param_names: list[str] = []
    has_plusargs = "plusargs" in source.lower()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "parametrize"
                and len(node.args) >= 2
            ):
                name_node = node.args[0]
                vals_node = node.args[1]
                if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str):
                    param_name = name_node.value
                    values = _eval_param_values(vals_node, source)
                    if values is not None:
                        param_axes[param_name] = values

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "build":
                for kw in node.keywords:
                    if kw.arg == "parameters" and isinstance(kw.value, ast.Name):
                        hdl_param_names.append(kw.value.id)
                    elif kw.arg == "parameters" and isinstance(kw.value, ast.Dict):
                        for key in kw.value.keys:
                            if isinstance(key, ast.Constant):
                                hdl_param_names.append(str(key.value))

    # Separate HDL parameters from iteration axes
    hdl_axes: dict[str, list[int]] = {}
    iteration_count = 1

    for name, values in param_axes.items():
        if name == "test":
            iteration_count = max(len(values), 1)
        elif name in hdl_param_names or _looks_like_hdl_param(name):
            hdl_axes[name] = [int(v) for v in values if _is_int(v)]
        else:
            if all(_is_int(v) for v in values):
                hdl_axes[name] = [int(v) for v in values]
            else:
                iteration_count *= max(len(values), 1)

    # Extract plusarg names from f-string patterns like f'+encoder_in={encoder_in}'
    plusarg_names: list[str] = []
    if has_plusargs:
        plusarg_names = _PLUSARG_NAME_RE.findall(source)

    hdl_combos = _cross_product(hdl_axes) if hdl_axes else [{}]
    effective_iterations = max(iteration_count, 1)

    for combo in hdl_combos:
        for _ in range(effective_iterations):
            # Generate random plusargs for each iteration
            plus = tuple(f"+{name}={random.randint(0, 255)}" for name in plusarg_names)
            configs.append(CocotbRunConfig(
                hdl_parameters=dict(combo),
                plusargs=plus,
            ))

    return configs if configs else [CocotbRunConfig(hdl_parameters={}, plusargs=())]


def _eval_param_values(node: ast.expr, source: str) -> list[Any] | None:
    """Try to evaluate a parametrize values node."""
    try:
        code = ast.get_source_segment(source, node)
        if code is None:
            return None
        # Safe-ish eval for simple expressions like range(10), [4,5], etc.
        val = eval(code, {"range": range, "random": random, "__builtins__": {}})
        return list(val)
    except Exception:
        return None


def _is_int(v: Any) -> bool:
    return isinstance(v, int) or (isinstance(v, str) and v.isdigit())


def _looks_like_hdl_param(name: str) -> bool:
    return name.upper() == name or name in {
        "WIDTH", "DEPTH", "N", "DATA_WIDTH", "ADDR_WIDTH", "STAGES",
        "CLK_DIV", "ARRAY_SIZE", "NUM_CHANNELS",
    }


def _cross_product(axes: dict[str, list[int]]) -> list[dict[str, int]]:
    if not axes:
        return [{}]
    keys = list(axes.keys())
    result: list[dict[str, int]] = [{}]
    for key in keys:
        new_result = []
        for combo in result:
            for val in axes[key]:
                new_combo = dict(combo)
                new_combo[key] = val
                new_result.append(new_combo)
        result = new_result
    return result


_INPUT_PORT_RE = re.compile(
    r"^\s*input\s+(?:wire|logic|reg)?\s*(?:signed\s*)?"
    r"(?:\[[^\]]*\]\s*)?(\w+)",
    re.MULTILINE,
)


def _write_iverilog_dump_module(
    dump_file: Path,
    toplevel: str,
    candidate_paths: Sequence[Path],
) -> None:
    """Write a helper module that exposes VPI signals and zeros inputs."""
    input_names: list[str] = []
    for p in candidate_paths:
        if p.is_file():
            text = p.read_text()
            input_names.extend(_INPUT_PORT_RE.findall(text))
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique_inputs: list[str] = []
    for name in input_names:
        if name not in seen:
            seen.add(name)
            unique_inputs.append(name)

    deposit_lines = "\n".join(
        f"        $deposit({toplevel}.{name}, 0);"
        for name in unique_inputs
    )
    dump_file.write_text(
        f"module cocotb_iverilog_dump();\n"
        f"initial begin\n"
        f"    $dumpvars(0, {toplevel});\n"
        f"    #0;\n"
        f"{deposit_lines}\n"
        f"end\n"
        f"endmodule\n"
    )


def compile_cocotb(
    *,
    candidate_paths: Sequence[Path],
    toplevel: str,
    work_dir: Path,
    hdl_parameters: dict[str, int] | None = None,
    timeout_s: int = 60,
) -> tuple[Path | None, subprocess.CompletedProcess[str]]:
    """Compile candidate RTL with iverilog. Returns (vvp_path, result)."""
    suffix = "_".join(f"{k}{v}" for k, v in sorted((hdl_parameters or {}).items()))
    vvp_name = f"sim_{suffix}.vvp" if suffix else "sim.vvp"
    vvp_path = work_dir / vvp_name

    timescale_stub = work_dir / "_cocotb_timescale.v"
    if not timescale_stub.exists():
        timescale_stub.write_text("`timescale 1ns/1ns\n")

    dump_file = work_dir / "_cocotb_iverilog_dump.v"
    if not dump_file.exists():
        _write_iverilog_dump_module(dump_file, toplevel, candidate_paths)

    param_args: list[str] = []
    for k, v in (hdl_parameters or {}).items():
        param_args.extend(["-P", f"{toplevel}.{k}={v}"])

    cmd = [
        "iverilog",
        "-o", str(vvp_path),
        "-s", toplevel,
        "-s", "cocotb_iverilog_dump",
        "-g2012",
        *param_args,
        str(timescale_stub),
        str(dump_file),
        *[str(p) for p in candidate_paths],
    ]
    result = subprocess.run(
        cmd, cwd=work_dir, capture_output=True, text=True,
        timeout=timeout_s, check=False,
    )
    if result.returncode != 0:
        return None, result
    return vvp_path, result


def run_cocotb_sim(
    *,
    vvp_path: Path,
    test_module: str,
    toplevel: str,
    work_dir: Path,
    plusargs: Sequence[str] = (),
    run_index: int = 0,
    timeout_s: int = 60,
) -> subprocess.CompletedProcess[str]:
    """Run a single cocotb simulation via vvp."""
    import cocotb as _cocotb
    cocotb_lib_dir = str(Path(_cocotb.__path__[0]) / "libs")

    env = os.environ.copy()
    env.update({
        "COCOTB_TEST_MODULES": test_module,
        "TOPLEVEL": toplevel,
        "TOPLEVEL_LANG": "verilog",
        "PYGPI_PYTHON_BIN": sys.executable,
        "PYTHONPATH": str(work_dir),
        "COCOTB_RESULTS_FILE": str(work_dir / f"results_{run_index}.xml"),
    })

    cmd = [
        "vvp",
        "-M", cocotb_lib_dir,
        "-m", "libcocotbvpi_icarus",
        str(vvp_path),
        *plusargs,
    ]
    return subprocess.run(
        cmd, cwd=work_dir, env=env,
        capture_output=True, text=True,
        timeout=timeout_s, check=False,
    )


# ---------------------------------------------------------------------------
# CVDP oracle entry point
# ---------------------------------------------------------------------------

def validate_candidate_cocotb(
    task: StoredTask,
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    timeout_s: int = 120,
) -> SimulationRunResult:
    """Validate candidate RTL using a cocotb testbench."""
    oracle_meta = task.metadata.get("oracle")
    if oracle_meta is None or oracle_meta.get("kind") != "cocotb":
        raise ValueError(f"task {task.task_id} does not have a cocotb oracle")

    # Normalise candidate paths
    if isinstance(candidate_rtl_paths, (str, Path)):
        p = Path(candidate_rtl_paths).resolve()
        if p.is_dir():
            candidate_rtl_paths = sorted(
                f for f in p.iterdir()
                if f.is_file() and f.suffix in {".sv", ".v", ".svh", ".vh"}
            )
        else:
            candidate_rtl_paths = [p]
    resolved_candidates = [Path(p).resolve() for p in candidate_rtl_paths]

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "cocotb_val"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    # Copy oracle test files into work_dir
    oracle_dir = task.root / str(oracle_meta["test_dir"])
    for src_file in sorted(oracle_dir.iterdir()):
        if src_file.is_file():
            shutil.copy2(src_file, work_dir / src_file.name)

    toplevel = str(oracle_meta.get("toplevel", oracle_meta.get("env", {}).get("TOPLEVEL", "")))
    test_module = str(oracle_meta.get("test_module", oracle_meta.get("env", {}).get("MODULE", "")))

    plan = SimulationPlan(
        task=task,
        source_files=tuple(resolved_candidates),
        work_dir=work_dir,
        log_path=work_dir / "sim.log",
        preferred_simulator="icarus",
    )

    # Parse the test_runner to discover HDL parameter combos and iterations
    runner_path = work_dir / "test_runner.py"
    if runner_path.exists():
        run_configs = parse_test_runner(runner_path)
    else:
        run_configs = [CocotbRunConfig(hdl_parameters={}, plusargs=())]

    all_stdout: list[str] = []
    all_stderr: list[str] = []
    total_tests = 0
    total_passed = 0
    total_failed = 0
    last_cmd: tuple[str, ...] = ()
    last_returncode = 0

    # Group runs by HDL parameters (same params = same compilation)
    sorted_configs = sorted(run_configs, key=lambda c: sorted(c.hdl_parameters.items()))
    for param_key, group in groupby(sorted_configs, key=lambda c: tuple(sorted(c.hdl_parameters.items()))):
        hdl_params = dict(param_key)
        runs = list(group)

        vvp_path, compile_result = compile_cocotb(
            candidate_paths=resolved_candidates,
            toplevel=toplevel,
            work_dir=work_dir,
            hdl_parameters=hdl_params if hdl_params else None,
            timeout_s=timeout_s,
        )
        if vvp_path is None:
            return SimulationRunResult(
                simulator="cocotb+icarus",
                plan=plan,
                command=tuple(compile_result.args) if hasattr(compile_result, 'args') else (),
                returncode=compile_result.returncode,
                passed=False,
                stdout=compile_result.stdout,
                stderr=compile_result.stderr,
            )

        for i, run_cfg in enumerate(runs):
            try:
                sim_result = run_cocotb_sim(
                    vvp_path=vvp_path,
                    test_module=test_module,
                    toplevel=toplevel,
                    work_dir=work_dir,
                    plusargs=run_cfg.plusargs,
                    run_index=i,
                    timeout_s=timeout_s,
                )
            except subprocess.TimeoutExpired:
                return SimulationRunResult(
                    simulator="cocotb+icarus",
                    plan=plan,
                    command=("vvp", str(vvp_path)),
                    returncode=-1,
                    passed=False,
                    stdout="\n".join(all_stdout),
                    stderr="timeout",
                )

            last_cmd = tuple(sim_result.args) if hasattr(sim_result, 'args') else ()
            last_returncode = sim_result.returncode
            output = sim_result.stdout + sim_result.stderr
            all_stdout.append(sim_result.stdout)
            all_stderr.append(sim_result.stderr)

            match = _COCOTB_PASS_RE.search(output)
            if match:
                total_tests += int(match.group(1))
                total_passed += int(match.group(2))
                total_failed += int(match.group(3))
            elif sim_result.returncode != 0:
                total_tests += 1
                total_failed += 1

    passed = total_tests > 0 and total_failed == 0 and total_passed == total_tests
    return SimulationRunResult(
        simulator="cocotb+icarus",
        plan=plan,
        command=last_cmd,
        returncode=0 if passed else (last_returncode or 1),
        passed=passed,
        stdout="\n".join(all_stdout),
        stderr="\n".join(all_stderr),
    )
