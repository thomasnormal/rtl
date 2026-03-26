from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import subprocess


class OpenCodeUnavailable(RuntimeError):
    """Raised when the `opencode` binary is not installed."""


@dataclass(frozen=True)
class OpenCodeRunRequest:
    workspace_root: Path
    agent: str
    prompt: str
    model: str | None = None
    output_format: str = "json"
    extra_args: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OpenCodeRunResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def ensure_opencode_available() -> None:
    if shutil.which("opencode") is None:
        raise OpenCodeUnavailable(
            "The `opencode` binary is not installed. Install OpenCode before running agent episodes."
        )


def build_run_command(request: OpenCodeRunRequest) -> tuple[str, ...]:
    command = [
        "opencode",
        "run",
        "--agent",
        request.agent,
        "--format",
        request.output_format,
        "--dir",
        str(request.workspace_root),
    ]
    if request.model is not None:
        command.extend(["--model", request.model])
    command.extend(request.extra_args)
    command.append(request.prompt)
    return tuple(command)


def build_run_environment(request: OpenCodeRunRequest) -> dict[str, str]:
    workspace_root = request.workspace_root.resolve()
    env = os.environ.copy()
    ceiling = str(workspace_root.parent)
    existing_ceiling = env.get("GIT_CEILING_DIRECTORIES")
    if existing_ceiling:
        env["GIT_CEILING_DIRECTORIES"] = os.pathsep.join([ceiling, existing_ceiling])
    else:
        env["GIT_CEILING_DIRECTORIES"] = ceiling
    return env


def run_opencode(
    request: OpenCodeRunRequest,
    *,
    timeout_s: int = 600,
) -> OpenCodeRunResult:
    ensure_opencode_available()
    command = build_run_command(request)
    env = build_run_environment(request)
    completed = subprocess.run(
        command,
        cwd=request.workspace_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return OpenCodeRunResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
