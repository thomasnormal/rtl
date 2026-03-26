from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from rtl_training.opentitan_oracle import (
    build_opentitan_candidate_validation_plan,
    build_opentitan_gold_selftest_plan,
    run_opentitan_dvsim_plan,
)
from rtl_training.shared_sources import SharedSourceBundle, SharedSourceRegistry
from rtl_training.task_store import load_stored_task


def _write_fake_opentitan_task(task_root: Path, repo_root: Path, registry_path: Path) -> None:
    (task_root / "public" / "spec").mkdir(parents=True)
    (task_root / "public" / "spec" / "README.md").write_text("uart spec\n")
    (task_root / "public" / "spec" / "interface").mkdir(parents=True)
    (task_root / "public" / "spec" / "compat").mkdir(parents=True)
    (task_root / "public" / "spec" / "interface" / "uart_public_types_pkg.sv").write_text(
        "package uart_public_types_pkg;\n"
        "  typedef logic [108:0] uart_tl_i_t;\n"
        "  typedef logic [65:0] uart_tl_o_t;\n"
        "endpackage\n"
    )
    (task_root / "public" / "spec" / "compat" / "uart_compat_if.sv").write_text(
        "interface uart_compat_if; endinterface\n"
    )
    (task_root / "public" / "spec" / "compat" / "uart_compat_checker.sv").write_text(
        "module uart_compat_checker(uart_compat_if compat_if); endmodule\n"
    )
    (task_root / "public" / "spec" / "compat" / "uart_compat_bind.sv").write_text(
        "module uart_compat_bind;\n"
        "  bind uart uart_compat_checker u_uart_compat_checker(.compat_if(u_uart_compat_if));\n"
        "endmodule\n"
    )
    (task_root / "public" / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan_ip_docs",
                "task_id": "uart",
                "candidate_top_module": "uart",
                "interface": {
                    "top_module": "uart",
                    "declared_module_name": "uart",
                    "ports": [],
                    "inputs": [],
                    "outputs": [],
                    "parameters": [],
                },
                "spec": "spec/",
            },
            indent=2,
        )
        + "\n"
    )
    (task_root / "oracle" / "golden_rtl").mkdir(parents=True)
    (task_root / "oracle" / "golden_rtl" / "uart.sv").write_text("module uart; // golden\nendmodule\n")
    (task_root / "oracle" / "golden_rtl" / "uart_core.sv").write_text("module uart_core; endmodule\n")

    SharedSourceRegistry(
        path=registry_path,
        bundles=(
            SharedSourceBundle(
                bundle_id="opentitan-test",
                name="opentitan_ip_docs",
                root=repo_root.resolve(),
                source_kind="directory",
                git_commit=None,
                git_dirty=None,
            ),
        ),
    ).write()

    (task_root / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan_ip_docs",
                "task_id": "uart",
                "public": {
                    "directory": "public",
                    "spec": "public/spec/",
                    "task": "public/task.json",
                },
                "shared_private": {
                    "registry": os.path.relpath(registry_path, task_root),
                    "bundle_id": "opentitan-test",
                    "subpaths": ["hw/ip/uart/rtl", "hw/ip/uart/dv"],
                },
                "oracle": {
                    "kind": "opentitan_dvsim",
                    "cfg": "hw/ip/uart/dv/uart_sim_cfg.hjson",
                    "test": "uart_smoke",
                    "tool": "xcelium",
                    "golden_rtl_dir": "golden_rtl",
                    "overlay_rel_dir": "hw/ip/uart/rtl",
                },
                "source": {
                    "source_root": str(repo_root.resolve()),
                    "public_interface_internal": {
                        "profile": "opentitan_self_contained_v1",
                        "native_interface": {
                            "top_module": "uart",
                            "declared_module_name": "uart",
                            "parameters": [],
                            "ports": [
                                {"name": "clk_i", "direction": "input", "width": "logic"},
                                {"name": "rst_ni", "direction": "input", "width": "logic"},
                                {
                                    "name": "tl_i",
                                    "direction": "input",
                                    "width": "tlul_pkg::tl_h2d_t",
                                },
                                {
                                    "name": "tl_o",
                                    "direction": "output",
                                    "width": "tlul_pkg::tl_d2h_t",
                                },
                            ],
                            "inputs": [],
                            "outputs": [],
                            "modports": [],
                        },
                        "projection": {
                            "types_package": "uart_public_types_pkg",
                            "support_files": ["uart_public_types_pkg.sv"],
                            "ports": [
                                {
                                    "name": "clk_i",
                                    "direction": "input",
                                    "native_type": "logic",
                                    "public_type": "logic",
                                    "cast_required": False,
                                },
                                {
                                    "name": "rst_ni",
                                    "direction": "input",
                                    "native_type": "logic",
                                    "public_type": "logic",
                                    "cast_required": False,
                                },
                                {
                                    "name": "tl_i",
                                    "direction": "input",
                                    "native_type": "tlul_pkg::tl_h2d_t",
                                    "public_type": "uart_public_types_pkg::uart_tl_i_t",
                                    "cast_required": True,
                                },
                                {
                                    "name": "tl_o",
                                    "direction": "output",
                                    "native_type": "tlul_pkg::tl_d2h_t",
                                    "public_type": "uart_public_types_pkg::uart_tl_o_t",
                                    "cast_required": True,
                                },
                            ],
                        },
                    },
                },
            },
            indent=2,
        )
        + "\n"
    )


