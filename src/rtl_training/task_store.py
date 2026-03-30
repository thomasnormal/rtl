from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Sequence

from .datasets import Tier, discover_rtllm_tasks, discover_verilog_eval_tasks
from .interface_contracts import (
    read_public_top_module,
    materialize_public_interface_sv,
    normalize_public_interface_contract,
    prepare_public_interface_contract,
)
from .micro_arch_contracts import validate_public_micro_arch_dir
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
    testbench_top_module: str | None = None
    preferred_simulator: str | None = None

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
            testbench_top_module=raw.get("testbench_top_module"),
            preferred_simulator=raw.get("preferred_simulator"),
        )

    def to_dict(self, task_root: Path) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": "simulation",
            "testbench": str(self.testbench_path.relative_to(task_root)),
            "gold_rtl": str(self.gold_rtl_path.relative_to(task_root)),
            "requires_reference_rtl": self.requires_reference_rtl,
            "candidate_top_module": self.candidate_top_module,
            "reference_top_module": self.reference_top_module,
            "pass_criteria": self.pass_criteria.to_dict(),
            "support_files": [str(path.relative_to(task_root)) for path in self.support_files],
        }
        if self.testbench_top_module is not None:
            d["testbench_top_module"] = self.testbench_top_module
        if self.preferred_simulator is not None:
            d["preferred_simulator"] = self.preferred_simulator
        return d


@dataclass(frozen=True)
class StoredTask:
    root: Path
    dataset_name: str
    task_id: str
    spec_dir: Path
    public_dir: Path
    public_top_module: str
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
    "opentitan": Path(__file__).resolve().parents[2]
    / "configs"
    / "opentitan_tasks.json",
    "riscv_hardware_specs": Path(__file__).resolve().parents[2]
    / "configs"
    / "riscv_hardware_specs_tasks.json",
}

_CURATED_TASK_PACK_SPECS: dict[str, Path] = {
    "opentitan": Path(__file__).resolve().parents[2]
    / "task_library"
    / "opentitan",
    "riscv_hardware_specs": Path(__file__).resolve().parents[2]
    / "task_library"
    / "riscv_hardware_specs",
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
def _load_curated_task_pack_document(dataset_name: str) -> dict[str, Any]:
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
    return raw


@lru_cache(maxsize=None)
def _load_curated_task_pack_manifest(dataset_name: str) -> tuple[dict[str, Any], ...]:
    raw = _load_curated_task_pack_document(dataset_name)
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


def _build_public_task_metadata(
    *,
    dataset_name: str,
    task_id: str,
    top_module: str,
    tier: Tier | None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "dataset_name": dataset_name,
        "task_id": task_id,
        "top_module": top_module,
        "deliverables": {
            "rtl": "submission/",
            "summary": "result/result.json",
        },
    }
    if tier is not None:
        metadata["tier"] = tier
    return metadata


def _write_task_bundle(
    *,
    output_root: Path,
    dataset_name: str,
    task_id: str,
    spec_source: str | Path,
    candidate_top_module: str,
    public_metadata: dict[str, Any],
    public_interface: dict[str, Any] | None,
    oracle: SimulationOracle | None,
    source_metadata: dict[str, Any],
    private_sources: Sequence[str | Path] = (),
    shared_private_ref: SharedPrivateSourceRef | None = None,
    tier: Tier | None = None,
    raw_oracle_dir: Path | None = None,
    raw_oracle_metadata: dict[str, Any] | None = None,
    public_interface_support_files: tuple[tuple[str, str], ...] = (),
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
    if public_interface is not None:
        normalized_public_interface = normalize_public_interface_contract(
            public_interface,
            candidate_top_module=candidate_top_module,
        )
        materialize_public_interface_sv(
            spec_dir,
            normalized_public_interface,
            support_files=public_interface_support_files,
        )
    else:
        normalized_public_interface = None
    validate_public_micro_arch_dir(spec_dir)
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
            testbench_top_module=oracle.testbench_top_module,
            preferred_simulator=oracle.preferred_simulator,
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
        public_top_module=read_public_top_module(task_root_path / str(public["task"])),
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
        public_metadata = _build_public_task_metadata(
            dataset_name=dataset_name,
            task_id=task.task_id,
            top_module=str(public_interface["top_module"]),
            tier=tier,
        )
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
                candidate_top_module=str(public_interface["top_module"]),
                public_metadata=public_metadata,
                public_interface=public_interface,
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
        public_metadata = _build_public_task_metadata(
            dataset_name=dataset_name,
            task_id=task.task_id,
            top_module="TopModule",
            tier=tier,
        )
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
                candidate_top_module="TopModule",
                public_metadata=public_metadata,
                public_interface=None,
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
    raw_oracle_dir: str | Path | None = None,
    raw_oracle_metadata: dict[str, Any] | None = None,
    public_interface_support_files: tuple[tuple[str, str], ...] = (),
) -> Path:
    """Ingest a hand-assembled task into the task store.

    Unlike :func:`store_rtllm_tasks` and :func:`store_verilog_eval_tasks`,
    this function does not discover files — the caller supplies all paths.
    *spec_source* can be a plain-text string, a file path, or a directory
    path containing markdown, images, and other spec artifacts.
    """
    public_metadata = _build_public_task_metadata(
        dataset_name=dataset_name,
        task_id=task_id,
        top_module=candidate_top_module,
        tier=tier,
    )
    normalized_public_interface = None
    if interface is not None:
        normalized_public_interface = normalize_public_interface_contract(
            interface,
            candidate_top_module=candidate_top_module,
        )

    oracle: SimulationOracle | None = None
    if raw_oracle_dir is not None and (gold_rtl_path is not None or testbench_path is not None):
        raise ValueError("generic task cannot use both simulation oracle inputs and raw_oracle_dir")
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
        candidate_top_module=candidate_top_module,
        public_metadata=public_metadata,
        public_interface=normalized_public_interface,
        oracle=oracle,
        source_metadata=effective_source_metadata,
        private_sources=private_sources,
        shared_private_ref=shared_private_ref,
        tier=tier,
        raw_oracle_dir=None if raw_oracle_dir is None else Path(raw_oracle_dir),
        raw_oracle_metadata=raw_oracle_metadata,
        public_interface_support_files=public_interface_support_files,
    )


