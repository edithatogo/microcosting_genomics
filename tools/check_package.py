# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Verify distribution contents against source without extracting archive paths."""

import argparse
import logging
import tarfile
from email.parser import BytesParser
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from zipfile import ZipFile

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from email.message import Message
FORBIDDEN_SUFFIXES = {".xlsx", ".xlsm", ".parquet", ".pkl", ".docx", ".ipynb"}
FORBIDDEN_PARTS = {"conductor", ".private-runs", "data", "manuscripts", "reports"}
SDIST_ROOTS = {
    ".gitignore",
    "src",
    "tests",
    "scripts",
    "tools",
    "pyproject.toml",
    "config.yaml",
    "uv.lock",
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "SECURITY.md",
    "PKG-INFO",
}
SDIST_HELPERS = {
    "scripts/__init__.py",
    "scripts/convert_to_csv.py",
    "scripts/parse_cost_tables.py",
    "scripts/parse_additional_tables.py",
    "tools/__init__.py",
    "tools/select_tests.py",
    "tools/check_package.py",
    "tools/build_t1_scenario.py",
}


def check_paths(names: list[str]) -> None:
    """Reject research payloads and nonportable archive traversal paths."""
    for name in names:
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in name
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or FORBIDDEN_PARTS.intersection(path.parts)
        ):
            message = f"Disallowed distribution path: {name}"
            raise ValueError(message)


def check_distribution_paths(payloads: dict[str, bytes]) -> None:
    """Classify the pinned generated dependency index separately from research data.

    The index contains static cell identities and three missing-parameter IDs.
    Its exact reviewed bytes are required; arbitrary files in data stay forbidden.
    """
    index = "t1_known_zero_lineage.json"
    expected = "c9c7b042ce024af28307be2d080f97f256933392d05c846cef0af2bad0222e54"
    for name, payload in payloads.items():
        parts = PurePosixPath(name).parts
        is_index = name == "genomics_microcosting/data/" + index or (
            parts[1:] == ("src", "genomics_microcosting", "data", index)
        )
        if not is_index:
            check_paths([name])
            continue
        if sha256(payload).hexdigest() != expected:
            message = "Generated dependency index differs from reviewed source bytes"
            raise ValueError(message)
        classified = PurePosixPath(*parts[:-2], "generated_code", parts[-1])
        check_paths([str(classified)])


def check_distributions(root: Path, dist_dir: Path) -> str:
    """Check source bytes, licence, typing marker and version identity."""
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        message = "Expected exactly one wheel and one source distribution"
        raise ValueError(message)
    with ZipFile(wheels[0]) as archive:
        wheel = {name: archive.read(name) for name in archive.namelist()}
    sdist = _read_sdist(sdists[0])
    check_distribution_paths(wheel)
    check_distribution_paths(sdist)
    _check_source_allowlist(sdist)
    _check_sdist_sources(root, sdist)
    licence = (root / "LICENSE").read_bytes()
    _require_single_payload(wheel, "/licenses/LICENSE", licence)
    _require_single_payload(sdist, "/LICENSE", licence)
    package = root / "src" / "genomics_microcosting"
    expected_names: set[str] = set()
    for path in package.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root / "src").as_posix()
        expected_names.add(relative)
        expected = path.read_bytes()
        if wheel.get(relative) != expected:
            message = f"Wheel source differs: {relative}"
            raise ValueError(message)
        _require_single_payload(sdist, "/src/" + relative, expected)
    packaged_config = "genomics_microcosting/config.yaml"
    if wheel.get(packaged_config) != (root / "config.yaml").read_bytes():
        message = "Wheel configuration differs from maintained source"
        raise ValueError(message)
    expected_names.add(packaged_config)
    _check_wheel_allowlist(wheel, expected_names)
    marker = "genomics_microcosting/py.typed"
    if marker not in wheel:
        message = "Wheel lacks the PEP 561 typing marker"
        raise ValueError(message)
    wheel_metadata = _metadata(wheel, "/METADATA")
    source_metadata = _metadata(sdist, "/PKG-INFO")
    _check_metadata(wheel_metadata, source_metadata)
    return str(wheel_metadata["Version"])


