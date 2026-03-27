from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from rtl_training.opentitan_oracle import (
    build_opentitan_candidate_validation_plan,
    build_opentitan_gold_selftest_plan,
    build_opentitan_mutant_plan,
    run_opentitan_dvsim_plan,
)
from rtl_training.shared_sources import SharedSourceBundle, SharedSourceRegistry
from rtl_training.task_store import load_stored_task


def _write_fake_uart_dv_files(repo_root: Path) -> None:
    (repo_root / "hw" / "ip" / "uart" / "dv").mkdir(parents=True, exist_ok=True)
    (repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim_cfg.hjson").write_text("name: uart\n")
    (repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim.core").write_text(
        "\n".join(
            [
                "CAPI=2:",
                'name: "lowrisc:dv:uart_sim:0.1"',
                "filesets:",
                "  files_dv:",
                "    files:",
                "      - tb/tb.sv",
                "    file_type: systemVerilogSource",
                "",
            ]
        )
    )


def _write_fake_opentitan_task(task_root: Path, repo_root: Path, registry_path: Path) -> None:
    (task_root / "public" / "spec").mkdir(parents=True)
    (task_root / "public" / "spec" / "README.md").write_text("uart spec\n")
    (task_root / "public" / "spec" / "interface").mkdir(parents=True)
    (task_root / "public" / "spec" / "micro_arch").mkdir(parents=True)
    (task_root / "public" / "spec" / "micro_arch" / "README.md").write_text("uart micro arch\n")
    (task_root / "public" / "spec" / "interface" / "uart_public_types_pkg.sv").write_text(
        "package uart_public_types_pkg;\n"
        "  typedef logic [108:0] uart_tl_i_t;\n"
        "  typedef logic [3:0] uart_alert_rx_i_t;\n"
        "  typedef logic [65:0] uart_tl_o_t;\n"
        "  typedef logic [1:0] uart_alert_tx_o_t;\n"
        "endpackage\n"
    )
    (task_root / "public" / "spec" / "interface" / "uart_public_if.sv").write_text(
        "`include \"uart_public_types_pkg.sv\"\n"
        "interface uart_public_if;\n"
        "  logic clk_i;\n"
        "  logic rst_ni;\n"
        "  uart_public_types_pkg::uart_tl_i_t tl_i;\n"
        "  uart_public_types_pkg::uart_alert_rx_i_t alert_rx_i;\n"
        "  uart_public_types_pkg::uart_tl_o_t tl_o;\n"
        "  uart_public_types_pkg::uart_alert_tx_o_t alert_tx_o;\n"
        "  modport dut (\n"
        "    input clk_i,\n"
        "    input rst_ni,\n"
        "    input tl_i,\n"
        "    input alert_rx_i,\n"
        "    output tl_o,\n"
        "    output alert_tx_o\n"
        "  );\n"
        "  modport tb (\n"
        "    output clk_i,\n"
        "    output rst_ni,\n"
        "    output tl_i,\n"
        "    output alert_rx_i,\n"
        "    input tl_o,\n"
        "    input alert_tx_o\n"
        "  );\n"
        "endinterface\n"
    )
    (task_root / "public" / "spec" / "micro_arch" / "uart_micro_arch_if.sv").write_text(
        "interface uart_micro_arch_if;\n"
        "  logic rx_sync;\n"
        "  modport dut (output rx_sync);\n"
        "  modport mon (input rx_sync);\n"
        "endinterface\n"
    )
    (task_root / "public" / "spec" / "micro_arch" / "uart_micro_arch_checker.sv").write_text(
        "module uart_micro_arch_checker(uart_micro_arch_if.mon micro_arch_if); endmodule\n"
    )
    (task_root / "public" / "spec" / "micro_arch" / "uart_micro_arch_bind.sv").write_text(
        "module uart_micro_arch_bind;\n"
        "  bind uart uart_micro_arch_checker u_uart_micro_arch_checker(.micro_arch_if(u_uart_micro_arch_if));\n"
        "endmodule\n"
    )
    (task_root / "public" / "task.json").write_text(
        json.dumps(
            {
                "dataset_name": "opentitan_ip_docs",
                "task_id": "uart",
                "top_module": "uart",
                "deliverables": {
                    "rtl": "submission/",
                    "summary": "result/result.json",
                },
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
                    "mutants": [
                        {
                            "name": "flip_uart_comment",
                            "edits": [
                                {
                                    "path": "uart.sv",
                                    "find": "// golden",
                                    "replace": "// mutated",
                                }
                            ],
                        }
                    ],
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
                                    "name": "alert_rx_i",
                                    "direction": "input",
                                    "native_type": "prim_alert_pkg::alert_rx_t [NumAlerts-1:0]",
                                    "public_type": "uart_public_types_pkg::uart_alert_rx_i_t",
                                    "cast_required": True,
                                },
                                {
                                    "name": "tl_o",
                                    "direction": "output",
                                    "native_type": "tlul_pkg::tl_d2h_t",
                                    "public_type": "uart_public_types_pkg::uart_tl_o_t",
                                    "cast_required": True,
                                },
                                {
                                    "name": "alert_tx_o",
                                    "direction": "output",
                                    "native_type": "prim_alert_pkg::alert_tx_t [NumAlerts-1:0]",
                                    "public_type": "uart_public_types_pkg::uart_alert_tx_o_t",
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
    _write_fake_uart_dv_files(repo_root)

    task_root = tmp_path / "task"
    registry_path = tmp_path / "registry" / "registry.json"
    _write_fake_opentitan_task(task_root, repo_root, registry_path)
    task = load_stored_task(task_root)

    plan = build_opentitan_gold_selftest_plan(task, work_root=tmp_path / "work")

    assert plan.repo_root.exists()
    wrapper_text = (plan.repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").read_text()
    assert "module uart; // golden" in wrapper_text
    assert "uart_micro_arch_if u_uart_micro_arch_if();" in wrapper_text
    assert "assign u_uart_micro_arch_if.rx_sync = '0;" in wrapper_text
    assert (plan.repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim_cfg.hjson").exists()
    assert (plan.repo_root / "hw" / "ip" / "uart" / "dv" / "micro_arch" / "uart_micro_arch_if.sv").exists()
    assert (
        plan.repo_root / "hw" / "ip" / "uart" / "dv" / "micro_arch" / "uart_micro_arch_bind.sv"
    ).read_text().strip().startswith("module uart_micro_arch_bind;")
    sim_core_text = (plan.repo_root / "hw" / "ip" / "uart" / "dv" / "uart_sim.core").read_text()
    assert "      - micro_arch/uart_micro_arch_if.sv" in sim_core_text
    assert "      - micro_arch/uart_micro_arch_checker.sv" in sim_core_text
    assert "      - micro_arch/uart_micro_arch_bind.sv" in sim_core_text
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
    _write_fake_uart_dv_files(repo_root)

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
    assert isinstance(captured["overlay_text"], str)
    assert "module uart; // golden" in captured["overlay_text"]
    assert "uart_micro_arch_if u_uart_micro_arch_if();" in captured["overlay_text"]
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
        "module uart\n"
        "  import uart_reg_pkg::*;\n"
        "#(\n"
        "  parameter int NumAlerts = 2,\n"
        "  parameter int AlertAsyncOn = 1\n"
        ") (\n"
        "  input logic clk_i,\n"
        "  input logic rst_ni,\n"
        "  input tlul_pkg::tl_h2d_t tl_i,\n"
        "  input prim_alert_pkg::alert_rx_t [NumAlerts-1:0] alert_rx_i,\n"
        "  output tlul_pkg::tl_d2h_t tl_o,\n"
        "  output prim_alert_pkg::alert_tx_t [NumAlerts-1:0] alert_tx_o\n"
        ");\n"
        "endmodule\n"
    )
    _write_fake_uart_dv_files(repo_root)

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
        "  input uart_public_types_pkg::uart_alert_rx_i_t alert_rx_i,\n"
        "  output uart_public_types_pkg::uart_tl_o_t tl_o,\n"
        "  output uart_public_types_pkg::uart_alert_tx_o_t alert_tx_o\n"
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
    assert "`include \"uart_public_types_pkg.sv\"" not in wrapper_text
    assert "`include \"candidate/uart_candidate.sv\"" not in wrapper_text
    assert "package uart_public_types_pkg;" in wrapper_text
    assert "module uart_candidate(" in wrapper_text
    assert "module uart\n  import uart_reg_pkg::*;\n#(" in wrapper_text
    assert "public_cast_tl_i_t candidate_tl_i;" in wrapper_text
    assert (
        "typedef prim_alert_pkg::alert_tx_t [NumAlerts-1:0] native_cast_alert_tx_o_t;" in wrapper_text
    )
    assert "uart_micro_arch_if u_uart_micro_arch_if();" in wrapper_text
    assert "assign u_uart_micro_arch_if.rx_sync = u_candidate.u_uart_micro_arch_if.rx_sync;" in wrapper_text
    assert "assign candidate_tl_i = public_cast_tl_i_t'(tl_i);" in wrapper_text
    assert "assign tl_o = native_cast_tl_o_t'(candidate_tl_o);" in wrapper_text
    assert "assign alert_tx_o = native_cast_alert_tx_o_t'(candidate_alert_tx_o);" in wrapper_text
    renamed_candidate = (overlay_dir / "candidate" / "uart_candidate.sv").read_text()
    assert "module uart_candidate(" in renamed_candidate


def test_build_opentitan_candidate_plan_applies_hidden_repo_overlay(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo_src"
    (repo_root / "util" / "dvsim").mkdir(parents=True)
    (repo_root / "util" / "dvsim" / "dvsim.py").write_text("print('fake dvsim')\n")
    (repo_root / "hw" / "ip" / "uart" / "rtl").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").write_text("module uart; endmodule\n")
    (repo_root / "hw" / "ip" / "uart" / "dv" / "tb").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "dv" / "tb" / "tb.sv").write_text("module tb; // upstream\nendmodule\n")
    _write_fake_uart_dv_files(repo_root)
    (repo_root / "hw" / "ip" / "uart" / "dv" / "tb" / "tb.sv").write_text("module tb; // upstream\nendmodule\n")

    task_root = tmp_path / "task"
    registry_path = tmp_path / "registry" / "registry.json"
    _write_fake_opentitan_task(task_root, repo_root, registry_path)
    overlay_file = task_root / "oracle" / "repo_overlay" / "hw" / "ip" / "uart" / "dv" / "tb" / "tb.sv"
    overlay_file.parent.mkdir(parents=True, exist_ok=True)
    overlay_file.write_text("module tb; // overlay\nendmodule\n")
    metadata = json.loads((task_root / "task.json").read_text())
    metadata["oracle"]["repo_overlay_dir"] = "repo_overlay"
    (task_root / "task.json").write_text(json.dumps(metadata, indent=2) + "\n")

    task = load_stored_task(task_root)
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    (candidate_dir / "uart.sv").write_text(
        "module uart(\n"
        "  input logic clk_i,\n"
        "  input logic rst_ni,\n"
        "  input uart_public_types_pkg::uart_tl_i_t tl_i,\n"
        "  input uart_public_types_pkg::uart_alert_rx_i_t alert_rx_i,\n"
        "  output uart_public_types_pkg::uart_tl_o_t tl_o,\n"
        "  output uart_public_types_pkg::uart_alert_tx_o_t alert_tx_o\n"
        ");\n"
        "  uart_micro_arch_if u_uart_micro_arch_if();\n"
        "endmodule\n"
    )
    plan = build_opentitan_candidate_validation_plan(
        task,
        candidate_dir=candidate_dir,
        work_root=tmp_path / "work",
    )

    assert (
        plan.repo_root / "hw" / "ip" / "uart" / "dv" / "tb" / "tb.sv"
    ).read_text() == "module tb; // overlay\nendmodule\n"


def test_build_opentitan_mutant_plan_applies_declared_mutation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo_src"
    (repo_root / "util" / "dvsim").mkdir(parents=True)
    (repo_root / "util" / "dvsim" / "dvsim.py").write_text("print('fake dvsim')\n")
    (repo_root / "hw" / "ip" / "uart" / "rtl").mkdir(parents=True)
    (repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").write_text("module uart; // live\nendmodule\n")
    _write_fake_uart_dv_files(repo_root)

    task_root = tmp_path / "task"
    registry_path = tmp_path / "registry" / "registry.json"
    _write_fake_opentitan_task(task_root, repo_root, registry_path)
    task = load_stored_task(task_root)

    plan = build_opentitan_mutant_plan(
        task,
        mutant_name="flip_uart_comment",
        work_root=tmp_path / "work",
    )

    wrapper_text = (plan.repo_root / "hw" / "ip" / "uart" / "rtl" / "uart.sv").read_text()
    assert "module uart; // mutated" in wrapper_text
    assert "uart_micro_arch_if u_uart_micro_arch_if();" in wrapper_text
