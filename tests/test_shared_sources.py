from pathlib import Path

from rtl_training.shared_sources import (
    SharedSourceRegistry,
    detect_source_bundle,
    register_shared_source_bundle,
)


def test_detect_source_bundle_for_plain_directory(tmp_path: Path) -> None:
    bundle = detect_source_bundle(tmp_path, name="example")

    assert bundle.name == "example"
    assert bundle.root == tmp_path.resolve()
    assert bundle.source_kind == "directory"
    assert bundle.git_commit is None
    assert bundle.git_dirty is None
    assert bundle.bundle_id == "example-local"


def test_register_shared_source_bundle_round_trips_git_metadata(tmp_path: Path) -> None:
    source_root = tmp_path / "repo"
    source_root.mkdir()

    # Initialize a minimal git checkout with one committed file and one dirty change.
    import subprocess

    subprocess.run(("git", "-C", str(source_root), "init"), check=True, capture_output=True, text=True)
    subprocess.run(
        ("git", "-C", str(source_root), "config", "user.email", "test@example.com"),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ("git", "-C", str(source_root), "config", "user.name", "Test User"),
        check=True,
        capture_output=True,
        text=True,
    )
    (source_root / "file.txt").write_text("v1\n")
    subprocess.run(
        ("git", "-C", str(source_root), "add", "file.txt"),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ("git", "-C", str(source_root), "commit", "-m", "init"),
        check=True,
        capture_output=True,
        text=True,
    )
    (source_root / "file.txt").write_text("v2\n")

    bundle = register_shared_source_bundle(
        tmp_path / "shared_sources",
        name="opentitan_ip_docs",
        source_root=source_root,
    )
    registry = SharedSourceRegistry.load(tmp_path / "shared_sources" / "registry.json")
    stored = registry.by_id(bundle.bundle_id)

    assert stored.root != source_root.resolve()
    assert stored.root.exists()
    assert stored.source_kind == "git_snapshot"
    assert stored.git_commit is not None
    assert stored.git_dirty is False
    assert stored.bundle_id == f"opentitan_ip_docs-{stored.git_commit[:12]}"
    assert (stored.root / "file.txt").read_text() == "v1\n"


def test_register_shared_source_bundle_prunes_live_checkout_entry_when_snapshotting(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "repo"
    source_root.mkdir()

    import subprocess

    subprocess.run(("git", "-C", str(source_root), "init"), check=True, capture_output=True, text=True)
    subprocess.run(
        ("git", "-C", str(source_root), "config", "user.email", "test@example.com"),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ("git", "-C", str(source_root), "config", "user.name", "Test User"),
        check=True,
        capture_output=True,
        text=True,
    )
    (source_root / "file.txt").write_text("v1\n")
    subprocess.run(
        ("git", "-C", str(source_root), "add", "file.txt"),
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ("git", "-C", str(source_root), "commit", "-m", "init"),
        check=True,
        capture_output=True,
        text=True,
    )
    (source_root / "file.txt").write_text("v2\n")

    registry_root = tmp_path / "shared_sources"
    live = register_shared_source_bundle(
        registry_root,
        name="opentitan_ip_docs",
        source_root=source_root,
        freeze_git_checkout=False,
    )
    assert live.source_kind == "git_checkout"

    frozen = register_shared_source_bundle(
        registry_root,
        name="opentitan_ip_docs",
        source_root=source_root,
    )
    registry = SharedSourceRegistry.load(registry_root / "registry.json")

    assert frozen.source_kind == "git_snapshot"
    assert registry.bundles == (frozen,)
