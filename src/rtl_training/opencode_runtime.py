from __future__ import annotations

from dataclasses import dataclass, field
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
    command = ["opencode", "run", "--agent", request.agent, "--format", request.output_format]
    if request.model is not None:
        command.extend(["--model", request.model])
    command.extend(request.extra_args)
    command.append(request.prompt)
    return tuple(command)


def run_opencode(
    request: OpenCodeRunRequest,
    *,
    timeout_s: int = 600,
) -> OpenCodeRunResult:
    ensure_opencode_available()
    command = build_run_command(request)
    completed = subprocess.run(
        command,
        cwd=request.workspace_root,
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
