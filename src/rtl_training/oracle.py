from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess
from typing import Sequence

from .task_store import PassCriteria, StoredTask


@dataclass(frozen=True)
class SimulationPlan:
    task: StoredTask
    source_files: tuple[Path, ...]
    work_dir: Path
    log_path: Path
    preferred_simulator: str | None = None


@dataclass(frozen=True)
class SimulationRunResult:
    simulator: str
    plan: SimulationPlan
    command: tuple[str, ...]
    returncode: int
    passed: bool
    stdout: str
    stderr: str


_XRUN_ERROR_RE = re.compile(r"(?m)^\s*(?:xrun|xmvlog|xmelab|xmsim|xmvhdl|irun)?\s*:?\s*\*E,")


def detect_simulator(preferred: tuple[str, ...] = ("xrun", "iverilog")) -> str:
    for name in preferred:
        if name == "xrun" and shutil.which("xrun"):
            return "xrun"
        if name == "iverilog" and shutil.which("iverilog") and shutil.which("vvp"):
            return "iverilog"
    raise RuntimeError("no supported simulator found; expected xrun or iverilog/vvp")


def build_candidate_validation_plan(
    task: StoredTask,
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    preferred_simulator: str | None = None,
) -> SimulationPlan:
    if task.oracle is None:
        raise ValueError(f"task {task.task_id} has no oracle")

    # Normalise to a list of resolved file paths.
    # A single directory is expanded to all RTL files within it.
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

    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "validation"
    work_dir.mkdir(parents=True, exist_ok=True)

    staged_support = _stage_support_files(task, work_dir)
    # Defines/config files must be compiled before files that reference them.
    # Put them at the front of source_files.
    _DEFINES_NAMES = {"config.v", "e203_defines.v", "sd_defines.v"}
    defines_first = [f for f in staged_support if f.name in _DEFINES_NAMES]
    other_support = [f for f in staged_support if f.name not in _DEFINES_NAMES]
    source_files: list[Path] = [*defines_first]
    source_files.append(_stage_text_input(task.oracle.testbench_path, work_dir, "testbench"))
    source_files.extend(other_support)
    if task.oracle.requires_reference_rtl:
        source_files.append(_stage_text_input(task.oracle.gold_rtl_path, work_dir, "gold_rtl"))

    candidate_dir = work_dir / "candidate_src"
    candidate_dir.mkdir(exist_ok=True)
    for candidate_path in resolved_candidates:
        dest = candidate_dir / candidate_path.name
        shutil.copy2(candidate_path, dest)
        source_files.append(dest)

    # Use caller override > task oracle preference > default
    effective_sim = preferred_simulator or getattr(task.oracle, "preferred_simulator", None)
    log_name = "xrun.log" if (effective_sim or "xrun") == "xrun" else "sim.log"
    return SimulationPlan(
        task=task,
        source_files=tuple(source_files),
        work_dir=work_dir,
        preferred_simulator=effective_sim,
        log_path=work_dir / log_name,
    )


def build_gold_selftest_plan(
    task: StoredTask,
    *,
    work_root: str | Path,
    preferred_simulator: str | None = None,
) -> SimulationPlan:
    if task.oracle is None:
        raise ValueError(f"task {task.task_id} has no oracle")
    if task.oracle.requires_reference_rtl:
        raise ValueError("gold selftest is ambiguous for reference-based oracle tasks")
    work_dir = Path(work_root).resolve() / task.dataset_name / task.task_id / "gold_selftest"
    work_dir.mkdir(parents=True, exist_ok=True)
    staged_testbench_path = _stage_text_input(task.oracle.testbench_path, work_dir, "testbench")
    _stage_support_files(task, work_dir)
    gold_candidate_path = _stage_text_input(task.oracle.gold_rtl_path, work_dir, "gold_rtl")
    if task.oracle.candidate_top_module != task.oracle.reference_top_module:
        gold_candidate_path = work_dir / f"{task.task_id}__gold_candidate{task.oracle.gold_rtl_path.suffix}"
        gold_candidate_path.write_text(
            _rewrite_first_module_name(
                task.oracle.gold_rtl_path.read_text(),
                old_name=task.oracle.reference_top_module,
                new_name=task.oracle.candidate_top_module,
            )
        )
    return SimulationPlan(
        task=task,
        source_files=(staged_testbench_path, gold_candidate_path),
        work_dir=work_dir,
        log_path=work_dir / ("xrun.log" if (preferred_simulator or "xrun") == "xrun" else "sim.log"),
        preferred_simulator=preferred_simulator,
    )


