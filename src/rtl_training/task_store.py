from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, Sequence

from .datasets import Tier, discover_rtllm_tasks, discover_verilog_eval_tasks
from .interface_contracts import (
    materialize_public_interface_sv,
    normalize_public_interface_contract,
)
from .shared_sources import SharedSourceRegistry, register_shared_source_bundle


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
    spec_dir: Path
    public_dir: Path
    public_task_path: Path
    private_dir: Path | None
    shared_private_ref: "SharedPrivateSourceRef | None"
    metadata: dict[str, Any]
    oracle: SimulationOracle | None
    tier: Tier | None = None


@dataclass(frozen=True)
class SharedPrivateSourceRef:
    registry_path: Path
    bundle_id: str
    subpaths: tuple[str, ...]

    @classmethod
    def from_dict(cls, task_root: Path, raw: dict[str, Any]) -> "SharedPrivateSourceRef":
        raw_subpaths = raw.get("subpaths", ())
        if not isinstance(raw_subpaths, list):
            raise ValueError("shared_private.subpaths must be a list")
        return cls(
            registry_path=(task_root / str(raw["registry"])).resolve(),
            bundle_id=str(raw["bundle_id"]),
            subpaths=tuple(str(item) for item in raw_subpaths),
        )

    def to_dict(self, task_root: Path) -> dict[str, Any]:
        return {
            "registry": os.path.relpath(self.registry_path, task_root),
            "bundle_id": self.bundle_id,
            "subpaths": list(self.subpaths),
        }

    def bundle_root(self) -> Path:
        registry = SharedSourceRegistry.load(self.registry_path)
        return registry.by_id(self.bundle_id).root

    def resolve_paths(self) -> tuple[Path, ...]:
        root = self.bundle_root()
        return tuple(root / subpath for subpath in self.subpaths)


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

_CURATED_TASK_PACK_MANIFESTS: dict[str, Path] = {
    "opentitan_ip_docs": Path(__file__).resolve().parents[2]
    / "configs"
    / "opentitan_ip_docs_tasks.json",
}