def store_curated_task_pack(
    output_root: str | Path,
    *,
    dataset_name: str,
    tier: Tier | None = None,
    source_root: str | Path | None = None,
) -> tuple[Path, ...]:
    manifest = _load_curated_task_pack_manifest(dataset_name)
    manifest_document = _load_curated_task_pack_document(dataset_name)
    default_interface_profile = manifest_document.get("default_public_interface_profile")
    if default_interface_profile is not None:
        default_interface_profile = str(default_interface_profile)
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
    material_source_root = shared_bundle.root if shared_bundle is not None else source_root_path
    written: list[Path] = []
    for task in manifest:
        task_id = str(task["task_id"])
        candidate_top_module = str(task["candidate_top_module"])
        interface = task.get("interface")
        spec_subdir = str(task["spec_subdir"])
        source_metadata: dict[str, Any] = {
            "origin": "curated_task_pack",
            "manifest": str(_CURATED_TASK_PACK_MANIFESTS[dataset_name].relative_to(specs_root.parents[1])),
            "spec_subdir": spec_subdir,
        }
        public_interface_support_files: tuple[tuple[str, str], ...] = ()
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
            interface_profile = task.get("public_interface_profile", default_interface_profile)
            if interface_profile is not None:
                prepared_interface = prepare_public_interface_contract(
                    interface,
                    candidate_top_module=candidate_top_module,
                    profile=str(interface_profile),
                    task_id=task_id,
                    source_root=material_source_root,
                )
                interface = prepared_interface.interface
                public_interface_support_files = prepared_interface.support_files
                if prepared_interface.hidden_metadata is not None:
                    source_metadata["public_interface_internal"] = prepared_interface.hidden_metadata
        spec_dir = specs_root / spec_subdir
        if not spec_dir.is_dir():
            raise FileNotFoundError(
                f"missing curated spec directory for {dataset_name}/{task_id}: {spec_dir}"
            )
        task_tier = tier if tier is not None else task.get("tier")
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
                assert material_source_root is not None
                private_sources = tuple(
                    material_source_root / str(item) for item in raw_private_source_dirs
                )
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
        if material_source_root is not None:
            source_metadata["source_root"] = str(material_source_root)
        if source_root_path is not None and material_source_root is not None and source_root_path != material_source_root:
            source_metadata["source_checkout_root"] = str(source_root_path)
        raw_oracle_dir: Path | None = None
        raw_oracle_metadata: dict[str, Any] | None = None
        raw_oracle = task.get("raw_oracle")
        tempdir_cm = None
        if raw_oracle is not None:
            if source_root_path is None:
                raise ValueError(
                    f"curated task pack {dataset_name}/{task_id} requires source_root "
                    "to materialize raw_oracle assets"
                )
            if not isinstance(raw_oracle, dict):
                raise ValueError(
                    f"curated task pack raw_oracle for {dataset_name}/{task_id} must be an object"
                )
            raw_oracle_metadata = {
                str(key): value
                for key, value in raw_oracle.items()
                if key != "assets"
            }
            raw_assets = raw_oracle.get("assets", [])
            if not isinstance(raw_assets, list):
                raise ValueError(
                    f"curated task pack raw_oracle assets for {dataset_name}/{task_id} must be a list"
                )
            tempdir_cm = tempfile.TemporaryDirectory()
            raw_oracle_dir = Path(tempdir_cm.name) / "oracle"
            raw_oracle_dir.mkdir(parents=True, exist_ok=True)
            for raw_asset in raw_assets:
                if not isinstance(raw_asset, dict):
                    raise ValueError(
                        f"curated task pack raw_oracle asset for {dataset_name}/{task_id} must be an object"
                    )
                if "source" not in raw_asset or "dest" not in raw_asset:
                    raise ValueError(
                        f"curated task pack raw_oracle asset for {dataset_name}/{task_id} "
                        "must contain source and dest"
                    )
                source_base = str(raw_asset.get("source_base", "source_root"))
                if source_base == "source_root":
                    source_base_path = material_source_root
                elif source_base == "task_library_root":
                    source_base_path = specs_root
                else:
                    raise ValueError(
                        f"curated task pack raw_oracle asset for {dataset_name}/{task_id} "
                        f"has unsupported source_base {source_base!r}"
                    )
                source_path = source_base_path / str(raw_asset["source"])
                destination = raw_oracle_dir / str(raw_asset["dest"])
                if source_path.is_dir():
                    shutil.copytree(source_path, destination, dirs_exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, destination)
            if (raw_oracle_dir / "repo_overlay").exists():
                raw_oracle_metadata.setdefault("repo_overlay_dir", "repo_overlay")
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
                raw_oracle_dir=raw_oracle_dir,
                raw_oracle_metadata=raw_oracle_metadata,
                public_interface_support_files=public_interface_support_files,
            )
        )
        if tempdir_cm is not None:
            tempdir_cm.cleanup()
    return tuple(written)


