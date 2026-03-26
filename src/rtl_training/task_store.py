from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import shutil
from typing import Any

from .datasets import discover_rtllm_tasks, discover_verilog_eval_tasks


@dataclass(frozen=True)
class PassCriteria:
    success_markers: tuple[str, ...] = ()
    failure_markers: tuple[str, ...] = ()
    zero_value_regex: str | None = None
    zero_value_group: int = 1

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PassCriteria":
        return cls(
            success_markers=tuple(str(item) for item in raw.get("success_markers", ())),
            failure_markers=tuple(str(item) for item in raw.get("failure_markers", ())),
            zero_value_regex=(
                None if raw.get("zero_value_regex") is None else str(raw["zero_value_regex"])
            ),
            zero_value_group=int(raw.get("zero_value_group", 1)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success_markers": list(self.success_markers),
            "failure_markers": list(self.failure_markers),
            "zero_value_regex": self.zero_value_regex,
            "zero_value_group": self.zero_value_group,
        }


@dataclass(frozen=True)
class SimulationOracle:
    testbench_path: Path
    gold_rtl_path: Path
    requires_reference_rtl: bool
    candidate_top_module: str
    reference_top_module: str
    pass_criteria: PassCriteria
    support_files: tuple[Path, ...] = ()

    @classmethod
    def from_dict(cls, task_root: Path, raw: dict[str, Any]) -> "SimulationOracle":
        return cls(
            testbench_path=task_root / str(raw["testbench"]),
            gold_rtl_path=task_root / str(raw["gold_rtl"]),
            requires_reference_rtl=bool(raw["requires_reference_rtl"]),
            candidate_top_module=str(raw["candidate_top_module"]),
            reference_top_module=str(raw["reference_top_module"]),
            pass_criteria=PassCriteria.from_dict(dict(raw["pass_criteria"])),
            support_files=tuple(task_root / str(item) for item in raw.get("support_files", ())),
        )

    def to_dict(self, task_root: Path) -> dict[str, Any]:
        return {
            "kind": "simulation",
            "testbench": str(self.testbench_path.relative_to(task_root)),
            "gold_rtl": str(self.gold_rtl_path.relative_to(task_root)),
            "requires_reference_rtl": self.requires_reference_rtl,
            "candidate_top_module": self.candidate_top_module,
            "reference_top_module": self.reference_top_module,
            "pass_criteria": self.pass_criteria.to_dict(),
            "support_files": [str(path.relative_to(task_root)) for path in self.support_files],
        }


@dataclass(frozen=True)
class StoredTask:
    root: Path
    dataset_name: str
    task_id: str
    spec_path: Path
    public_dir: Path
    public_task_path: Path
    metadata: dict[str, Any]
    oracle: SimulationOracle | None


_MODULE_DECL_RE = re.compile(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)\b")
_SECTION_HEADING_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_ /-]*$")
_SPEC_SECTION_LABELS = {
    "module name": "module_name",
    "input ports": "inputs",
    "output ports": "outputs",
    "parameter": "parameters",
    "parameters": "parameters",
}

_RTLLM_INVALID_TASKS: dict[str, str] = {
    "div_16bit": "benchmark testbench does not compile cleanly",
    "radix2_div": "published gold RTL fails its own benchmark",
}

_CURATED_INTERFACE_MANIFESTS: dict[str, Path] = {
    "rtllm_v1_1": Path(__file__).resolve().parents[2] / "configs" / "rtllm_v1_1_interfaces.json",
}


def _extract_module_names(text: str) -> tuple[str, ...]:
    return tuple(match.group(1) for match in _MODULE_DECL_RE.finditer(text))


def _select_reference_top_module(*, task_id: str, gold_path: Path, gold_rtl_text: str) -> str:
    module_names = _extract_module_names(gold_rtl_text)
    if not module_names:
        return task_id

    preferred_names = (
        f"verified_{task_id}",
        gold_path.stem,
        task_id,
    )
    for name in preferred_names:
        if name in module_names:
            return name

    verified_names = tuple(name for name in module_names if name.startswith("verified_"))
    if len(verified_names) == 1:
        return verified_names[0]
    return module_names[0]


def _collect_support_files(
    *,
    source_dir: Path,
    spec_path: Path,
    gold_rtl_path: Path,
    testbench_path: Path,
) -> tuple[Path, ...]:
    excluded = {spec_path.resolve(), gold_rtl_path.resolve(), testbench_path.resolve()}
    return tuple(
        sorted(
            path
            for path in source_dir.iterdir()
            if path.is_file() and path.resolve() not in excluded
        )
    )


