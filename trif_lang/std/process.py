"""Process management helpers."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Mapping, Sequence


@dataclass(frozen=True)
class CompletedProcess:
    """Light-weight wrapper exposing process execution results."""

    args: Sequence[str]
    returncode: int
    stdout: str
    stderr: str

    def check_returncode(self) -> None:
        """Raise :class:`subprocess.CalledProcessError` when execution failed."""

        if self.returncode != 0:
            raise subprocess.CalledProcessError(self.returncode, list(self.args), self.stdout, self.stderr)


def run(
    command: Sequence[str] | str,
    *,
    input: str | None = None,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
    capture_output: bool = True,
    check: bool = False,
    encoding: str = "utf-8",
    errors: str = "strict",
) -> CompletedProcess:
    """Execute *command* and capture its result."""

    if isinstance(command, str):
        shell = True
        args = command
    else:
        shell = False
        args = list(command)
    completed = subprocess.run(  # noqa: S603 - arguments supplied by caller
        args,
        shell=shell,
        input=input.encode(encoding) if input is not None else None,
        cwd=cwd,
        env=dict(env) if env is not None else None,
        timeout=timeout,
        capture_output=capture_output,
        text=False,
    )
    stdout = completed.stdout.decode(encoding, errors) if completed.stdout is not None else ""
    stderr = completed.stderr.decode(encoding, errors) if completed.stderr is not None else ""
    result = CompletedProcess(
        args=list(args) if not shell else ["/bin/sh", "-c", command],
        returncode=completed.returncode,
        stdout=stdout,
        stderr=stderr,
    )
    if check:
        result.check_returncode()
    return result


def stream(
    command: Sequence[str] | str,
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    encoding: str = "utf-8",
    errors: str = "replace",
) -> Iterable[str]:
    """Yield output lines from *command* as they become available."""

    if isinstance(command, str):
        proc = subprocess.Popen(  # noqa: S603 - intended invocation
            command,
            shell=True,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    else:
        proc = subprocess.Popen(  # noqa: S603
            list(command),
            shell=False,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    assert proc.stdout is not None
    for raw_line in iter(proc.stdout.readline, b""):
        yield raw_line.decode(encoding, errors)
    proc.wait()


def which(executable: str) -> str | None:
    """Return the absolute path to *executable* when available."""

    return shutil.which(executable)


def env() -> Dict[str, str]:
    """Return a copy of the current environment variables."""

    return dict(os.environ)


def setEnv(mapping: Mapping[str, str]) -> None:
    """Update the current process environment with *mapping*."""

    os.environ.update(mapping)


def unsetEnv(keys: Iterable[str]) -> None:
    """Remove the provided *keys* from the process environment."""

    for key in keys:
        os.environ.pop(key, None)


def terminate(process: subprocess.Popen[bytes]) -> None:
    """Terminate a running :class:`subprocess.Popen` instance."""

    process.terminate()


def kill(process: subprocess.Popen[bytes]) -> None:
    """Forcefully kill a running :class:`subprocess.Popen` instance."""

    process.kill()


def spawn(
    command: Sequence[str] | str,
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    stdin: int | None = None,
    stdout: int | None = None,
    stderr: int | None = None,
) -> subprocess.Popen[bytes]:
    """Launch *command* returning the underlying :class:`subprocess.Popen`."""

    if isinstance(command, str):
        return subprocess.Popen(  # noqa: S603 - caller controls command
            command,
            shell=True,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
    return subprocess.Popen(  # noqa: S603
        list(command),
        shell=False,
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
    )


def quote(args: Sequence[str]) -> str:
    """Return a shell-escaped string built from *args*."""

    return " ".join(shlex.quote(part) for part in args)


@contextmanager
def temporary_env(mapping: Mapping[str, str], *, clear: bool = False) -> Iterator[None]:
    """Temporarily modify the process environment."""

    original = dict(os.environ)
    try:
        if clear:
            os.environ.clear()
        os.environ.update(mapping)
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


__all__ = [
    "CompletedProcess",
    "run",
    "stream",
    "which",
    "env",
    "setEnv",
    "unsetEnv",
    "terminate",
    "kill",
    "spawn",
    "quote",
    "temporary_env",
]