def store_opentitan_tasks(
    output_root: str | Path,
    *,
    tier: Tier | None = None,
    source_root: str | Path | None = None,
) -> tuple[Path, ...]:
    return store_curated_task_pack(
        output_root,
        dataset_name="opentitan",
        tier=tier,
        source_root=source_root,
    )



def store_riscv_hardware_specs_tasks(
    output_root: str | Path,
    *,
    tier: Tier | None = None,
) -> tuple[Path, ...]:
    return store_curated_task_pack(
        output_root,
        dataset_name="riscv_hardware_specs",
        tier=tier,
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

            public_metadata = _build_public_task_metadata(
                dataset_name=dataset_name,
                task_id=task_id,
                top_module=toplevel,
                tier=task_tier,
            )

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
                    candidate_top_module=toplevel,
                    public_metadata=public_metadata,
                    public_interface=None,
                    oracle=None,
                    source_metadata=source_metadata,
                    tier=task_tier,
                    raw_oracle_dir=cocotb_dir,
                    raw_oracle_metadata=oracle_metadata,
                )
            )

    return tuple(written)


def _discover_chipbench_gen_tasks(
    root: Path,
    *,
    dataset_name: str,
    category: str,
) -> list[tuple[str, Path, Path, Path]]:
    """Find (task_id, spec, ref, test) triples inside a ChipBench gen subset."""
    prompt_suffix = "_prompt.txt"
    tasks: list[tuple[str, Path, Path, Path]] = []
    for prompt_path in sorted(root.glob(f"*{prompt_suffix}")):
        stem = prompt_path.name[: -len(prompt_suffix)]
        ref_path = _find_first_chipbench(root, stem, "_ref")
        test_path = _find_first_chipbench(root, stem, "_test")
        if ref_path is None or test_path is None:
            continue
        task_id = f"chipbench_{category}_{stem}"
        tasks.append((task_id, prompt_path, ref_path, test_path))
    return tasks


def _deconflict_ref_helpers(ref_text: str, spec_text: str) -> tuple[str, str]:
    """Handle helper module collisions in non-self-contained ChipBench tasks.

    Returns ``(patched_ref, shared_helpers_sv)`` where:
    - *patched_ref* has its internal helper definitions renamed to
      ``__ref_<name>`` and instantiations updated to match.
    - *shared_helpers_sv* contains the helper module code extracted from
      the spec (provided to both ref and candidate) left with original names.
      The ref's deconflicted copies avoid collisions with these originals.
    """
    import re as _re

    # 1. Extract helper code blocks from the spec
    blocks = _re.findall(
        r"```(?:verilog|systemverilog|sv)?\n(.*?)```", spec_text, _re.DOTALL,
    )
    shared_helpers = "\n\n".join(blocks)

    # 2. Find helper module definitions in ref (not RefModule itself)
    modules_in_ref = _re.findall(r"(?<=\bmodule\s)(\w+)", ref_text)
    helpers_in_ref = [m for m in modules_in_ref if m != "RefModule"]

    # 3. Rename ref-internal helpers so they don't collide with the spec copies
    for helper in helpers_in_ref:
        ref_text = _re.sub(
            rf"\b{_re.escape(helper)}\b", f"__ref_{helper}", ref_text,
        )

    # 4. Only keep spec helpers that are NOT already defined in the ref.
    #    If the ref defines dual_port_RAM internally, we renamed it to
    #    __ref_dual_port_RAM.  The candidate will provide its own copy,
    #    so we don't need the spec's copy as a support file.
    helpers_in_ref_set = set(helpers_in_ref)
    filtered_blocks: list[str] = []
    for block in blocks:
        block_modules = set(_re.findall(r"(?<=\bmodule\s)\w+", block))
        # Only include this block if none of its modules collide with ref
        if not block_modules & helpers_in_ref_set:
            filtered_blocks.append(block)
    shared_helpers = "\n\n".join(filtered_blocks)

    return ref_text, shared_helpers


def _find_first_chipbench(directory: Path, stem: str, suffix: str) -> Path | None:
    for ext in (".sv", ".v"):
        candidate = directory / f"{stem}{suffix}{ext}"
        if candidate.exists():
            return candidate
    return None


