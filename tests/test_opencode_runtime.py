import json
from pathlib import Path
import stat
import subprocess
import sys
import textwrap

import pytest

from rtl_training.opencode_runtime import (
    OpenCodeRunRequest,
    OpenCodeUnavailable,
    build_run_environment,
    build_run_command,
    ensure_opencode_available,
    run_opencode,
)


def _install_fake_opencode(tmp_path: Path, script_body: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script_path = bin_dir / "opencode"
    script_path.write_text(
        textwrap.dedent(
            f"""\
#!/usr/bin/env python3
import json
import os
import signal
import sys
import time
from pathlib import Path

{textwrap.dedent(script_body)}
"""
        )
    )
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
    return script_path


def test_build_run_command_uses_agent_format_and_prompt() -> None:
    request = OpenCodeRunRequest(
        workspace_root=Path("/tmp/workspace"),
        agent="generator",
        prompt="Read TASK.md and do the job.",
        model="anthropic/claude-sonnet-4",
        extra_args=("--quiet",),
    )

    command = build_run_command(request)

    assert command == (
        "opencode",
        "run",
        "--agent",
        "generator",
        "--format",
        "json",
        "--dir",
        "/tmp/workspace",
        "--model",
        "anthropic/claude-sonnet-4",
        "--quiet",
        "Read TASK.md and do the job.",
    )


def test_ensure_opencode_available_rejects_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("rtl_training.opencode_runtime.shutil.which", lambda _: None)

    with pytest.raises(OpenCodeUnavailable):
        ensure_opencode_available()


def test_run_opencode_uses_workspace_as_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_opencode = _install_fake_opencode(
        tmp_path,
        """
        workspace = Path(sys.argv[sys.argv.index("--dir") + 1])
        result_dir = workspace / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        (workspace / "cwd.txt").write_text(os.getcwd())
        env_payload = {
            "GIT_CEILING_DIRECTORIES": os.environ["GIT_CEILING_DIRECTORIES"],
            "HOME": os.environ["HOME"],
            "XDG_CONFIG_HOME": os.environ["XDG_CONFIG_HOME"],
            "XDG_DATA_HOME": os.environ["XDG_DATA_HOME"],
            "XDG_CACHE_HOME": os.environ["XDG_CACHE_HOME"],
        }
        (workspace / "env.json").write_text(json.dumps(env_payload))
        (result_dir / "result.json").write_text('{"status":"complete"}\\n')
        print('{"ok":true}')
        """,
    )
    workspace_root = tmp_path / "episode"
    request = OpenCodeRunRequest(
        workspace_root=workspace_root,
        agent="generator",
        prompt="Read TASK.md.",
    )
    monkeypatch.setattr("rtl_training.opencode_runtime.ensure_opencode_available", lambda: None)
    monkeypatch.setattr(
        "rtl_training.opencode_runtime.build_run_command",
        lambda _: (str(fake_opencode), "--dir", str(workspace_root)),
    )
    result = run_opencode(request, timeout_s=45)

    env_payload = json.loads((workspace_root / "env.json").read_text())
    assert (workspace_root / "cwd.txt").read_text() == str(workspace_root)
    assert env_payload["GIT_CEILING_DIRECTORIES"] == str(workspace_root.parent)
    assert env_payload["HOME"] == str(workspace_root / ".home")
    assert env_payload["XDG_CONFIG_HOME"] == str(workspace_root / ".xdg_config")
    assert env_payload["XDG_DATA_HOME"] == str(workspace_root / ".xdg_data")
    assert env_payload["XDG_CACHE_HOME"] == str(workspace_root / ".xdg_cache")
    assert result.returncode == 0
    assert result.stdout == '{"ok":true}\n'
    assert result.completed_via_result_file is False


def test_build_run_environment_caps_git_discovery_at_workspace_parent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", "/existing/ceiling")
    request = OpenCodeRunRequest(
        workspace_root=tmp_path / "episode",
        agent="verifier",
        prompt="Read TASK.md.",
    )

    env = build_run_environment(request)

    assert env["GIT_CEILING_DIRECTORIES"] == f"{request.workspace_root.parent}:/existing/ceiling"


def test_build_run_environment_uses_workspace_local_opencode_config(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "episode"
    workspace_root.mkdir()
    (workspace_root / "opencode.json").write_text("{}\n")
    (workspace_root / ".opencode").mkdir()
    request = OpenCodeRunRequest(
        workspace_root=workspace_root,
        agent="generator",
        prompt="Read TASK.md.",
    )

    env = build_run_environment(request)

    assert env["OPENCODE_CONFIG"] == str(workspace_root / "opencode.json")
    assert env["OPENCODE_CONFIG_DIR"] == str(workspace_root / ".opencode")
    assert (workspace_root / ".home").is_dir()
    assert (workspace_root / ".xdg_config").is_dir()
    assert (workspace_root / ".xdg_data").is_dir()
    assert (workspace_root / ".xdg_cache").is_dir()


def test_build_run_environment_preserves_python_userbase_for_user_site_tools(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original_home = tmp_path / "original-home"
    usersite = (
        original_home
        / ".local"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
    usersite.mkdir(parents=True)
    (usersite / "dummyusersitepkg.py").write_text("VALUE = 7\n")
    monkeypatch.setenv("HOME", str(original_home))
    monkeypatch.delenv("PYTHONUSERBASE", raising=False)
    request = OpenCodeRunRequest(
        workspace_root=tmp_path / "episode",
        agent="generator",
        prompt="Read TASK.md.",
    )

    env = build_run_environment(request)

    assert env["HOME"] == str((tmp_path / "episode" / ".home").resolve())
    assert env["PYTHONUSERBASE"] == str((original_home / ".local").resolve())
    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "import dummyusersitepkg; print(dummyusersitepkg.VALUE)",
        ],
        env=env,
        text=True,
    )
    assert output.strip() == "7"


def test_run_opencode_stops_after_result_file_stabilizes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_opencode = _install_fake_opencode(
        tmp_path,
        """
        workspace = Path(sys.argv[sys.argv.index("--dir") + 1])
        result_dir = workspace / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        terminated = {"seen": False}

        def _handle_term(signum, frame):
            terminated["seen"] = True
            sys.stderr.write("terminated after result\\n")
            sys.stderr.flush()
            sys.exit(0)

        signal.signal(signal.SIGTERM, _handle_term)
        print("starting agent")
        sys.stdout.flush()
        (result_dir / "result.json").write_text('{"status":"complete","verdict":"bad"}\\n')
        while not terminated["seen"]:
            time.sleep(0.1)
        """,
    )
    request = OpenCodeRunRequest(
        workspace_root=tmp_path / "episode",
        agent="verifier",
        prompt="Read TASK.md.",
    )
    monkeypatch.setattr("rtl_training.opencode_runtime.ensure_opencode_available", lambda: None)
    monkeypatch.setattr(
        "rtl_training.opencode_runtime.build_run_command",
        lambda _: (str(fake_opencode), "--dir", str(request.workspace_root)),
    )

    result = run_opencode(
        request,
        timeout_s=10,
        result_settle_s=0.2,
        poll_interval_s=0.05,
        terminate_grace_s=1.0,
    )

    assert result.returncode == 0
    assert result.completed_via_result_file is True
    assert "starting agent" in result.stdout
    assert "terminated after result" in result.stderr
    assert (request.workspace_root / "result" / "result.json").exists()