def test_build_opentitan_gold_selftest_plan_overlays_golden_rtl(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo_src"
    (repo_root / "util" / "dvsim").mkdir(parents=True)
    (repo_root / "util" / "dvsim" / "dvsim.py").write_text("print('fake dvsim')\n")
    (repo_root / "hw" / "ip" / "uart" / "rtl").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").write_text("module uart; // live\nendmodule\n")
    (repo_root / "hw" / "ip" / "uart" / "dv").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim_cfg.hjson").write_text("name: uart\n")

    task_root = tmp_path / "task"
    registry_path = tmp_path / "registry" / "registry.json"
    _write_fake_opentitan_task(task_root, repo_root, registry_path)
    task = load_stored_task(task_root)

    plan = build_opentitan_gold_selftest_plan(task, work_root=tmp_path / "work")

    assert plan.repo_root.exists()
    assert (plan.repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").read_text() == (
        "module uart; // golden\nendmodule\n"
    )
    assert (plan.repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim_cfg.hjson").exists()
    assert (plan.repo_root / "hw" / "ip" / "uart" / "dv" / "compat" / "uart_compat_if.sv").exists()
    assert (
        plan.repo_root / "hw" / "ip" / "uart" / "dv" / "compat" / "uart_compat_bind.sv"
    ).read_text().strip() == "module uart_compat_bind; endmodule : uart_compat_bind"
    assert plan.command[1] == "util/dvsim/dvsim.py"
    assert plan.command[2] == "hw/ip/uart/dv/uart_sim_cfg.hjson"
    assert plan.command[4] == "uart_smoke"
    assert "--proj-root" in plan.command
    assert str(plan.repo_root) in plan.command


def test_run_opentitan_dvsim_plan_invokes_dvsim_from_overlaid_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo_src"
    (repo_root / "util" / "dvsim").mkdir(parents=True)
    (repo_root / "util" / "dvsim" / "dvsim.py").write_text("print('fake dvsim')\n")
    (repo_root / "hw" / "ip" / "uart" / "rtl").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").write_text("module uart; // live\nendmodule\n")
    (repo_root / "hw" / "ip" / "uart" / "dv").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim_cfg.hjson").write_text("name: uart\n")

    task_root = tmp_path / "task"
    registry_path = tmp_path / "registry" / "registry.json"
    _write_fake_opentitan_task(task_root, repo_root, registry_path)
    task = load_stored_task(task_root)
    plan = build_opentitan_gold_selftest_plan(task, work_root=tmp_path / "work")

    captured: dict[str, object] = {}

    def fake_run(command, *, cwd, capture_output, text, timeout, check):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["overlay_text"] = (plan.repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").read_text()
        return subprocess.CompletedProcess(command, 0, stdout="PASS\n", stderr="")

    monkeypatch.setattr("rtl_training.opentitan_oracle.subprocess.run", fake_run)

    result = run_opentitan_dvsim_plan(plan, timeout_s=30)

    assert result.passed is True
    assert Path(captured["cwd"]) == plan.repo_root
    assert captured["overlay_text"] == "module uart; // golden\nendmodule\n"
    command = captured["command"]
    assert isinstance(command, tuple)
    assert "--scratch-root" in command
    assert plan.log_path.read_text() == "PASS\n"


def test_build_opentitan_candidate_validation_plan_wraps_projected_candidate(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo_src"
    (repo_root / "util" / "dvsim").mkdir(parents=True)
    (repo_root / "util" / "dvsim" / "dvsim.py").write_text("print('fake dvsim')\n")
    (repo_root / "hw" / "ip" / "uart" / "rtl").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").write_text(
        "module uart(\n"
        "  input logic clk_i,\n"
        "  input logic rst_ni,\n"
        "  input tlul_pkg::tl_h2d_t tl_i,\n"
        "  output tlul_pkg::tl_d2h_t tl_o\n"
        ");\n"
        "endmodule\n"
    )
    (repo_root / "hw" / "ip" / "uart" / "dv").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim_cfg.hjson").write_text("name: uart\n")

    task_root = tmp_path / "task"
    registry_path = tmp_path / "registry" / "registry.json"
    _write_fake_opentitan_task(task_root, repo_root, registry_path)
    task = load_stored_task(task_root)

    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "uart.sv").write_text(
        "module uart(\n"
        "  input logic clk_i,\n"
        "  input logic rst_ni,\n"
        "  input uart_public_types_pkg::uart_tl_i_t tl_i,\n"
        "  output uart_public_types_pkg::uart_tl_o_t tl_o\n"
        ");\n"
        "endmodule\n"
    )

    plan = build_opentitan_candidate_validation_plan(
        task,
        candidate_dir=candidate_dir,
        work_root=tmp_path / "work",
    )

    overlay_dir = plan.repo_root / "hw" / "ip" / "uart" / "rtl"
    wrapper_text = (overlay_dir / "uart.sv").read_text()
    assert "`include \"uart_public_types_pkg.sv\"" in wrapper_text
    assert "`include \"candidate/uart_candidate.sv\"" in wrapper_text
    assert "module uart(" in wrapper_text
    assert "uart_public_types_pkg::uart_tl_i_t candidate_tl_i;" in wrapper_text
    assert "assign candidate_tl_i = uart_public_types_pkg::uart_tl_i_t'(tl_i);" in wrapper_text
    assert "assign tl_o = tlul_pkg::tl_d2h_t'(candidate_tl_o);" in wrapper_text
    renamed_candidate = (overlay_dir / "candidate" / "uart_candidate.sv").read_text()
    assert "module uart_candidate(" in renamed_candidate