def _split_structured_spec_sections(spec_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for raw_line in spec_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            if current_section is not None:
                sections.setdefault(current_section, []).append("")
            continue
        if stripped.endswith((":","：")):
            label = stripped[:-1].strip().lower()
            mapped = _SPEC_SECTION_LABELS.get(label)
            if mapped is not None:
                current_section = mapped
                sections.setdefault(current_section, [])
                continue
            if _SECTION_HEADING_RE.match(stripped[:-1].strip()):
                current_section = None
                continue
        if current_section is not None:
            sections.setdefault(current_section, []).append(stripped)
    return sections


def _parse_named_items(lines: list[str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for line in lines:
        if not line:
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_$]*)\s*:\s*(.*)$", line)
        if match is None:
            continue
        items.append(
            {
                "name": match.group(1),
                "description": match.group(2).strip(),
            }
        )
    return items


def _parse_parameters(lines: list[str]) -> list[dict[str, str]]:
    parameters: list[dict[str, str]] = []
    for line in lines:
        if not line:
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_$]*)\s*=\s*([^;]+);?$", line)
        if match is None:
            continue
        parameters.append(
            {
                "name": match.group(1),
                "value": match.group(2).strip(),
            }
        )
    return parameters


@lru_cache(maxsize=None)
def _load_curated_interface_manifest(dataset_name: str) -> dict[str, dict[str, Any]]:
    manifest_path = _CURATED_INTERFACE_MANIFESTS.get(dataset_name)
    if manifest_path is None:
        return {}
    raw = json.loads(manifest_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"curated interface manifest for {dataset_name} must be a mapping")
    manifest: dict[str, dict[str, Any]] = {}
    for task_id, task_interface in raw.items():
        if not isinstance(task_interface, dict):
            raise ValueError(
                f"curated interface manifest entry for {dataset_name}/{task_id} must be an object"
            )
        manifest[str(task_id)] = dict(task_interface)
    return manifest


def _normalize_curated_parameters(
    raw_parameters: Any,
    *,
    dataset_name: str,
    task_id: str,
) -> list[dict[str, str]]:
    if not isinstance(raw_parameters, list):
        raise ValueError(
            f"curated interface manifest entry for {dataset_name}/{task_id} has non-list parameters"
        )
    parameters: list[dict[str, str]] = []
    for raw_parameter in raw_parameters:
        if not isinstance(raw_parameter, dict) or "name" not in raw_parameter:
            raise ValueError(
                f"curated interface manifest entry for {dataset_name}/{task_id} has invalid parameter"
            )
        parameter = {"name": str(raw_parameter["name"])}
        if raw_parameter.get("value") is not None:
            parameter["value"] = str(raw_parameter["value"])
        parameters.append(parameter)
    return parameters


def _normalize_curated_ports(
    raw_ports: Any,
    *,
    dataset_name: str,
    task_id: str,
) -> list[dict[str, str]]:
    if not isinstance(raw_ports, list):
        raise ValueError(
            f"curated interface manifest entry for {dataset_name}/{task_id} has non-list ports"
        )
    ports: list[dict[str, str]] = []
    for raw_port in raw_ports:
        if not isinstance(raw_port, dict) or "name" not in raw_port or "direction" not in raw_port:
            raise ValueError(
                f"curated interface manifest entry for {dataset_name}/{task_id} has invalid port"
            )
        direction = str(raw_port["direction"]).lower()
        if direction not in {"input", "output", "inout"}:
            raise ValueError(
                f"curated interface manifest entry for {dataset_name}/{task_id} has invalid "
                f"direction {direction!r}"
            )
        port = {
            "name": str(raw_port["name"]),
            "direction": direction,
        }
        if raw_port.get("width") not in {None, ""}:
            port["width"] = str(raw_port["width"])
        ports.append(port)
    return ports


def _build_curated_public_interface_contract(
    *,
    dataset_name: str,
    task_id: str,
    candidate_top_module: str,
) -> dict[str, Any] | None:
    manifest = _load_curated_interface_manifest(dataset_name)
    if not manifest:
        return None
    raw_interface = manifest.get(task_id)
    if raw_interface is None:
        raise ValueError(
            f"missing curated interface manifest entry for {dataset_name}/{task_id}"
        )

    top_module = str(raw_interface.get("top_module", candidate_top_module))
    if top_module != candidate_top_module:
        raise ValueError(
            f"curated top module for {dataset_name}/{task_id} is {top_module!r}, "
            f"expected {candidate_top_module!r}"
        )

    ports = _normalize_curated_ports(
        raw_interface.get("ports", []),
        dataset_name=dataset_name,
        task_id=task_id,
    )
    parameters = _normalize_curated_parameters(
        raw_interface.get("parameters", []),
        dataset_name=dataset_name,
        task_id=task_id,
    )
    interface: dict[str, Any] = {
        "top_module": top_module,
        "declared_module_name": top_module,
        "inputs": [dict(port) for port in ports if port["direction"] == "input"],
        "outputs": [dict(port) for port in ports if port["direction"] == "output"],
        "parameters": parameters,
        "ports": ports,
    }

    notes = raw_interface.get("notes", [])
    if notes:
        if not isinstance(notes, list):
            raise ValueError(
                f"curated interface manifest entry for {dataset_name}/{task_id} has non-list notes"
            )
        interface["notes"] = [str(note) for note in notes]
    return interface