def store_chipbench_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str = "chipbench",
    tier: Tier | None = "small",
) -> tuple[Path, ...]:
    """Ingest Verilog generation tasks from the ChipBench benchmark.

    ChipBench uses a VerilogEval-style harness: specs as ``*_prompt.txt``,
    gold RTL as ``*_ref.sv`` (module ``RefModule``), and self-checking
    testbenches as ``*_test.sv`` that compare ``TopModule`` vs ``RefModule``.
    """
    root = Path(source_root)
    output = Path(output_root)
    written: list[Path] = []

    gen_root = root / "Verilog Gen"
    # Some subsets (cpu_ip) use a different output format in the testbench.
    # self_contain: prints "Mismatches: N in M samples"
    # cpu_ip: prints "Total mismatched samples is N out of M samples."
    #         or "No mismatched samples." when zero.
    _standard_criteria = PassCriteria(
        failure_markers=("TIMEOUT",),
        zero_value_regex=r"Mismatches:\s*(\d+)\s+in\s+\d+\s+samples",
        zero_value_group=1,
    )
    _cpu_criteria = PassCriteria(
        success_markers=("No mismatched samples.",),
        failure_markers=("TIMEOUT",),
        zero_value_regex=r"Total mismatched samples is\s*(\d+)\s+out of\s+\d+\s+samples",
        zero_value_group=1,
    )
    subsets: list[tuple[str, str, Tier | None, PassCriteria]] = [
        ("dataset_self_contain", "sc", "small", _standard_criteria),
        ("dataset_not_self_contain", "nsc", "small", _standard_criteria),
        ("dataset_cpu_ip", "cpu", "medium", _cpu_criteria),
    ]

    for subdir, category, subset_tier, criteria in subsets:
        subset_path = gen_root / subdir
        if not subset_path.is_dir():
            continue
        tasks = _discover_chipbench_gen_tasks(
            subset_path, dataset_name=dataset_name, category=category,
        )
        for task_id, spec_path, ref_path, test_path in tasks:
            # For NSC tasks, deconflict helper module names in ref files
            # and extract shared helpers from the spec.
            effective_ref = ref_path
            nsc_support: list[Path] = []
            if category == "nsc":
                patched, shared = _deconflict_ref_helpers(
                    ref_path.read_text(), spec_path.read_text(),
                )
                effective_ref = ref_path.parent / f"_deconf_{ref_path.name}"
                effective_ref.write_text(patched)
                if shared.strip():
                    helpers_path = ref_path.parent / f"_helpers_{ref_path.stem}.sv"
                    helpers_path.write_text(shared)
                    nsc_support.append(helpers_path)

            public_metadata = _build_public_task_metadata(
                dataset_name=dataset_name,
                task_id=task_id,
                top_module="TopModule",
                tier=subset_tier or tier,
            )
            # ChipBench was developed with iverilog v12-branch.  We use
            # verilator (handles most SV constructs + 2-state avoids Z
            # comparison issues).  Fall back to xrun for tasks with coding
            # patterns verilator rejects (BLKANDNBLK, BLKLOOPINIT).
            _VERILATOR_BLOCKLIST = {
                "Prob023_gray_code_counter",  # mixed blocking/nonblocking in gold RTL
                "Prob030_simple_implementation_RAM",  # loop init in gold RTL
            }
            stem = spec_path.name.replace("_prompt.txt", "")
            sim = "xrun" if stem in _VERILATOR_BLOCKLIST else "verilator"

            oracle = SimulationOracle(
                testbench_path=test_path,
                gold_rtl_path=effective_ref,
                requires_reference_rtl=True,
                candidate_top_module="TopModule",
                reference_top_module="RefModule",
                pass_criteria=criteria,
                support_files=tuple(nsc_support),
                preferred_simulator=sim,
            )
            source_metadata: dict[str, Any] = {
                "origin": "chipbench",
                "category": category,
                "spec_file": spec_path.name,
                "ref_file": ref_path.name,
                "test_file": test_path.name,
            }
            written.append(
                _write_task_bundle(
                    output_root=output,
                    dataset_name=dataset_name,
                    task_id=task_id,
                    spec_source=spec_path.read_text(),
                    candidate_top_module="TopModule",
                    public_metadata=public_metadata,
                    public_interface=None,
                    oracle=oracle,
                    source_metadata=source_metadata,
                    tier=subset_tier or tier,
                )
            )

    return tuple(written)


