from pathlib import Path

from rtl_training.task_store import load_stored_task, store_opentitan_ip_docs_tasks


_OPENTITAN_IPS = (
    "adc_ctrl",
    "aon_timer",
    "dma",
    "i2c",
    "pattgen",
    "rv_timer",
    "spi_host",
    "sysrst_ctrl",
    "uart",
)


def _collect_relevant_opentitan_public_files(ip_root: Path) -> set[str]:
    files: set[str] = set()
    allowed_suffixes = {".md", ".svg", ".png", ".hjson", ".tpl", ".txt", ".rst", ".pdf"}

    readme = ip_root / "README.md"
    if readme.is_file():
        files.add("README.md")

    for subdir_name in ("doc", "data", "dv"):
        subdir = ip_root / subdir_name
        if not subdir.is_dir():
            continue
        for path in sorted(subdir.rglob("*")):
            if path.is_file() and path.suffix in allowed_suffixes:
                files.add(str(path.relative_to(ip_root)))

    return files


def test_store_opentitan_tasks_mirror_relevant_public_docs_from_upstream(tmp_path: Path) -> None:
    source_root = Path("~/opentitan").expanduser().resolve()
    store_opentitan_ip_docs_tasks(
        tmp_path / "task_store",
        source_root=source_root,
    )

    for task_name in _OPENTITAN_IPS:
        task = load_stored_task(tmp_path / "task_store" / "opentitan_ip_docs" / task_name)
        mirrored = {
            str(path.relative_to(task.spec_dir))
            for path in task.spec_dir.rglob("*")
            if path.is_file()
        }
        expected = _collect_relevant_opentitan_public_files(source_root / "hw" / "ip" / task_name)
        missing = sorted(expected - mirrored)
        assert not missing, f"{task_name} missing public upstream docs: {missing}"