def _build_public_interface_contract(*, spec_text: str, candidate_top_module: str) -> dict[str, Any]:
    sections = _split_structured_spec_sections(spec_text)
    module_name_lines = [line for line in sections.get("module_name", []) if line]
    declared_top_module = candidate_top_module
    if module_name_lines:
        declared_top_module = module_name_lines[0].split()[0]

    return {
        "top_module": candidate_top_module,
        "declared_module_name": declared_top_module,
        "inputs": _parse_named_items(sections.get("inputs", [])),
        "outputs": _parse_named_items(sections.get("outputs", [])),
        "parameters": _parse_parameters(sections.get("parameters", [])),
    }


def _build_task_public_interface_contract(
    *,
    dataset_name: str,
    task_id: str,
    spec_text: str,
    candidate_top_module: str,
) -> dict[str, Any]:
    curated_interface = _build_curated_public_interface_contract(
        dataset_name=dataset_name,
        task_id=task_id,
        candidate_top_module=candidate_top_module,
    )
    if curated_interface is not None:
        return curated_interface
    return _build_public_interface_contract(
        spec_text=spec_text,
        candidate_top_module=candidate_top_module,
    )


def _write_task_bundle(
    *,
    output_root: Path,
    dataset_name: str,
    task_id: str,
    spec_text: str,
    spec_name: str,
    public_metadata: dict[str, Any],
    oracle: SimulationOracle | None,
    source_metadata: dict[str, Any],
) -> Path:
    task_root = output_root / dataset_name / task_id
    public_dir = task_root / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    spec_path = public_dir / spec_name
    public_task_path = public_dir / "task.json"

    spec_path.write_text(spec_text)
    public_task_path.write_text(json.dumps(public_metadata, indent=2, sort_keys=True) + "\n")

    task_metadata: dict[str, Any] = {
        "dataset_name": dataset_name,
        "task_id": task_id,
        "public": {
            "directory": "public",
            "spec": str(spec_path.relative_to(task_root)),
            "task": str(public_task_path.relative_to(task_root)),
        },
        "source": source_metadata,
    }

    if oracle is not None:
        oracle_dir = task_root / "oracle"
        sim_dir = oracle_dir / "sim"
        support_dir = oracle_dir / "support"
        sim_dir.mkdir(parents=True, exist_ok=True)

        gold_dest = oracle_dir / f"gold_rtl{oracle.gold_rtl_path.suffix}"
        testbench_dest = sim_dir / f"testbench{oracle.testbench_path.suffix}"
        shutil.copy2(oracle.gold_rtl_path, gold_dest)
        shutil.copy2(oracle.testbench_path, testbench_dest)

        support_destinations: list[Path] = []
        for support_file in oracle.support_files:
            dest = support_dir / support_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(support_file, dest)
            support_destinations.append(dest)

        stored_oracle = SimulationOracle(
            testbench_path=testbench_dest,
            gold_rtl_path=gold_dest,
            requires_reference_rtl=oracle.requires_reference_rtl,
            candidate_top_module=oracle.candidate_top_module,
            reference_top_module=oracle.reference_top_module,
            pass_criteria=oracle.pass_criteria,
            support_files=tuple(support_destinations),
        )
        task_metadata["oracle"] = stored_oracle.to_dict(task_root)

    (task_root / "task.json").write_text(json.dumps(task_metadata, indent=2, sort_keys=True) + "\n")
    return task_root


def load_stored_task(task_root: str | Path) -> StoredTask:
    task_root_path = Path(task_root).resolve()
    metadata = json.loads((task_root_path / "task.json").read_text())
    public = dict(metadata["public"])
    oracle_raw = metadata.get("oracle")
    oracle = None
    if oracle_raw is not None:
        oracle = SimulationOracle.from_dict(task_root_path, dict(oracle_raw))
    return StoredTask(
        root=task_root_path,
        dataset_name=str(metadata["dataset_name"]),
        task_id=str(metadata["task_id"]),
        spec_path=task_root_path / str(public["spec"]),
        public_dir=task_root_path / str(public["directory"]),
        public_task_path=task_root_path / str(public["task"]),
        metadata=metadata,
        oracle=oracle,
    )