def _check_metadata(wheel_metadata: Message, source_metadata: Message) -> None:
    """Keep runtime/licence policy and wheel/source metadata aligned."""
    for field in ("Version", "Requires-Python", "License-Expression"):
        if not wheel_metadata[field] or wheel_metadata[field] != source_metadata[field]:
            message = f"Distribution metadata disagrees: {field}"
            raise ValueError(message)
    if (
        wheel_metadata["Requires-Python"] != "==3.15.1"
        or wheel_metadata["License-Expression"] != "Apache-2.0"
    ):
        message = "Distribution runtime/licence policy disagrees with the project"
        raise ValueError(message)


def _check_sdist_sources(root: Path, sdist: dict[str, bytes]) -> None:
    """Compare included tests, helpers and maintained package metadata exactly."""
    paths = set((root / "tests").rglob("*.py"))
    paths.update(root / name for name in SDIST_HELPERS)
    metadata_paths = (
        ".gitignore",
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "SECURITY.md",
        "pyproject.toml",
        "config.yaml",
        "uv.lock",
    )
    paths.update(root / name for name in metadata_paths)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        _require_single_payload(sdist, "/" + relative, path.read_bytes())


def _check_wheel_allowlist(wheel: dict[str, bytes], expected_names: set[str]) -> None:
    """Allow exact package files plus the generated distribution metadata."""
    actual = {
        name
        for name in wheel
        if not PurePosixPath(name).parts[0].endswith(".dist-info")
    }
    if actual != expected_names:
        difference = actual ^ expected_names
        message = f"Wheel contains unexpected/missing package files: {difference}"
        raise ValueError(message)


def _check_source_allowlist(sdist: dict[str, bytes]) -> None:
    """Require one source root and the maintained source-distribution allowlist."""
    roots = {PurePosixPath(name).parts[0] for name in sdist}
    if len(roots) != 1:
        message = "Source archive contains multiple roots"
        raise ValueError(message)
    for name in sdist:
        relative = PurePosixPath(*PurePosixPath(name).parts[1:])
        if (
            not relative.parts
            or relative.parts[0] not in SDIST_ROOTS
            or (
                relative.parts[0] in {"scripts", "tools"}
                and relative.as_posix() not in SDIST_HELPERS
            )
        ):
            message = f"Unexpected source distribution member: {name}"
            raise ValueError(message)


def _read_sdist(path: Path) -> dict[str, bytes]:
    """Read only regular source archive members without materializing paths."""
    with tarfile.open(path) as archive:
        sdist: dict[str, bytes] = {}
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                message = f"Nonregular source archive member: {member.name}"
                raise ValueError(message)
            stream = archive.extractfile(member)
            if stream is None:
                raise AssertionError(member.name)
            sdist[member.name] = stream.read()
    return sdist


def _metadata(payloads: dict[str, bytes], suffix: str) -> Message:
    """Read exactly one generated distribution metadata record."""
    records = [value for name, value in payloads.items() if name.endswith(suffix)]
    if len(records) != 1:
        message = f"Expected one metadata record ending in {suffix}"
        raise ValueError(message)
    return BytesParser().parsebytes(records[0])


def _require_single_payload(
    payloads: dict[str, bytes],
    suffix: str,
    expected: bytes,
) -> None:
    """Require exact single-member content rather than approximate licence labels."""
    records = [value for name, value in payloads.items() if name.endswith(suffix)]
    if records != [expected]:
        message = f"Missing, duplicated or changed source payload: {suffix}"
        raise ValueError(message)


def main() -> None:
    """Validate a local build directory and log the qualified distribution version."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", type=Path)
    options = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    check_distributions(Path(__file__).resolve().parents[1], options.dist_dir)
    logger.info("Distribution source, licence and version checks passed")


if __name__ == "__main__":
    main()
