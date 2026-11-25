"""Mutation testing for a Helm chart: break its templates and schema one way at a time, and check its tests notice.

Each mutant changes one line of a template (or drops one constraint from `values.schema.json`); the chart's tests then
run on a copy that holds the mutant. A mutant the tests still pass survived: nothing checks what it changed. Run it
with `uv run --no-project --with pyyaml python scripts/mutate_chart.py <chart>`; a survivor that cannot change what the
chart renders goes in `<chart>/mutation-ignore.yaml` with its reason.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_TEST_COMMAND = "helm unittest {chart}"
IGNORE_FILE = "mutation-ignore.yaml"
SCHEMA_FILE = "values.schema.json"
SCHEMA_CONSTRAINTS = (
    "enum",
    "const",
    "required",
    "minimum",
    "maximum",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
)
TIMEOUT_SECONDS = 600

_ACTION = re.compile(r"\{\{.*?\}\}")
_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
_FAIL = re.compile(r"\{\{-?\s*fail\b")
_IF = re.compile(r"^(\s*\{\{-?\s*(?:else\s+)?if\s+)(.*?)(\s*-?\}\})\s*$")
_CONTROL = re.compile(r"^\{\{-?\s*(?:if|else|end|range|with|define|fail|/\*|\$\w*\s*:?=)")
_PARENT_KEY = re.compile(r"^\s*[\w./-]+:\s*$")
_LOGIC = re.compile(r"(?<=[\s(])(and|or)(?=\s)")
_NUMBER = re.compile(r"(?<![\w.$])(?<!indent )\d+(?![\w.])")
_NAMES_A_HELPER = re.compile(r"\b(?:include|template|define)\s*$")


@dataclass(frozen=True)
class Mutant:
    """One change to one file. `line` is 1-based; 0 means `mutated` is the whole new file (a schema mutant)."""

    file: str
    line: int
    operator: str
    original: str
    mutated: str

    def where(self) -> str:
        """Where the mutant is: `file:line`, or `file#pointer` for a schema constraint."""
        return f"{self.file}#{self.original}" if self.line == 0 else f"{self.file}:{self.line}"


def _masked(text: str) -> str:
    """The text with every string literal blanked, so a word inside a string is never taken for code."""
    return _STRING.sub(lambda match: '"' + " " * (len(match.group()) - 2) + '"', text)


def _line_mutants(path: str, number: int, line: str) -> list[Mutant]:
    mutants: list[Mutant] = []

    def add(operator: str, mutated: str) -> None:
        mutants.append(Mutant(path, number, operator, line, mutated))

    if _FAIL.search(line):
        add("remove-fail", "")
    if found := _IF.match(line):
        prefix, condition, suffix = found.groups()
        add("negate-if", f"{prefix}not ({condition}){suffix}")
    masked = _masked(line)
    for action in _ACTION.finditer(masked):
        start, end = action.span()
        for logic in _LOGIC.finditer(masked, start, end):
            swapped = "or" if logic.group() == "and" else "and"
            add("swap-and-or", line[: logic.start()] + swapped + line[logic.end() :])
        for literal in _STRING.finditer(line, start, end):
            if not _NAMES_A_HELPER.search(line[start : literal.start()]):
                add("change-string", line[: literal.end() - 1] + "-mutant" + line[literal.end() - 1 :])
        for digits in _NUMBER.finditer(masked, start, end):
            add("change-number", line[: digits.start()] + str(int(digits.group()) + 1) + line[digits.end() :])
    stripped = line.strip()
    if stripped and stripped != "---" and not stripped.startswith("#"):
        if not _CONTROL.match(stripped) and not _PARENT_KEY.match(line):
            add("delete-line", "")
    return mutants


def template_mutants(path: str, text: str) -> list[Mutant]:
    """Every one-line mutant of a template file."""
    mutants: list[Mutant] = []
    for number, line in enumerate(text.split("\n"), start=1):
        mutants += _line_mutants(path, number, line)
    return mutants


def _constraint_pointers(node: object, pointer: str = "") -> list[str]:
    pointers: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{pointer}/{key}"
            if key in SCHEMA_CONSTRAINTS or (key == "additionalProperties" and value is False):
                pointers.append(here)
            if key not in ("enum", "const", "required"):
                pointers += _constraint_pointers(value, here)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            pointers += _constraint_pointers(value, f"{pointer}/{index}")
    return pointers


def _without(schema: Any, pointer: str) -> Any:
    mutated = copy.deepcopy(schema)
    *parents, last = pointer.strip("/").split("/")
    node = mutated
    for part in parents:
        node = node[int(part)] if isinstance(node, list) else node[part]
    del node[last]
    return mutated


def schema_mutants(path: str, text: str) -> list[Mutant]:
    """One mutant per constraint in the schema, each dropping just that constraint."""
    schema = json.loads(text)
    return [
        Mutant(path, 0, "remove-constraint", pointer, json.dumps(_without(schema, pointer), indent=2) + "\n")
        for pointer in _constraint_pointers(schema)
    ]


def apply(text: str, mutant: Mutant) -> str:
    """The file's text with the mutant in it."""
    if mutant.line == 0:
        return mutant.mutated
    lines = text.split("\n")
    lines[mutant.line - 1] = mutant.mutated
    return "\n".join(lines)