def _rewrite_first_module_name(text: str, *, old_name: str, new_name: str) -> str:
    pattern = re.compile(rf"(\bmodule\s+){re.escape(old_name)}(\b)")
    rewritten, count = pattern.subn(rf"\1{new_name}\2", text, count=1)
    if count != 1:
        raise ValueError(f"unable to rewrite module name {old_name} -> {new_name}")
    return rewritten


def _stage_text_input(source_path: Path, work_dir: Path, stem: str) -> Path:
    destination = work_dir / f"{stem}{source_path.suffix}"
    shutil.copy2(source_path, destination)
    return destination


def _stage_support_files(task: StoredTask, work_dir: Path) -> tuple[Path, ...]:
    if task.oracle is None:
        raise ValueError(f"task {task.task_id} has no oracle")
    staged: list[Path] = []
    for support_file in task.oracle.support_files:
        destination = work_dir / support_file.name
        shutil.copy2(support_file, destination)
        staged.append(destination)
    return tuple(staged)


def judge_simulation_output(*, returncode: int, output_text: str, criteria: PassCriteria) -> bool:
    if returncode != 0:
        return False
    if _XRUN_ERROR_RE.search(output_text):
        return False
    for marker in criteria.failure_markers:
        if marker and marker in output_text:
            return False
    for marker in criteria.success_markers:
        if marker and marker in output_text:
            return True
    if criteria.zero_value_regex is not None:
        match = re.search(criteria.zero_value_regex, output_text)
        if match is None:
            return False
        return int(match.group(criteria.zero_value_group)) == 0
    return True