_CURATED_TASK_PACK_SPECS: dict[str, Path] = {
    "opentitan_ip_docs": Path(__file__).resolve().parents[2]
    / "task_library"
    / "opentitan_ip_docs",
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


@lru_cache(maxsize=None)
def _load_curated_task_pack_manifest(dataset_name: str) -> tuple[dict[str, Any], ...]:
    manifest_path = _CURATED_TASK_PACK_MANIFESTS.get(dataset_name)
    if manifest_path is None:
        raise ValueError(f"no curated task pack manifest registered for {dataset_name}")
    raw = json.loads(manifest_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"curated task pack manifest for {dataset_name} must be an object")
    manifest_dataset_name = str(raw.get("dataset_name", ""))
    if manifest_dataset_name != dataset_name:
        raise ValueError(
            f"curated task pack manifest dataset_name {manifest_dataset_name!r} "
            f"does not match {dataset_name!r}"
        )
    raw_tasks = raw.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError(f"curated task pack manifest for {dataset_name} must contain a tasks list")
    tasks: list[dict[str, Any]] = []
    for raw_task in raw_tasks:
        if not isinstance(raw_task, dict):
            raise ValueError(
                f"curated task pack manifest entry for {dataset_name} must be an object"
            )
        tasks.append(dict(raw_task))
    return tuple(tasks)


def _curated_task_pack_specs_root(dataset_name: str) -> Path:
    specs_root = _CURATED_TASK_PACK_SPECS.get(dataset_name)
    if specs_root is None:
        raise ValueError(f"no curated task pack specs registered for {dataset_name}")
    return specs_root


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
    return normalize_public_interface_contract(
        interface,
        candidate_top_module=top_module,
    )


def _build_public_interface_contract(*, spec_text: str, candidate_top_module: str) -> dict[str, Any]:
    sections = _split_structured_spec_sections(spec_text)
    module_name_lines = [line for line in sections.get("module_name", []) if line]
    declared_top_module = candidate_top_module
    if module_name_lines:
        declared_top_module = module_name_lines[0].split()[0]

    return normalize_public_interface_contract({
        "top_module": candidate_top_module,
        "declared_module_name": declared_top_module,
        "inputs": _parse_named_items(sections.get("inputs", [])),
        "outputs": _parse_named_items(sections.get("outputs", [])),
        "parameters": _parse_parameters(sections.get("parameters", [])),
    }, candidate_top_module=candidate_top_module)


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
    spec_source: str | Path,
    public_metadata: dict[str, Any],
    oracle: SimulationOracle | None,
    source_metadata: dict[str, Any],
    private_sources: Sequence[str | Path] = (),
    shared_private_ref: SharedPrivateSourceRef | None = None,
    tier: Tier | None = None,
    raw_oracle_dir: Path | None = None,
    raw_oracle_metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a task bundle to *output_root/dataset_name/task_id/*.

    *spec_source* is either a plain-text string (written as ``spec/spec.txt``)
    or a :class:`~pathlib.Path` pointing to a file or directory that is copied
    into ``public/spec/``.
    """
    task_root = output_root / dataset_name / task_id
    if task_root.exists():
        shutil.rmtree(task_root)
    public_dir = task_root / "public"
    spec_dir = public_dir / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    public_task_path = public_dir / "task.json"

    if isinstance(spec_source, str):
        (spec_dir / "spec.txt").write_text(spec_source)
    else:
        source_path = Path(spec_source)
        if source_path.is_dir():
            shutil.copytree(source_path, spec_dir, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, spec_dir / source_path.name)

    if tier is not None:
        public_metadata.setdefault("tier", tier)
    public_metadata["spec"] = "spec/"
    interface = public_metadata.get("interface")
    if isinstance(interface, dict):
        public_metadata["interface"] = normalize_public_interface_contract(
            interface,
            candidate_top_module=str(public_metadata["candidate_top_module"]),
        )
        materialize_public_interface_sv(spec_dir, public_metadata["interface"])
    public_task_path.write_text(json.dumps(public_metadata, indent=2, sort_keys=True) + "\n")

    task_metadata: dict[str, Any] = {
        "dataset_name": dataset_name,
        "task_id": task_id,
        "public": {
            "directory": "public",
            "spec": "public/spec/",
            "task": str(public_task_path.relative_to(task_root)),
        },
        "source": source_metadata,
    }
    if tier is not None:
        task_metadata["tier"] = tier

    private_assets: list[str] = []
    if private_sources and shared_private_ref is not None:
        raise ValueError("task bundle cannot use copied private sources and shared private refs together")
    if private_sources:
        private_dir = task_root / "private"
        private_dir.mkdir(parents=True, exist_ok=True)
        for private_source in private_sources:
            source_path = Path(private_source)
            destination = private_dir / source_path.name
            if source_path.is_dir():
                shutil.copytree(source_path, destination, dirs_exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
            private_assets.append(str(destination.relative_to(task_root)))
        task_metadata["private"] = {
            "directory": "private",
            "assets": private_assets,
        }
    elif shared_private_ref is not None:
        task_metadata["shared_private"] = shared_private_ref.to_dict(task_root)

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
    elif raw_oracle_dir is not None:
        oracle_dest = task_root / "oracle"
        shutil.copytree(raw_oracle_dir, oracle_dest, dirs_exist_ok=True)
        if raw_oracle_metadata is not None:
            task_metadata["oracle"] = raw_oracle_metadata

    (task_root / "task.json").write_text(json.dumps(task_metadata, indent=2, sort_keys=True) + "\n")
    return task_root


def load_stored_task(task_root: str | Path) -> StoredTask:
    task_root_path = Path(task_root).resolve()
    metadata = json.loads((task_root_path / "task.json").read_text())
    public = dict(metadata["public"])
    private = metadata.get("private")
    shared_private_raw = metadata.get("shared_private")
    oracle_raw = metadata.get("oracle")
    oracle = None
    if oracle_raw is not None and oracle_raw.get("kind", "simulation") == "simulation":
        oracle = SimulationOracle.from_dict(task_root_path, dict(oracle_raw))
    shared_private_ref = None
    if shared_private_raw is not None:
        shared_private_ref = SharedPrivateSourceRef.from_dict(
            task_root_path,
            dict(shared_private_raw),
        )
    raw_tier = metadata.get("tier")
    tier: Tier | None = raw_tier if raw_tier is not None else None
    spec_ref = str(public["spec"])
    spec_resolved = task_root_path / spec_ref
    # Backward compat: old format has "public/spec.txt" (a file).
    # New format has "public/spec/" (a directory).
    if spec_resolved.is_dir():
        spec_dir = spec_resolved
    else:
        spec_dir = spec_resolved.parent
    return StoredTask(
        root=task_root_path,
        dataset_name=str(metadata["dataset_name"]),
        task_id=str(metadata["task_id"]),
        spec_dir=spec_dir,
        public_dir=task_root_path / str(public["directory"]),
        public_task_path=task_root_path / str(public["task"]),
        private_dir=(
            task_root_path / str(dict(private)["directory"])
            if isinstance(private, dict) and "directory" in private
            else None
        ),
        shared_private_ref=shared_private_ref,
        metadata=metadata,
        oracle=oracle,
        tier=tier,
    )


def store_rtllm_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str,
    include_invalid: bool = False,
    tier: Tier | None = None,
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
            "interface": public_interface,
            "deliverables": {
                "rtl": "submission/",
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
                spec_source=spec_text,
                public_metadata=public_metadata,
                oracle=oracle,
                source_metadata=source_metadata,
                tier=tier,
            )
        )
    return tuple(written)


def store_verilog_eval_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str,
    subset: str = "dataset_spec-to-rtl",
    tier: Tier | None = None,
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
            "deliverables": {
                "rtl": "submission/",
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
                spec_source=task.spec_path.read_text(),
                public_metadata=public_metadata,
                oracle=oracle,
                source_metadata=source_metadata,
                tier=tier,
            )
        )
    return tuple(written)


def store_generic_task(
    *,
    output_root: str | Path,
    dataset_name: str,
    task_id: str,
    spec_source: str | Path,
    tier: Tier | None = None,
    candidate_top_module: str,
    interface: dict[str, Any] | None = None,
    gold_rtl_path: str | Path | None = None,
    testbench_path: str | Path | None = None,
    support_files: Sequence[str | Path] = (),
    reference_top_module: str | None = None,
    requires_reference_rtl: bool = False,
    pass_criteria: PassCriteria | None = None,
    source_metadata: dict[str, Any] | None = None,
    private_sources: Sequence[str | Path] = (),
    shared_private_ref: SharedPrivateSourceRef | None = None,
) -> Path:
    """Ingest a hand-assembled task into the task store.

    Unlike :func:`store_rtllm_tasks` and :func:`store_verilog_eval_tasks`,
    this function does not discover files — the caller supplies all paths.
    *spec_source* can be a plain-text string, a file path, or a directory
    path containing markdown, images, and other spec artifacts.
    """
    public_metadata: dict[str, Any] = {
        "dataset_name": dataset_name,
        "task_id": task_id,
        "candidate_top_module": candidate_top_module,
        "deliverables": {
            "rtl": "submission/",
            "summary": "result/result.json",
        },
    }
    if interface is not None:
        public_metadata["interface"] = normalize_public_interface_contract(
            interface,
            candidate_top_module=candidate_top_module,
        )

    oracle: SimulationOracle | None = None
    if gold_rtl_path is not None and testbench_path is not None:
        oracle = SimulationOracle(
            testbench_path=Path(testbench_path),
            gold_rtl_path=Path(gold_rtl_path),
            requires_reference_rtl=requires_reference_rtl,
            candidate_top_module=candidate_top_module,
            reference_top_module=reference_top_module or candidate_top_module,
            pass_criteria=pass_criteria or PassCriteria(),
            support_files=tuple(Path(p) for p in support_files),
        )

    effective_source_metadata: dict[str, Any] = {"origin": "generic"}
    if source_metadata is not None:
        effective_source_metadata.update(source_metadata)

    return _write_task_bundle(
        output_root=Path(output_root),
        dataset_name=dataset_name,
        task_id=task_id,
        spec_source=spec_source,
        public_metadata=public_metadata,
        oracle=oracle,
        source_metadata=effective_source_metadata,
        private_sources=private_sources,
        shared_private_ref=shared_private_ref,
        tier=tier,
    )


def store_curated_task_pack(
    output_root: str | Path,
    *,
    dataset_name: str,
    tier: Tier | None = None,
    source_root: str | Path | None = None,
) -> tuple[Path, ...]:
    manifest = _load_curated_task_pack_manifest(dataset_name)
    specs_root = _curated_task_pack_specs_root(dataset_name)
    source_root_path = Path(source_root).expanduser().resolve() if source_root is not None else None
    registry_root = Path(output_root).resolve().parent / "shared_sources"
    shared_bundle = None
    if source_root_path is not None and any(
        str(task.get("private_source_mode", "copy")) == "shared_bundle" for task in manifest
    ):
        shared_bundle = register_shared_source_bundle(
            registry_root,
            name=dataset_name,
            source_root=source_root_path,
        )
    written: list[Path] = []
    for task in manifest:
        task_id = str(task["task_id"])
        candidate_top_module = str(task["candidate_top_module"])
        interface = task.get("interface")
        if interface is not None:
            if not isinstance(interface, dict):
                raise ValueError(
                    f"curated task pack interface for {dataset_name}/{task_id} must be an object"
                )
            top_module = str(interface.get("top_module", candidate_top_module))
            if top_module != candidate_top_module:
                raise ValueError(
                    f"curated task pack top module for {dataset_name}/{task_id} is "
                    f"{top_module!r}, expected {candidate_top_module!r}"
                )
        spec_subdir = str(task["spec_subdir"])
        spec_dir = specs_root / spec_subdir
        if not spec_dir.is_dir():
            raise FileNotFoundError(
                f"missing curated spec directory for {dataset_name}/{task_id}: {spec_dir}"
            )
        task_tier = tier if tier is not None else task.get("tier")
        source_metadata: dict[str, Any] = {
            "origin": "curated_task_pack",
            "manifest": str(_CURATED_TASK_PACK_MANIFESTS[dataset_name].relative_to(specs_root.parents[1])),
            "spec_subdir": spec_subdir,
        }
        source_docs = task.get("source_docs")
        if source_docs is not None:
            if not isinstance(source_docs, list):
                raise ValueError(
                    f"curated task pack source_docs for {dataset_name}/{task_id} must be a list"
                )
            source_metadata["source_docs"] = [str(item) for item in source_docs]
        private_sources: tuple[Path, ...] = ()
        shared_private_ref = None
        raw_private_source_dirs = task.get("private_source_dirs")
        if raw_private_source_dirs is not None:
            if source_root_path is None:
                raise ValueError(
                    f"curated task pack {dataset_name}/{task_id} requires source_root "
                    "to materialize private_source_dirs"
                )
            if not isinstance(raw_private_source_dirs, list):
                raise ValueError(
                    f"curated task pack private_source_dirs for {dataset_name}/{task_id} "
                    "must be a list"
                )
            private_source_mode = str(task.get("private_source_mode", "copy"))
            if private_source_mode == "copy":
                private_sources = tuple(source_root_path / str(item) for item in raw_private_source_dirs)
            elif private_source_mode == "shared_bundle":
                if shared_bundle is None:
                    raise ValueError(
                        f"curated task pack {dataset_name}/{task_id} expected a shared bundle"
                    )
                shared_private_ref = SharedPrivateSourceRef(
                    registry_path=(registry_root / "registry.json"),
                    bundle_id=shared_bundle.bundle_id,
                    subpaths=tuple(str(item) for item in raw_private_source_dirs),
                )
            else:
                raise ValueError(
                    f"curated task pack private_source_mode for {dataset_name}/{task_id} "
                    f"must be 'copy' or 'shared_bundle', got {private_source_mode!r}"
                )
            source_metadata["private_source_dirs"] = [str(item) for item in raw_private_source_dirs]
            source_metadata["private_source_mode"] = private_source_mode
        if source_root_path is not None:
            source_metadata["source_root"] = str(source_root_path)
        written.append(
            store_generic_task(
                output_root=output_root,
                dataset_name=dataset_name,
                task_id=task_id,
                spec_source=spec_dir,
                tier=task_tier,
                candidate_top_module=candidate_top_module,
                interface=dict(interface) if interface is not None else None,
                source_metadata=source_metadata,
                private_sources=private_sources,
                shared_private_ref=shared_private_ref,
            )
        )
    return tuple(written)


def store_opentitan_ip_docs_tasks(
    output_root: str | Path,
    *,
    tier: Tier | None = None,
    source_root: str | Path | None = None,
) -> tuple[Path, ...]:
    return store_curated_task_pack(
        output_root,
        dataset_name="opentitan_ip_docs",
        tier=tier,
        source_root=source_root,
    )


def store_cvdp_tasks(
    jsonl_path: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str = "cvdp",
    tier: Tier | None = "small",
) -> tuple[Path, ...]:
    """Ingest tasks from the CVDP benchmark JSONL into the task store.

    Each task gets a plain-text spec and a cocotb oracle harness.  Gold RTL
    is not required — the cocotb tests are the oracle.
    """
    import tempfile

    jsonl = Path(jsonl_path)
    output = Path(output_root)
    written: list[Path] = []

    for line in jsonl.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)

        # Skip modify/bugfix/complete tasks that supply existing RTL.
        input_ctx = record.get("input", {}).get("context", {})
        if any(v.strip() for v in input_ctx.values()):
            continue

        task_id = str(record["id"])
        categories = list(record.get("categories", []))
        spec_text = str(record["input"]["prompt"])
        harness_files: dict[str, str] = dict(record["harness"]["files"])

        # Parse .env to get TOPLEVEL (candidate module name) and MODULE (test module)
        env_text = harness_files.get("src/.env", "")
        env_vars: dict[str, str] = {}
        for env_line in env_text.splitlines():
            if "=" in env_line:
                key, _, val = env_line.partition("=")
                env_vars[key.strip()] = val.strip()

        toplevel = env_vars.get("TOPLEVEL", task_id)
        test_module = env_vars.get("MODULE", "")
        verilog_sources = env_vars.get("VERILOG_SOURCES", "")

        # Determine the expected candidate RTL filename from VERILOG_SOURCES
        # e.g., "/code/rtl/16qam_mapper.sv" → "16qam_mapper.sv"
        candidate_filenames = [
            Path(s.strip()).name
            for s in verilog_sources.split()
            if s.strip()
        ]

        # Write cocotb oracle files to a temp dir, then pass to _write_task_bundle
        with tempfile.TemporaryDirectory() as tmp:
            cocotb_dir = Path(tmp) / "cocotb"
            cocotb_dir.mkdir()
            for file_key, file_content in harness_files.items():
                if file_key == "docker-compose.yml":
                    continue
                # Strip the "src/" prefix for oracle storage
                if file_key.startswith("src/"):
                    dest_name = file_key[4:]
                else:
                    dest_name = file_key
                dest = cocotb_dir / dest_name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(file_content)

            # Determine difficulty from categories
            task_tier = tier
            if "easy" in categories:
                task_tier = "small"
            elif "medium" in categories:
                task_tier = "small"  # CVDP medium is still small by our scale

            public_metadata: dict[str, Any] = {
                "dataset_name": dataset_name,
                "task_id": task_id,
                "candidate_top_module": toplevel,
                "deliverables": {
                    "rtl": "submission/",
                    "summary": "result/result.json",
                },
            }

            oracle_metadata: dict[str, Any] = {
                "kind": "cocotb",
                "test_dir": "oracle",
                "toplevel": toplevel,
                "test_module": test_module,
                "candidate_filenames": candidate_filenames,
                "env": env_vars,
            }

            source_metadata: dict[str, Any] = {
                "origin": "cvdp_benchmark",
                "cvdp_id": task_id,
                "categories": categories,
            }

            written.append(
                _write_task_bundle(
                    output_root=output,
                    dataset_name=dataset_name,
                    task_id=task_id,
                    spec_source=spec_text,
                    public_metadata=public_metadata,
                    oracle=None,
                    source_metadata=source_metadata,
                    tier=task_tier,
                    raw_oracle_dir=cocotb_dir,
                    raw_oracle_metadata=oracle_metadata,
                )
            )

    return tuple(written)
