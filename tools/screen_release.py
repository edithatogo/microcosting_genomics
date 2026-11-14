# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Screen outgoing revisions and report finding locations only."""

import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import spacy
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import SpacyNlpEngine


def run_scan_command(tool: str, *arguments: str) -> bytes:
    """Run a resolved Git or Gitleaks command with no shell."""
    if tool not in {"git", "gitleaks"}:
        raise ValueError(tool)
    found = shutil.which(tool)
    if found is None:
        raise FileNotFoundError(tool)
    executable = Path(found).resolve(strict=True)
    with tempfile.TemporaryFile(mode="w+b") as output:
        pid = os.posix_spawn(
            executable,
            [str(executable), *arguments],
            os.environ,
            file_actions=[(os.POSIX_SPAWN_DUP2, output.fileno(), 1)],
        )
        _, status = os.waitpid(pid, 0)
        if result := os.waitstatus_to_exitcode(status):
            raise SystemExit(result)
        output.seek(0)
        return output.read()


def git(*args: str) -> bytes:
    """Run the selected Git read and return its output bytes."""
    return run_scan_command("git", *args)


base = sys.argv[1]
if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", base):
    message = "Supply the full Git base commit hash"
    raise SystemExit(message)
git("rev-parse", "--verify", "--end-of-options", base + "^{commit}")
if not spacy.util.is_package("en_core_web_sm"):
    message = "Install the pinned English model locally before scanning."
    raise SystemExit(message)
# spaCy 3.8.18 cannot deserialize the model tokenizer on CPython 3.15.1.
# Keep the English defaults and the complete trained entity pipeline.
nlp = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
nlp.nlp = {"en": spacy.load("en_core_web_sm", exclude=["tokenizer"])}
engine = AnalyzerEngine(nlp_engine=nlp)
if not engine.analyze(
    text="Barack Obama visited London.",
    language="en",
    entities=["PERSON"],
):
    message = "Presidio name positive control failed."
    raise SystemExit(message)
entities = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "US_SSN",
    "AU_MEDICARE",
    "AU_TFN",
    "PERSON",
]
if not engine.analyze(
    text="Contact alice@example.org",
    language="en",
    entities=["EMAIL_ADDRESS"],
):
    message = "Presidio positive control failed."
    raise SystemExit(message)
revisions = base + "..HEAD"
run_scan_command("gitleaks", "git", "--redact", "--log-opts=" + revisions, ".")
blocked = False
for revision in git("rev-list", revisions).decode().splitlines():
    paths = git(
        "diff-tree",
        "-m",
        "--root",
        "--no-commit-id",
        "--name-only",
        "--diff-filter=ACMRT",
        "-r",
        "-z",
        revision,
    )
    for raw in set(paths.split(b"\0")) - {b""}:
        name = raw.decode()
        if Path(name).suffix not in {
            ".py",
            ".md",
            ".toml",
            ".yaml",
            ".yml",
            ".txt",
            ".lock",
        }:
            sys.stdout.writelines(
                (
                    " ".join((str(revision[:12]), str(name), "requires manual review")),
                    "\n",
                ),
            )
            blocked = True
            continue
        content = git("show", revision + ":" + name).decode()
        for start in range(0, len(content), 12000):
            findings = engine.analyze(
                text=content[max(0, start - 256) : start + 12000],
                language="en",
                entities=entities,
            )
            if findings:
                sys.stdout.writelines(
                    (
                        " ".join(
                            (
                                str(revision[:12]),
                                str(name),
                                str(sorted({hit.entity_type for hit in findings})),
                            ),
                        ),
                        "\n",
                    ),
                )
                blocked = True
                break
raise SystemExit(int(blocked))
