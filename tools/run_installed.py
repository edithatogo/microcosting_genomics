# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Run an installed command and record a local execution receipt."""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

r = Path(sys.argv[1]).resolve()
cmd = sys.argv[2]
if cmd not in {"prepare-data", "validate-engine", "microcosting-healthworkforce"}:
    message = "Choose a supported microcosting entry point"
    raise SystemExit(message)
os.chdir(r)
out = r / ".private-runs" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
out.mkdir(parents=True, mode=0o700)


def digest(p: Path) -> str:
    """Return the SHA-256 digest of a local file."""
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def event(kind: str, **details: object) -> None:
    """Append a timestamped event to the execution receipt."""
    with (out / "events.jsonl").open("a") as f:
        record = dict(at=datetime.now(UTC).isoformat(), event=kind, **details)
        f.write(json.dumps(record) + "\n")


def execute(program: Path, arguments: list[str], target: int, **env: str) -> int:
    """Spawn one resolved program with explicit arguments and file descriptors."""
    executable = program.resolve(strict=True)
    actions = [(os.POSIX_SPAWN_DUP2, target, 1)]
    if env:
        actions.append((os.POSIX_SPAWN_DUP2, target, 2))
    pid = os.posix_spawn(
        executable,
        [str(program), *arguments],
        {**os.environ, **env},
        file_actions=actions,
    )
    _, wait_status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(wait_status)


def capture(tool: str, *arguments: str) -> str:
    """Capture read-only Git or uv output for the execution receipt."""
    path = shutil.which(tool)
    if path is None:
        raise FileNotFoundError(tool)
    with tempfile.TemporaryFile(mode="w+b") as output:
        result = execute(Path(path), list(arguments), output.fileno())
        if result:
            raise SystemExit(result)
        output.seek(0)
        return output.read().decode()


runtime = Path(os.environ.get("MICROCOSTING_RUNTIME", r / ".venv")).resolve()
entrypoint = runtime / "bin" / cmd
args: list[str] = []
if cmd == "microcosting-healthworkforce":
    args += [
        "--run-psa",
        "--psa-iterations",
        "20",
        "--output-dir",
        str(out / "results"),
    ]
(out / "results").mkdir()
files = [p for p in (r / "data").iterdir() if p.suffix in {".xlsx", ".xlsm", ".json"}]
files += [p for p in (r / "config.yaml", r / "pyproject.toml") if p.exists()]
event(
    "started",
    commit=capture("git", "rev-parse", "HEAD").strip(),
    dirty=bool(capture("git", "status", "--porcelain").strip()),
    source_hashes={
        str(p.relative_to(r)): digest(p)
        for directory in ("src", "tests", "tools", "typings")
        for p in (r / directory).rglob("*")
        if p.is_file() and p.suffix in {".py", ".pyi"}
    },
    lockfile_sha256=digest(r / "uv.lock"),
    prepared_input_hashes={
        str(p): digest(p)
        for p in Path(
            os.environ.get("MICROCOSTING_PREPARED_DIR", r / "data/prepared"),
        ).glob("*.parquet")
    },
    args=[str(entrypoint), *args],
    inputs={p.name: digest(p) for p in files},
    environment=capture(
        "uv",
        "pip",
        "freeze",
        "--python",
        str(runtime / "bin/python"),
    ).splitlines(),
)
with (out / "process.log").open("w") as f:
    result = execute(
        entrypoint,
        args,
        f.fileno(),
        MICROCOSTING_OUTPUT_DIR=str(out / "results"),
        MPLBACKEND="Agg",
    )
event(
    "finished",
    exit_code=result,
    outputs={
        str(p.relative_to(out)): digest(p)
        for p in out.rglob("*")
        if p.is_file() and p.name != "events.jsonl"
    },
)
sys.stdout.write(f"{cmd} {result} {out}\n")
raise SystemExit(result)
