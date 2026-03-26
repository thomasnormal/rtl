from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any


def _sanitize_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return sanitized.strip("-") or "bundle"


def _git_output(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ("git", "-C", str(root), *args),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip()


@dataclass(frozen=True)
class SharedSourceBundle:
    bundle_id: str
    name: str
    root: Path
    source_kind: str
    git_commit: str | None
    git_dirty: bool | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SharedSourceBundle":
        return cls(
            bundle_id=str(raw["bundle_id"]),
            name=str(raw["name"]),
            root=Path(str(raw["root"])).resolve(),
            source_kind=str(raw["source_kind"]),
            git_commit=None if raw.get("git_commit") is None else str(raw["git_commit"]),
            git_dirty=None if raw.get("git_dirty") is None else bool(raw["git_dirty"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "name": self.name,
            "root": str(self.root),
            "source_kind": self.source_kind,
            "git_commit": self.git_commit,
            "git_dirty": self.git_dirty,
        }


@dataclass(frozen=True)
class SharedSourceRegistry:
    path: Path
    bundles: tuple[SharedSourceBundle, ...]

    @classmethod
    def load(cls, path: str | Path) -> "SharedSourceRegistry":
        registry_path = Path(path).resolve()
        if not registry_path.exists():
            return cls(path=registry_path, bundles=())
        raw = json.loads(registry_path.read_text())
        raw_bundles = raw.get("bundles", [])
        if not isinstance(raw_bundles, list):
            raise ValueError(f"shared source registry at {registry_path} must contain a bundles list")
        return cls(
            path=registry_path,
            bundles=tuple(
                SharedSourceBundle.from_dict(dict(item))
                for item in raw_bundles
                if isinstance(item, dict)
            ),
        )

    def by_id(self, bundle_id: str) -> SharedSourceBundle:
        for bundle in self.bundles:
            if bundle.bundle_id == bundle_id:
                return bundle
        raise KeyError(bundle_id)

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"bundles": [bundle.to_dict() for bundle in self.bundles]}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def detect_source_bundle(source_root: str | Path, *, name: str) -> SharedSourceBundle:
    root = Path(source_root).expanduser().resolve()
    git_commit = _git_output(root, "rev-parse", "HEAD")
    if git_commit is not None:
        dirty_output = _git_output(root, "status", "--porcelain")
        git_dirty = bool(dirty_output)
        suffix = git_commit[:12]
        if git_dirty:
            suffix += "-dirty"
        return SharedSourceBundle(
            bundle_id=f"{_sanitize_name(name)}-{suffix}",
            name=name,
            root=root,
            source_kind="git_checkout",
            git_commit=git_commit,
            git_dirty=git_dirty,
        )
    return SharedSourceBundle(
        bundle_id=f"{_sanitize_name(name)}-local",
        name=name,
        root=root,
        source_kind="directory",
        git_commit=None,
        git_dirty=None,
    )


def register_shared_source_bundle(
    registry_root: str | Path,
    *,
    name: str,
    source_root: str | Path,
) -> SharedSourceBundle:
    registry_path = Path(registry_root).resolve() / "registry.json"
    registry = SharedSourceRegistry.load(registry_path)
    bundle = detect_source_bundle(source_root, name=name)

    existing: list[SharedSourceBundle] = []
    replaced = False
    for current in registry.bundles:
        if current.bundle_id == bundle.bundle_id:
            existing.append(bundle)
            replaced = True
        else:
            existing.append(current)
    if not replaced:
        existing.append(bundle)

    SharedSourceRegistry(path=registry_path, bundles=tuple(existing)).write()
    return bundle

