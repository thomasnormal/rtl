from pathlib import Path

from rtl_training.task_store import load_stored_task, store_opentitan_tasks


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

_FORBIDDEN_PUBLIC_PATTERNS = (
    "OpenTitan",
    "Comportable",
    "reports.opentitan.org",
    "dashboards.lowrisc.org",
    "hw/ip/",
    "hw/dv/",
    "$REPO_TOP",
    "cip_lib",
    "dvsim.py",
    "regtool.py",
    "github.com/lowRISC/opentitan",
)


def test_store_opentitan_tasks_materialize_task_facing_public_docs(tmp_path: Path) -> None:
    source_root = Path("~/opentitan").expanduser().resolve()
    store_opentitan_tasks(
        tmp_path / "task_store",
        source_root=source_root,
    )

    for task_name in _OPENTITAN_IPS:
        task = load_stored_task(tmp_path / "task_store" / "opentitan" / task_name)
        spec_dir = task.spec_dir

        assert (spec_dir / "README.md").is_file(), task_name
        assert (spec_dir / "doc" / "interfaces.md").is_file(), task_name
        assert (spec_dir / "doc" / "registers.md").is_file(), task_name
        assert (spec_dir / "doc" / "theory_of_operation.md").is_file(), task_name
        assert (spec_dir / "dv" / "README.md").is_file(), task_name
        assert (spec_dir / "interface").is_dir(), task_name
        assert (spec_dir / "micro_arch").is_dir(), task_name

        assert not any((spec_dir / "data").glob("*testplan*.hjson")), task_name
        assert not any((spec_dir / "dv").glob("*_sim_cfg.hjson")), task_name
        assert not (spec_dir / "doc" / "checklist.md").exists(), task_name


def test_store_opentitan_tasks_strip_upstream_repo_noise_from_public_docs(tmp_path: Path) -> None:
    source_root = Path("~/opentitan").expanduser().resolve()
    store_opentitan_tasks(
        tmp_path / "task_store",
        source_root=source_root,
    )

    for task_name in _OPENTITAN_IPS:
        task = load_stored_task(tmp_path / "task_store" / "opentitan" / task_name)
        for path in sorted(task.spec_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in {".md", ".hjson"}:
                continue
            text = path.read_text()
            for pattern in _FORBIDDEN_PUBLIC_PATTERNS:
                assert pattern not in text, f"{task_name} leaked {pattern!r} in {path.relative_to(task.spec_dir)}"