def store_rtllm_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str,
    include_invalid: bool = False,
) -> tuple[Path, ...]:
    tasks = discover_rtllm_tasks(source_root, dataset_name=dataset_name)
    written: list[Path] = []
    for task in tasks:
        if not include_invalid and task.task_id in _RTLLM_INVALID_TASKS:
            continue
        assert task.gold_rtl_path is not None
        assert task.testbench_path is not None
        gold_rtl_text = task.gold_rtl_path.read_text()
        reference_top_module = _select_reference_top_module(
            task_id=task.task_id,
            gold_path=task.gold_rtl_path,
            gold_rtl_text=gold_rtl_text,
        )
        spec_text = task.spec_path.read_text()
        support_files = _collect_support_files(
            source_dir=task.source_dir,
            spec_path=task.spec_path,
            gold_rtl_path=task.gold_rtl_path,
            testbench_path=task.testbench_path,
        )
        public_interface = _build_task_public_interface_contract(
            dataset_name=dataset_name,
            task_id=task.task_id,
            spec_text=spec_text,
            candidate_top_module=task.task_id,
        )
        public_metadata = {
            "dataset_name": dataset_name,
            "task_id": task.task_id,
            "candidate_top_module": public_interface["top_module"],
            "spec": "spec.txt",
            "interface": public_interface,
            "deliverables": {
                "rtl": "submission/candidate.sv",
                "summary": "result/result.json",
            },
        }
        oracle = SimulationOracle(
            testbench_path=task.testbench_path,
            gold_rtl_path=task.gold_rtl_path,
            requires_reference_rtl=False,
            candidate_top_module=str(public_interface["top_module"]),
            reference_top_module=reference_top_module,
            pass_criteria=PassCriteria(
                success_markers=("Your Design Passed",),
                failure_markers=("===========Error===========", "=========== Failed ==========="),
                zero_value_regex=r"Test completed with\s+(\d+)/(\d+)\s+failures",
                zero_value_group=1,
            ),
            support_files=support_files,
        )
        source_metadata = {
            "source_rel_dir": task.source_rel_dir.as_posix(),
            "source_files": {
                "spec": task.spec_path.name,
                "gold_rtl": task.gold_rtl_path.name,
                "testbench": task.testbench_path.name,
                "support": [path.name for path in support_files],
            },
        }
        written.append(
            _write_task_bundle(
                output_root=Path(output_root),
                dataset_name=dataset_name,
                task_id=task.task_id,
                spec_text=spec_text,
                spec_name="spec.txt",
                public_metadata=public_metadata,
                oracle=oracle,
                source_metadata=source_metadata,
            )
        )
    return tuple(written)


def store_verilog_eval_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str,
    subset: str = "dataset_spec-to-rtl",
) -> tuple[Path, ...]:
    tasks = discover_verilog_eval_tasks(
        source_root,
        dataset_name=dataset_name,
        subset=subset,
    )
    written: list[Path] = []
    for task in tasks:
        assert task.gold_rtl_path is not None
        assert task.testbench_path is not None
        public_metadata = {
            "dataset_name": dataset_name,
            "task_id": task.task_id,
            "candidate_top_module": "TopModule",
            "spec": "spec.txt",
            "deliverables": {
                "rtl": "submission/candidate.sv",
                "summary": "result/result.json",
            },
        }
        oracle = SimulationOracle(
            testbench_path=task.testbench_path,
            gold_rtl_path=task.gold_rtl_path,
            requires_reference_rtl=True,
            candidate_top_module="TopModule",
            reference_top_module="RefModule",
            pass_criteria=PassCriteria(
                failure_markers=("TIMEOUT",),
                zero_value_regex=r"Mismatches:\s*(\d+)\s+in\s+\d+\s+samples",
                zero_value_group=1,
            ),
        )
        source_metadata = {
            "source_rel_dir": task.source_rel_dir.as_posix(),
            "source_files": {
                "spec": task.spec_path.name,
                "gold_rtl": task.gold_rtl_path.name,
                "testbench": task.testbench_path.name,
            },
        }
        written.append(
            _write_task_bundle(
                output_root=Path(output_root),
                dataset_name=dataset_name,
                task_id=task.task_id,
                spec_text=task.spec_path.read_text(),
                spec_name="spec.txt",
                public_metadata=public_metadata,
                oracle=oracle,
                source_metadata=source_metadata,
            )
        )
    return tuple(written)
