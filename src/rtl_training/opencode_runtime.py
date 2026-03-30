from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import TextIO


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
    completed_via_result_file: bool = False


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
    _merge_repo_dotenv(env)
    original_home = env.get("HOME")
    original_python_userbase = env.get("PYTHONUSERBASE")
    ceiling = str(workspace_root.parent)
    existing_ceiling = env.get("GIT_CEILING_DIRECTORIES")
    if existing_ceiling:
        env["GIT_CEILING_DIRECTORIES"] = os.pathsep.join([ceiling, existing_ceiling])
    else:
        env["GIT_CEILING_DIRECTORIES"] = ceiling

    workspace_home = workspace_root / ".home"
    xdg_config_home = workspace_root / ".xdg_config"
    xdg_data_home = workspace_root / ".xdg_data"
    xdg_cache_home = workspace_root / ".xdg_cache"
    for path in (workspace_home, xdg_config_home, xdg_data_home, xdg_cache_home):
        path.mkdir(parents=True, exist_ok=True)

    env["HOME"] = str(workspace_home)
    env["XDG_CONFIG_HOME"] = str(xdg_config_home)
    env["XDG_DATA_HOME"] = str(xdg_data_home)
    env["XDG_CACHE_HOME"] = str(xdg_cache_home)
    if original_python_userbase:
        env["PYTHONUSERBASE"] = original_python_userbase
    elif original_home:
        env["PYTHONUSERBASE"] = str((Path(original_home).expanduser() / ".local").resolve())

    config_path = workspace_root / "opencode.json"
    if config_path.exists():
        env["OPENCODE_CONFIG"] = str(config_path)
    config_dir = workspace_root / ".opencode"
    if config_dir.exists():
        env["OPENCODE_CONFIG_DIR"] = str(config_dir)
    return env


def _merge_repo_dotenv(env: dict[str, str]) -> None:
    """Populate missing provider env vars from the repo-local `.env` file."""
    dotenv_path = _repo_root() / ".env"
    if not dotenv_path.exists():
        return
    try:
        lines = dotenv_path.read_text().splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in env:
            continue
        env[key] = value


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_opencode(
    request: OpenCodeRunRequest,
    *,
    timeout_s: int = 600,
    result_settle_s: float = 2.0,
    poll_interval_s: float = 0.2,
    terminate_grace_s: float = 5.0,
) -> OpenCodeRunResult:
    ensure_opencode_available()
    command = build_run_command(request)
    env = build_run_environment(request)
    result_path = request.workspace_root / "result" / "result.json"
    start_time = time.monotonic()
    stable_since: float | None = None
    last_result_state: tuple[int, int] | None = None

    with (
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout_file,
        tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr_file,
        subprocess.Popen(
            command,
            cwd=request.workspace_root,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
        ) as process,
    ):
        while True:
            if process.poll() is not None:
                break

            current_state = _result_file_state(result_path)
            if current_state is not None:
                if current_state == last_result_state:
                    if stable_since is None:
                        stable_since = time.monotonic()
                else:
                    last_result_state = current_state
                    stable_since = time.monotonic()
                if (
                    stable_since is not None
                    and (time.monotonic() - stable_since) >= result_settle_s
                ):
                    _terminate_process(process, grace_s=terminate_grace_s)
                    stdout_text = _read_captured_output(stdout_file)
                    stderr_text = _read_captured_output(stderr_file)
                    return OpenCodeRunResult(
                        command=command,
                        returncode=0,
                        stdout=stdout_text,
                        stderr=stderr_text,
                        completed_via_result_file=True,
                    )
            else:
                stable_since = None
                last_result_state = None

            if (time.monotonic() - start_time) >= timeout_s:
                _terminate_process(process, grace_s=terminate_grace_s)
                stdout_text = _read_captured_output(stdout_file)
                stderr_text = _read_captured_output(stderr_file)
                raise subprocess.TimeoutExpired(
                    command,
                    timeout_s,
                    output=stdout_text,
                    stderr=stderr_text,
                )
            time.sleep(poll_interval_s)

        stdout_text = _read_captured_output(stdout_file)
        stderr_text = _read_captured_output(stderr_file)
    return OpenCodeRunResult(
        command=command,
        returncode=process.returncode,
        stdout=stdout_text,
        stderr=stderr_text,
    )


def _read_captured_output(file_obj: TextIO) -> str:
    file_obj.seek(0)
    return file_obj.read()


def _result_file_state(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not _is_terminal_result_payload(payload):
        return None
    return (stat_result.st_size, stat_result.st_mtime_ns)


def _is_terminal_result_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return True
    raw_status = payload.get("status")
    if raw_status is None:
        return True
    status = str(raw_status).strip().lower()
    return status not in {"in_progress", "pending", "running"}


def _terminate_process(process: subprocess.Popen[str], *, grace_s: float) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    deadline = time.monotonic() + grace_s
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    if process.poll() is None:
        process.kill()
        process.wait()