def store_realbench_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str = "realbench",
) -> tuple[Path, ...]:
    """Ingest module-level tasks from the RealBench benchmark.

    RealBench has three IP families (AES, SD card controller, E203 RISC-V).
    Each module has a markdown spec, a reference module (``ref_{module}``),
    a testbench comparing ref vs candidate, stimulus, and dependency files.
    Specs must be decrypted before calling (``make decrypt`` in the repo).
    """
    root = Path(source_root)
    output = Path(output_root)
    written: list[Path] = []

    ip_families: list[tuple[str, str, Tier]] = [
        ("aes", "aes", "small"),
        ("sdc", "sdc", "medium"),
        ("e203_hbirdv2", "e203", "medium"),
    ]

    # RealBench testbenches legitimately print "TIMEOUT" even on passing
    # runs (the timeout fires after the test completes).  Do not use it
    # as a failure marker.
    criteria = PassCriteria(
        zero_value_regex=r"Total mismatched samples is\s*(\d+)\s+out of\s+\d+\s+samples",
        zero_value_group=1,
    )

    for ip_dir, ip_prefix, tier in ip_families:
        ip_path = root / ip_dir
        if not ip_path.is_dir():
            continue
        for module_dir in sorted(ip_path.iterdir()):
            if not module_dir.is_dir():
                continue
            module_name = module_dir.name
            verif_dir = module_dir / "verification"
            spec_path = module_dir / f"{module_name}.md"
            if not verif_dir.is_dir() or not spec_path.exists():
                continue

            tb_path = verif_dir / f"{module_name}_testbench.sv"
            ref_path = verif_dir / f"{module_name}_ref.sv"
            stim_path = verif_dir / f"{module_name}_stimulus_gen.sv"
            if not tb_path.exists() or not ref_path.exists():
                continue

            # Collect support files (all .v/.sv in verif except tb/ref/top/stim)
            skip_names = {tb_path.name, ref_path.name, stim_path.name,
                          f"{module_name}_top.sv", "Makefile"}
            support_files: list[Path] = [stim_path] if stim_path.exists() else []
            local_names: set[str] = set(skip_names)
            for f in sorted(verif_dir.iterdir()):
                if f.name in skip_names:
                    continue
                if f.suffix in {".v", ".sv"} and f.is_file():
                    support_files.append(f)
                    local_names.add(f.name)

            # No cross-task dep pooling: each task's verification dir should
            # already contain all files needed (per the Makefile's ``*v``
            # pattern).  Failures from missing transitive deps are
            # benchmark defects that we accept rather than papering over.

            # Detect testbench top module name (some use 'tb', some 'tb_<name>')
            import re as _re
            tb_text = tb_path.read_text()
            tb_top_match = _re.search(r"^\s*module\s+(\w+)", tb_text, _re.MULTILINE)
            tb_top = tb_top_match.group(1) if tb_top_match else None

            # No testbench or stimulus patching — we run with verilator,
            # the same simulator the benchmark was developed with.

            task_id = f"realbench_{ip_prefix}_{module_name}"
            public_metadata = _build_public_task_metadata(
                dataset_name=dataset_name,
                task_id=task_id,
                top_module=module_name,
                tier=tier,
            )
            # RealBench was developed and tested with Verilator.
            sim = "verilator"

            oracle = SimulationOracle(
                testbench_path=tb_path,
                gold_rtl_path=ref_path,
                requires_reference_rtl=True,
                candidate_top_module=module_name,
                reference_top_module=f"ref_{module_name}",
                pass_criteria=criteria,
                support_files=tuple(support_files),
                testbench_top_module=tb_top,
                preferred_simulator=sim,
            )
            source_metadata: dict[str, Any] = {
                "origin": "realbench",
                "ip_family": ip_prefix,
                "module": module_name,
            }
            written.append(
                _write_task_bundle(
                    output_root=output,
                    dataset_name=dataset_name,
                    task_id=task_id,
                    spec_source=spec_path.parent,
                    candidate_top_module=module_name,
                    public_metadata=public_metadata,
                    public_interface=None,
                    oracle=oracle,
                    source_metadata=source_metadata,
                    tier=tier,
                )
            )

    return tuple(written)


def store_resbench_tasks(
    json_path: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str = "resbench",
) -> tuple[Path, ...]:
    """Ingest tasks from the ResBench benchmark JSON.

    ResBench provides 56 problems across 12 categories, each with a spec,
    module header, and a self-checking testbench (no gold RTL).  The
    testbench directly instantiates the DUT module by name.
    """
    import tempfile as _tempfile

    data = json.loads(Path(json_path).read_text())
    output = Path(output_root)
    written: list[Path] = []

    _category_tiers: dict[str, Tier] = {
        "Combinational Logic": "micro",
        "Bitwise and Logical Operations": "micro",
        "Basic Arithmetic Operations": "micro",
        "Mathematical Functions": "small",
        "Polynomial Evaluation": "small",
        "Finite State Machines": "small",
        "Pipelining": "small",
        "Machine Learning": "small",
        "Financial Computing": "small",
        "Encryption": "medium",
        "Physics": "small",
        "Climate": "small",
    }

    for category, problems in data.items():
        for problem in problems:
            module_name = str(problem["module"])
            spec_text = str(problem["Problem"])
            header = str(problem.get("Module header") or problem.get("Module Header", ""))
            testbench_text = str(problem["Testbench"])
            task_id = f"resbench_{module_name}"

            # Build a combined spec with the problem description and module header
            full_spec = f"{spec_text}\n\n### Module Header\n\n```verilog\n{header}\n```\n"

            # Write testbench to temp file for the oracle
            with _tempfile.TemporaryDirectory() as tmp:
                tb_path = Path(tmp) / f"{module_name}_tb.v"
                tb_path.write_text(testbench_text)
                # Create a minimal gold stub (oracle only uses the testbench)
                gold_path = Path(tmp) / f"{module_name}_gold.v"
                gold_path.write_text(f"// ResBench gold stub - testbench is the oracle\n{header}\nendmodule\n")

                tier = _category_tiers.get(category, "small")
                public_metadata = _build_public_task_metadata(
                    dataset_name=dataset_name,
                    task_id=task_id,
                    top_module=module_name,
                    tier=tier,
                )
                oracle = SimulationOracle(
                    testbench_path=tb_path,
                    gold_rtl_path=gold_path,
                    requires_reference_rtl=False,
                    candidate_top_module=module_name,
                    reference_top_module=module_name,
                    pass_criteria=PassCriteria(
                        success_markers=("All tests passed",),
                        failure_markers=("Some tests failed",),
                    ),
                )
                source_metadata: dict[str, Any] = {
                    "origin": "resbench",
                    "category": category,
                    "module": module_name,
                }
                written.append(
                    _write_task_bundle(
                        output_root=output,
                        dataset_name=dataset_name,
                        task_id=task_id,
                        spec_source=full_spec,
                        candidate_top_module=module_name,
                        public_metadata=public_metadata,
                        public_interface=None,
                        oracle=oracle,
                        source_metadata=source_metadata,
                        tier=tier,
                    )
                )

    return tuple(written)