def _ignored(chart: Path) -> list[dict]:
    path = chart / IGNORE_FILE
    if not path.exists():
        return []
    entries = yaml.safe_load(path.read_text()) or []
    for entry in entries:
        if not str(entry.get("reason", "")).strip():
            raise ValueError(f"{IGNORE_FILE}: every entry needs a reason, {entry} has none")
    return entries


def all_mutants(chart: Path, only: list[str] | None = None) -> list[Mutant]:
    """Every mutant of the chart's templates and schema, less the ones its ignore file names."""
    mutants: list[Mutant] = []
    for path in sorted((chart / "templates").rglob("*")):
        if path.suffix in (".yaml", ".tpl"):
            mutants += template_mutants(path.relative_to(chart).as_posix(), path.read_text())
    if (chart / SCHEMA_FILE).exists():
        mutants += schema_mutants(SCHEMA_FILE, (chart / SCHEMA_FILE).read_text())
    if only:
        mutants = [m for m in mutants if m.file in only]
    ignored = {(e["file"], e["operator"], str(e["original"]).strip()) for e in _ignored(chart)}
    return [m for m in mutants if (m.file, m.operator, m.original.strip()) not in ignored]


def killed(chart: Path, mutant: Mutant, command: list[str]) -> bool:
    """Run the tests on a copy of the chart holding the mutant; the mutant is killed when they fail."""
    with tempfile.TemporaryDirectory() as scratch:
        copied = Path(scratch) / chart.name
        shutil.copytree(chart, copied)
        target = copied / mutant.file
        target.write_text(apply(target.read_text(), mutant))
        argv = [part.replace("{chart}", str(copied)) for part in command]
        try:
            finished = subprocess.run(argv, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
        except subprocess.TimeoutExpired:
            return True
        return finished.returncode != 0


def main(argv: list[str] | None = None) -> int:
    """Run every mutant and list the survivors; the exit status is 1 when any survived."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("chart", type=Path)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    parser.add_argument("--only", action="append", help="mutate only this file (relative to the chart), repeatable")
    parser.add_argument("--test-command", default=DEFAULT_TEST_COMMAND, help="'{chart}' is the mutated copy")
    arguments = parser.parse_args(argv)
    chart = arguments.chart.resolve()
    command = shlex.split(arguments.test_command)
    mutants = all_mutants(chart, arguments.only)
    with ThreadPoolExecutor(max_workers=arguments.jobs) as pool:
        verdicts = list(pool.map(lambda mutant: killed(chart, mutant, command), mutants))
    survivors = [mutant for mutant, verdict in zip(mutants, verdicts, strict=True) if not verdict]
    for mutant in survivors:
        change = f"{mutant.original.strip()!r} -> {mutant.mutated.strip()!r}"[:300]
        print(f"survived: {mutant.where()} {mutant.operator}: {change}")
    print(f"{len(mutants)} mutants, {len(mutants) - len(survivors)} killed, {len(survivors)} survived")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
