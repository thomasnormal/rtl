from pathlib import Path
import subprocess

import pytest

from rtl_training.opencode_runtime import (
    OpenCodeRunRequest,
    OpenCodeUnavailable,
    build_run_environment,
    build_run_command,
    ensure_opencode_available,
    run_opencode,
)


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
    monkeypatch.setattr("rtl_training.opencode_runtime.shutil.which", lambda _: "/usr/bin/opencode")
    captured = {}

    def fake_run(command, *, cwd, env, capture_output, text, timeout, check):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["env"] = env
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0, stdout='{"ok":true}\n', stderr="")

    monkeypatch.setattr("rtl_training.opencode_runtime.subprocess.run", fake_run)

    request = OpenCodeRunRequest(
        workspace_root=tmp_path,
        agent="generator",
        prompt="Read TASK.md.",
    )
    result = run_opencode(request, timeout_s=45)

    assert captured["cwd"] == tmp_path
    assert captured["env"]["GIT_CEILING_DIRECTORIES"] == str(tmp_path.parent)
    assert captured["timeout"] == 45
    assert result.returncode == 0
    assert result.stdout == '{"ok":true}\n'


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