def store_icrtl_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str = "icrtl",
) -> tuple[Path, ...]:
    """Ingest tasks from the IC-RTL (EvolVE) benchmark.

    IC-RTL has 6 industry-scale tasks (LBP, GEMM, CONV, HC, JAM, DT).
    Each has a markdown spec, a self-checking testbench with data files,
    and a reference solution.  The testbench references data via
    ``./00_TB/`` paths, so the entire ``00_TB/`` directory is stored as
    a raw oracle directory.
    """
    root = Path(source_root)
    output = Path(output_root)
    written: list[Path] = []

    task_dirs: list[tuple[str, str, str]] = [
        ("Q1_LBP", "lbp", "TOP"),
        ("Q2_GEMM", "gemm", "TOP"),
        ("Q3_CONV", "conv", "TOP"),
        ("Q4_HC", "hc", "TOP"),
        ("Q5_JAM", "jam", "TOP"),
        ("Q6_DT", "dt", "TOP"),
    ]

    for dirname, short_name, top_module in task_dirs:
        task_path = root / dirname
        if not task_path.is_dir():
            continue
        spec_path = task_path / "referenced_spec" / "human.md"
        tb_dir = task_path / "00_TB"
        if not spec_path.exists() or not tb_dir.is_dir():
            continue

        task_id = f"icrtl_{short_name}"
        public_metadata = _build_public_task_metadata(
            dataset_name=dataset_name,
            task_id=task_id,
            top_module=top_module,
            tier="medium",
        )
        oracle_metadata: dict[str, Any] = {
            "kind": "simulation",
            "testbench": "oracle/00_TB/test.sv",
            "gold_rtl": "oracle/gold_rtl.sv",
            "requires_reference_rtl": False,
            "candidate_top_module": top_module,
            "reference_top_module": top_module,
            "pass_criteria": {
                "success_markers": ["All tests PASS!"],
                "failure_markers": ["FAIL"],
                "zero_value_regex": None,
                "zero_value_group": 1,
            },
            "support_files": [],
        }
        source_metadata: dict[str, Any] = {
            "origin": "icrtl",
            "problem": dirname,
            "top_module": top_module,
        }

        # Copy 00_TB as raw oracle dir, add ref solution as gold_rtl
        with tempfile.TemporaryDirectory() as tmp:
            oracle_dir = Path(tmp) / "oracle"
            tb_dest = oracle_dir / "00_TB"
            shutil.copytree(tb_dir, tb_dest)

            ref_sol = task_path / "ref_solution"
            if ref_sol.is_dir():
                # Find the first .sv or .v file
                for f in sorted(ref_sol.iterdir()):
                    if f.suffix in {".sv", ".v"} and f.is_file():
                        shutil.copy2(f, oracle_dir / "gold_rtl.sv")
                        break

            written.append(
                _write_task_bundle(
                    output_root=output,
                    dataset_name=dataset_name,
                    task_id=task_id,
                    spec_source=spec_path.parent,
                    candidate_top_module=top_module,
                    public_metadata=public_metadata,
                    public_interface=None,
                    oracle=None,
                    source_metadata=source_metadata,
                    tier="medium",
                    raw_oracle_dir=oracle_dir,
                    raw_oracle_metadata=oracle_metadata,
                )
            )

    return tuple(written)