def run_simulation_plan(
    plan: SimulationPlan,
    *,
    timeout_s: int = 30,
) -> SimulationRunResult:
    if plan.task.oracle is None:
        raise ValueError(f"task {plan.task.task_id} has no oracle")

    simulator = plan.preferred_simulator or detect_simulator()
    plan.work_dir.mkdir(parents=True, exist_ok=True)

    if simulator == "xrun":
        xrun_args: list[str] = [
            "xrun",
            "-64bit",
            "-q",
            "-sv",
            "-l",
            str(plan.log_path),
            "-xmlibdirname",
            str(plan.work_dir / "xcelium.d"),
        ]
        tb_top = getattr(plan.task.oracle, "testbench_top_module", None)
        if tb_top:
            xrun_args.extend(["-top", tb_top])
        xrun_args.extend(str(path) for path in plan.source_files)
        command = tuple(xrun_args)
        completed = subprocess.run(
            command,
            cwd=plan.work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        log_text = plan.log_path.read_text() if plan.log_path.exists() else ""
        output_text = completed.stdout + completed.stderr + log_text
        passed = judge_simulation_output(
            returncode=completed.returncode,
            output_text=output_text,
            criteria=plan.task.oracle.pass_criteria,
        )
        return SimulationRunResult(
            simulator=simulator,
            plan=plan,
            command=command,
            returncode=completed.returncode,
            passed=passed,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    if simulator == "iverilog":
        compile_out = plan.work_dir / "simv"
        compile_cmd = (
            "iverilog",
            "-g2012",
            "-o",
            str(compile_out),
            *[str(path) for path in plan.source_files],
        )
        compiled = subprocess.run(
            compile_cmd,
            cwd=plan.work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if compiled.returncode != 0:
            return SimulationRunResult(
                simulator=simulator,
                plan=plan,
                command=compile_cmd,
                returncode=compiled.returncode,
                passed=False,
                stdout=compiled.stdout,
                stderr=compiled.stderr,
            )
        run_cmd = ("vvp", str(compile_out))
        completed = subprocess.run(
            run_cmd,
            cwd=plan.work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        output_text = completed.stdout + completed.stderr
        passed = judge_simulation_output(
            returncode=completed.returncode,
            output_text=output_text,
            criteria=plan.task.oracle.pass_criteria,
        )
        return SimulationRunResult(
            simulator=simulator,
            plan=plan,
            command=run_cmd,
            returncode=completed.returncode,
            passed=passed,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    if simulator == "verilator":
        tb_top = getattr(plan.task.oracle, "testbench_top_module", None) or "tb"
        obj_dir = plan.work_dir / "obj_dir"
        # Verilator compile
        compile_cmd_list: list[str] = [
            "verilator",
            "--binary",
            "--timing",
            "--trace",
            "-sv",
            f"--top-module", tb_top,
            "-j", "4",
            "--Mdir", str(obj_dir),
            # Suppress common warnings from third-party RTL
            "-Wno-COMBDLY", "-Wno-LATCH", "-Wno-UNOPTFLAT",
            "-Wno-MULTIDRIVEN", "-Wno-CASEOVERLAP", "-Wno-IMPLICIT",
            "-Wno-CASEINCOMPLETE", "-Wno-WIDTHTRUNC", "-Wno-WIDTHEXPAND",
            "-Wno-PINMISSING", "-Wno-ASCRANGE", "-Wno-EOFNEWLINE",
            "-Wno-DECLFILENAME", "-Wno-TIMESCALEMOD", "-Wno-INITIALDLY",
            "-Wno-SIDEEFFECT", "-Wno-fatal",
        ]
        compile_cmd_list.extend(str(path) for path in plan.source_files)
        compile_cmd = tuple(compile_cmd_list)
        compiled = subprocess.run(
            compile_cmd,
            cwd=plan.work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        if compiled.returncode != 0:
            return SimulationRunResult(
                simulator=simulator,
                plan=plan,
                command=compile_cmd,
                returncode=compiled.returncode,
                passed=False,
                stdout=compiled.stdout,
                stderr=compiled.stderr,
            )
        # Verilator run
        sim_binary = obj_dir / f"V{tb_top}"
        run_cmd = (str(sim_binary),)
        completed = subprocess.run(
            run_cmd,
            cwd=plan.work_dir,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        output_text = completed.stdout + completed.stderr
        passed = judge_simulation_output(
            returncode=completed.returncode,
            output_text=output_text,
            criteria=plan.task.oracle.pass_criteria,
        )
        return SimulationRunResult(
            simulator=simulator,
            plan=plan,
            command=run_cmd,
            returncode=completed.returncode,
            passed=passed,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    raise RuntimeError(f"unsupported simulator {simulator}")


def validate_candidate(
    task: StoredTask,
    candidate_rtl_paths: str | Path | Sequence[str | Path],
    *,
    work_root: str | Path,
    preferred_simulator: str | None = "xrun",
    timeout_s: int = 30,
) -> SimulationRunResult:
    plan = build_candidate_validation_plan(
        task,
        candidate_rtl_paths,
        work_root=work_root,
        preferred_simulator=preferred_simulator,
    )
    return run_simulation_plan(plan, timeout_s=timeout_s)



# ---------------------------------------------------------------------------
# Shared cocotb pass/fail regex — used by multiple task-group oracles.
# ---------------------------------------------------------------------------

_COCOTB_PASS_RE = re.compile(r"TESTS=(\d+)\s+PASS=(\d+)\s+FAIL=(\d+)")