def _extract_cocotb_behavioral_spec(test_file: Path) -> str:
    """Extract behavioral specification from a cocotb test file.

    Parses the test to identify which protocols are exercised,
    what test scenarios are covered, and what assertions define
    the behavioral contract.
    """
    import re as _re

    source = test_file.read_text()
    sections: list[str] = []

    # 1. Identify protocols from imports/usage
    protocol_checks = [
        ("AxiMaster", "AXI4 master"),
        ("AxiLiteMaster", "AXI4-Lite master"),
        ("AxiStreamSource", "AXI-Stream source"),
        ("AxiStreamSink", "AXI-Stream sink"),
        ("AxiStreamFrame", "AXI-Stream frames"),
        ("GmiiSource", "GMII source"), ("GmiiSink", "GMII sink"),
        ("RgmiiSource", "RGMII source"), ("RgmiiSink", "RGMII sink"),
        ("XgmiiSource", "XGMII source"), ("XgmiiSink", "XGMII sink"),
        ("MiiSource", "MII source"), ("MiiSink", "MII sink"),
        ("EthMacFrame", "Ethernet MAC frames"),
        ("ArpFrame", "ARP frames"),
        ("PtpClock", "PTP clock"),
    ]
    protocols = [desc for token, desc in protocol_checks if token in source]
    if protocols:
        sections.append(
            "## Protocols Under Test\n\n" + "\n".join(f"- {p}" for p in protocols)
        )

    # 2. Extract test functions with their key operations
    func_re = _re.compile(
        r"^async def (run_test_\w+|run_stress_\w+)\(([^)]*)\):",
        _re.MULTILINE,
    )
    test_descs: list[str] = []
    for match in func_re.finditer(source):
        name = match.group(1)
        start = match.end()
        # Find the end of this function
        next_func = _re.search(r"\n(?:async )?def \w+\(", source[start:])
        body = source[start : start + next_func.start()] if next_func else source[start:]

        ops: list[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("assert "):
                ops.append(f"  - Asserts: `{stripped}`")
            elif _re.match(r".*\b(write|read|send|recv)\(", stripped) and "await" in stripped:
                clean = stripped.split("await ")[-1].split("#")[0].strip()
                ops.append(f"  - `{clean}`")
            elif "log.info" in stripped:
                ops.append(f"  - {stripped}")

        test_descs.append(f"- **{name}**")
        for op in ops[:8]:
            test_descs.append(op)

    if test_descs:
        sections.append("## Behavioral Requirements (from test suite)\n\n" + "\n".join(test_descs))

    # 3. Parameter sweeps from TestFactory
    sweeps: list[str] = []
    for line in source.splitlines():
        if "add_option" in line:
            sweeps.append(f"- `{line.strip()}`")
    if sweeps:
        sections.append(
            "## Parameter Variations\n\nThe test suite sweeps these axes:\n\n"
            + "\n".join(sweeps)
        )

    return "\n\n".join(sections) + "\n" if sections else ""


def store_forencich_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str,
) -> tuple[Path, ...]:
    """Ingest tasks from an Alex Forencich cocotb-tested Verilog repo.

    Works for ``verilog-axi``, ``verilog-ethernet``, and similar repos
    that follow the convention:

    * ``rtl/<module>.v`` — RTL source
    * ``tb/<module>/Makefile`` + ``test_<module>.py`` — cocotb test
    * ``README.md`` — per-module documentation sections

    Each testable module (one per ``tb/*/Makefile``) becomes a task.
    The oracle stores the upstream Makefile + test script and all gold
    RTL files; validation swaps the DUT source(s) for the candidate.
    """
    import re as _re

    root = Path(source_root)
    output = Path(output_root)
    rtl_dir = root / "rtl"
    tb_root = root / "tb"
    readme_path = root / "README.md"
    written: list[Path] = []

    # Parse README for per-module descriptions
    module_docs: dict[str, str] = {}
    if readme_path.exists():
        readme = readme_path.read_text()
        sections = _re.split(r"^### `(\w+)` module", readme, flags=_re.MULTILINE)
        for i in range(1, len(sections) - 1, 2):
            name = sections[i]
            desc = sections[i + 1].strip().split("\n##")[0].strip()
            module_docs[name] = desc

    for tb_dir in sorted(tb_root.iterdir()):
        makefile = tb_dir / "Makefile"
        if not makefile.exists() or not tb_dir.is_dir():
            continue

        makefile_text = makefile.read_text()

        # Extract DUT name and VERILOG_SOURCES
        dut_match = _re.search(r"^DUT\s*=\s*(\S+)", makefile_text, _re.MULTILINE)
        if dut_match is None:
            continue
        dut = dut_match.group(1)

        # Collect RTL source filenames (resolve $(DUT) references)
        raw_sources = _re.findall(r"VERILOG_SOURCES\s*\+=\s*(\S+)", makefile_text)
        source_files: list[str] = []
        for s in raw_sources:
            s = s.replace("$(DUT)", dut)
            s = s.replace("../../rtl/", "")
            if s == "iverilog_dump.v" or s.startswith("$("):
                continue
            source_files.append(s)

        if not source_files:
            continue

        # Verify gold RTL exists for all sources
        gold_paths: list[Path] = []
        skip = False
        for sf in source_files:
            p = rtl_dir / sf
            if p.exists():
                gold_paths.append(p)
            else:
                skip = True
                break
        if skip or not gold_paths:
            continue

        # Extract module header from the DUT file
        dut_rtl_path = gold_paths[0]
        dut_rtl_text = dut_rtl_path.read_text()
        header_match = _re.search(
            r"(module\s+" + _re.escape(dut) + r"\s*(?:#\s*\(.*?\))?\s*\(.*?\)\s*;)",
            dut_rtl_text,
            _re.DOTALL,
        )
        header = header_match.group(1) if header_match else ""

        # Build spec from README description + module header + test behavior
        doc = module_docs.get(dut, f"Implement the `{dut}` module.")
        spec = f"# {dut}\n\n{doc}\n\n## Module Header\n\n```verilog\n{header}\n```\n"

        # Enrich with behavioral spec extracted from the cocotb test
        test_py = tb_dir / f"test_{dut}.py"
        if test_py.exists():
            spec += "\n" + _extract_cocotb_behavioral_spec(test_py)

        task_id = f"{dataset_name}_{dut}"

        # Prepare oracle directory: Makefile + test_*.py + gold RTL
        with tempfile.TemporaryDirectory() as tmp:
            oracle_dir = Path(tmp) / "oracle"
            test_dir = oracle_dir / "test"
            gold_dir = oracle_dir / "rtl"
            test_dir.mkdir(parents=True)
            gold_dir.mkdir(parents=True)

            # Copy Makefile and test scripts
            shutil.copy2(makefile, test_dir / "Makefile")
            for f in tb_dir.iterdir():
                if f.name.endswith(".py") and f.is_file():
                    shutil.copy2(f, test_dir / f.name)

            # Copy ALL gold RTL files
            for p in gold_paths:
                shutil.copy2(p, gold_dir / p.name)

            # Copy any generated wrapper files from the tb dir
            for f in tb_dir.iterdir():
                if f.suffix == ".v" and f.is_file():
                    shutil.copy2(f, gold_dir / f.name)

            oracle_metadata: dict[str, Any] = {
                "kind": "makefile_cocotb",
                "test_dir": "oracle/test",
                "gold_rtl_dir": "oracle/rtl",
                "dut": dut,
                "dut_source_files": [source_files[0]],
                "dep_source_files": source_files[1:],
            }

            public_metadata = _build_public_task_metadata(
                dataset_name=dataset_name,
                task_id=task_id,
                top_module=dut,
                tier="medium",
            )

            source_metadata_dict: dict[str, Any] = {
                "origin": dataset_name,
                "dut": dut,
                "source_files": source_files,
            }

            written.append(
                _write_task_bundle(
                    output_root=output,
                    dataset_name=dataset_name,
                    task_id=task_id,
                    spec_source=spec,
                    candidate_top_module=dut,
                    public_metadata=public_metadata,
                    public_interface=None,
                    oracle=None,
                    source_metadata=source_metadata_dict,
                    tier="medium",
                    raw_oracle_dir=oracle_dir,
                    raw_oracle_metadata=oracle_metadata,
                )
            )

    return tuple(written)


def store_pulp_common_cells_tasks(
    source_root: str | Path,
    output_root: str | Path,
    *,
    dataset_name: str = "pulp_common_cells",
) -> tuple[Path, ...]:
    """Ingest tasks from PULP Platform common_cells.

    Each ``test/*_tb.sv`` file becomes a task.  The DUT is the primary
    module tested, and its transitive dependencies are resolved from
    ``src/``.  The oracle uses xrun with ``+incdir`` for assertion macros.
    """
    import re as _re

    root = Path(source_root)
    output = Path(output_root)
    src_dir = root / "src"
    test_dir = root / "test"
    include_dir = root / "include"
    written: list[Path] = []

    # Build module/package -> file map
    mod_files: dict[str, Path] = {}
    for f in sorted(src_dir.glob("*.sv")):
        for m in _re.finditer(r"(?:^|\s)(?:module|package)\s+(\w+)", f.read_text()):
            mod_files[m.group(1)] = f

    # Resolve transitive deps for a testbench
    def _resolve_deps(tb_path: Path) -> list[Path]:
        text = tb_path.read_text()
        refs = set(_re.findall(r"\b(\w+)\s+(?:#\s*\(|i_)", text))
        refs |= set(_re.findall(r"import\s+(\w+)::", text))
        checked: set[str] = set()
        queue = [mod_files[r].name for r in refs if r in mod_files]
        while queue:
            fname = queue.pop()
            if fname in checked:
                continue
            checked.add(fname)
            fpath = src_dir / fname
            if fpath.exists():
                ftext = fpath.read_text()
                for inst in _re.findall(r"\b(\w+)\s+(?:#\s*\(|i_)", ftext):
                    if inst in mod_files and mod_files[inst].name not in checked:
                        queue.append(mod_files[inst].name)
                for imp in _re.findall(r"import\s+(\w+)::", ftext):
                    if imp in mod_files and mod_files[imp].name not in checked:
                        queue.append(mod_files[imp].name)
        return sorted(set(src_dir / n for n in checked if (src_dir / n).exists()))

    for tb in sorted(test_dir.glob("*_tb.sv")):
        tb_text = tb.read_text()
        if "rand_verif_pkg" in tb_text:
            continue

        dut_name = tb.stem.replace("_tb", "")
        if dut_name not in mod_files:
            continue
        dut_file = mod_files[dut_name]

        all_deps = _resolve_deps(tb)
        dep_files = [f for f in all_deps if f != dut_file]

        dut_text = dut_file.read_text()
        header_match = _re.search(
            r"(module\s+" + _re.escape(dut_name) + r"\s*(?:#\s*\(.*?\))?\s*\(.*?\)\s*;)",
            dut_text, _re.DOTALL,
        )
        header = header_match.group(1) if header_match else ""
        spec = (
            f"# {dut_name}\n\n"
            f"PULP Platform common_cells component.\n\n"
            f"## Module Header\n\n```systemverilog\n{header}\n```\n"
        )

        task_id = f"{dataset_name}_{dut_name}"

        with tempfile.TemporaryDirectory() as tmp:
            oracle_dir = Path(tmp) / "oracle"
            deps_dir = oracle_dir / "deps"
            incl_dir = oracle_dir / "include" / "common_cells"
            deps_dir.mkdir(parents=True)
            incl_dir.mkdir(parents=True)

            for f in dep_files:
                shutil.copy2(f, deps_dir / f.name)
            shutil.copy2(dut_file, deps_dir / dut_file.name)
            shutil.copy2(tb, oracle_dir / tb.name)
            for hdr in (include_dir / "common_cells").glob("*.svh"):
                shutil.copy2(hdr, incl_dir / hdr.name)

            oracle_metadata: dict[str, Any] = {
                "kind": "pulp_xrun",
                "testbench": f"oracle/{tb.name}",
                "tb_top": tb.stem,
                "dep_dir": "oracle/deps",
                "include_dir": "oracle/include",
                "dut": dut_name,
                "dut_source_file": dut_file.name,
            }

            public_metadata = _build_public_task_metadata(
                dataset_name=dataset_name,
                task_id=task_id,
                top_module=dut_name,
                tier="small",
            )

            source_meta: dict[str, Any] = {
                "origin": dataset_name,
                "dut": dut_name,
                "dep_files": [f.name for f in dep_files],
            }

            written.append(
                _write_task_bundle(
                    output_root=output,
                    dataset_name=dataset_name,
                    task_id=task_id,
                    spec_source=spec,
                    candidate_top_module=dut_name,
                    public_metadata=public_metadata,
                    public_interface=None,
                    oracle=None,
                    source_metadata=source_meta,
                    tier="small",
                    raw_oracle_dir=oracle_dir,
                    raw_oracle_metadata=oracle_metadata,
                )
            )

    return tuple(written)
