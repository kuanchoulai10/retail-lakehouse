"""Move the backend's table maintenance code into ``context/table_maintenance``.

One-off tool for the bounded context restructure. It moves the code and rewrites
references, and it does not change any logic. Historical: it ran once, for commit
1b7fb0f, and ``check`` reproduces only against that tree (working tree at 1b7fb0f,
``BASE`` its parent 85b348f). Run it from the repository root::

    uv run scripts/move_backend_into_context.py move
    uv run scripts/move_backend_into_context.py check <BASE>

``move``
    1. ``git mv`` the backend's ``application/`` and ``adapter/`` into
       ``context/table_maintenance/``, and ``tests/{application,adapter,fakes}/``
       into ``tests/context/table_maintenance/``. Write the four structural
       ``__init__.py`` files (one-line docstring, no exports).
    2. Rewrite every ``.py`` file of the backend with the rules below, in order.
    3. Rewrite the module names in ``.importlinter`` (rule I).
    4. Run ``ruff format`` on the backend, so the longer names wrap the way the
       pre-commit hook would wrap them, then apply rule R7 to the wrapped imports.

Rules (``P`` is ``application`` or ``adapter``; a rule never fires inside a
longer word, because a token must not follow a word character or a dot):

    R1 root hop       In a moved file, ``Path(__file__).resolve().parents[N]`` that
                      names the backend root is renumbered so that it still names
                      the backend root from the file's new, deeper location.
    R2 derived hop    A ``parents[N]`` hop that climbs from a directory inside a
                      moved package to the backend root grows by the two inserted
                      levels. The hops are listed in ``DERIVED_ROOT_HOPS``.
    R3 dotted         ``P.<ident>`` becomes ``context.table_maintenance.P.<ident>``.
                      This covers imports, ``import x.y`` attribute chains such as
                      ``application.service.__path__``, and dotted strings.
    R4 test dotted    ``tests.Q.<ident>``, where ``Q`` is ``application``, ``adapter``
                      or ``fakes``, becomes ``tests.context.table_maintenance.Q.<ident>``.
    R5 path literal   A string literal that starts with ``P/<ident>``, and the bare
                      ``"P"`` argument of the ``subdirs(...)`` test helper (a
                      backend-relative directory), get ``context/table_maintenance/``
                      in front.
    R6 path segment   A ``/ "P"`` segment straight after a backend-root expression
                      (``BACKEND``, ``_BACKEND`` or the file's own
                      ``Path(__file__).resolve().parents[N]``) gets
                      ``/ "context" / "table_maintenance"`` in front.
    I  importlinter   A module line ``P`` or ``P.x.y`` gets ``context.table_maintenance.``
                      in front, except under ``root_packages`` (a residual, below).
    R7 noqa           When ``ruff format`` wraps a one-name import that carries a
                      trailing ``# noqa`` comment, the comment lands after the closing
                      parenthesis, where it no longer silences the imported name.
                      It moves back onto the name's line (``harness,  # noqa: F401``).

``check <BASE>``
    For every backend file at ``BASE``, read the file at its new path, apply the
    inverse rules (in reverse order), and compare it line by line with
    ``git show <BASE>:<old path>``. Python files on both sides are first passed
    through ``ruff format`` with ``skip-magic-trailing-comma``, so that wrapping
    added by step 4 is not reported as a difference. Every differing line is
    printed as ``residual: <new path>:<line>: <text>`` (a line only on the old side
    is shown as ``(removed) <text>``). The exit code is 0 only when every residual
    is in ``ALLOWED_RESIDUALS`` and no file is missing, unexpected or left behind.

``ALLOWED_RESIDUALS`` holds the lists of top-level package names. They cannot be
written as a prefix substitution: ``application`` and ``adapter`` both become the
single package ``context``. They are edited by hand after ``move``.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
BACKEND_REL = "src/data-platform/backend"
BACKEND = REPO / BACKEND_REL

CONTEXT_DIR = "context/table_maintenance"
CONTEXT_DOTTED = "context.table_maintenance."

MOVES: tuple[tuple[str, str], ...] = (
    ("application", f"{CONTEXT_DIR}/application"),
    ("adapter", f"{CONTEXT_DIR}/adapter"),
    ("tests/application", f"tests/{CONTEXT_DIR}/application"),
    ("tests/adapter", f"tests/{CONTEXT_DIR}/adapter"),
    ("tests/fakes", f"tests/{CONTEXT_DIR}/fakes"),
)

STRUCTURAL_INITS: dict[str, str] = {
    "context/__init__.py": '"""Bounded contexts of the data platform backend."""\n',
    f"{CONTEXT_DIR}/__init__.py": '"""Table maintenance bounded context."""\n',
    "tests/context/__init__.py": '"""Tests for the bounded contexts."""\n',
    f"tests/{CONTEXT_DIR}/__init__.py": ('"""Tests for the table maintenance bounded context."""\n'),
}

DERIVED_ROOT_HOPS: dict[str, tuple[tuple[str, str], ...]] = {
    "tests/architecture/test_service_structure.py": (("SERVICE_DIR.parents[1]", "SERVICE_DIR.parents[3]"),),
}

ALLOWED_RESIDUALS: frozenset[tuple[str, str]] = frozenset(
    {
        (".importlinter", "(removed) adapter"),
        (".importlinter", "(removed) application"),
        (".importlinter", "context"),
        (
            "tests/architecture/boundaries.py",
            '(removed) PROJECT_PACKAGES = ("application", "adapter", "base", "bootstrap")',
        ),
        (
            "tests/architecture/boundaries.py",
            'PROJECT_PACKAGES = ("context", "base", "bootstrap")',
        ),
        (
            "tests/architecture/test_inheritance_depth.py",
            '(removed) SOURCE_PACKAGES = ("base", "application", "adapter", "bootstrap")',
        ),
        (
            "tests/architecture/test_inheritance_depth.py",
            'SOURCE_PACKAGES = ("base", "context", "bootstrap")',
        ),
        (
            "tests/architecture/test_directory_structure.py",
            '(removed) EXPECTED_TOP_LEVEL = {"adapter", "application", "base", "bootstrap"}',
        ),
        (
            "tests/architecture/test_directory_structure.py",
            'EXPECTED_TOP_LEVEL = {"context", "base", "bootstrap"}',
        ),
    }
)

_PKG = r"(?:application|adapter)"
_TEST_PKG = r"(?:application|adapter|fakes)"
_ROOT_HOP = re.compile(r"(Path\(__file__\)\.resolve\(\)\.parents\[)(\d+)(\])")

_DOTTED = re.compile(rf"(?<![\w.])(?={_PKG}\.[A-Za-z_])")
_DOTTED_INV = re.compile(rf"(?<![\w.]){re.escape(CONTEXT_DOTTED)}(?={_PKG}\.[A-Za-z_])")
_TESTS_DOTTED = re.compile(rf"(?<![\w.])tests\.(?={_TEST_PKG}\.[A-Za-z_])")
_TESTS_DOTTED_INV = re.compile(rf"(?<![\w.])tests\.{re.escape(CONTEXT_DOTTED)}(?={_TEST_PKG}\.[A-Za-z_])")
_PATH_LITERAL = re.compile(rf"(?<=[\"'])(?={_PKG}/[\w{{])")
_SUBDIRS_ARG = re.compile(rf"(?<=subdirs\([\"'])(?={_PKG}[\"'])")
_PATH_LITERAL_INV = re.compile(rf"(?<=[\"']){re.escape(CONTEXT_DIR)}/(?={_PKG}(?:/[\w{{]|[\"']))")
_IMPORTLINTER_MODULE = re.compile(rf"^(\s+)({_PKG}(?:\.[\w.]+)?)\s*$")
_IMPORTLINTER_MODULE_INV = re.compile(rf"^(\s+){re.escape(CONTEXT_DOTTED)}({_PKG}(?:\.[\w.]+)?)\s*$")
_IMPORTLINTER_KEY = re.compile(r"^(\w+)\s*=")
_WRAPPED_NOQA = re.compile(r"^(from [\w.]+ import \(\n\s+\w+,)\n\)(  # noqa: [^\n]+)$", re.MULTILINE)
_WRAPPED_NOQA_INV = re.compile(r"^(from [\w.]+ import \(\n\s+\w+,)(  # noqa: [^\n]+)\n\)$", re.MULTILINE)


def _run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, check=True, capture_output=capture, text=True)
    return result.stdout if capture else ""


def _git(*args: str, capture: bool = False) -> str:
    return _run("git", "-C", str(REPO), *args, capture=capture)


def _uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        sys.exit("uv is required on PATH")
    return uv


def new_path(old: str) -> str:
    """Return the backend-relative path a BASE file has after the move."""
    for source, target in MOVES:
        if old == source or old.startswith(f"{source}/"):
            return target + old[len(source) :]
    return old


def old_path(new: str) -> str:
    """Return the backend-relative BASE path of a file after the move."""
    for source, target in MOVES:
        if new == target or new.startswith(f"{target}/"):
            return source + new[len(target) :]
    return new


def _root_index(path: str) -> int:
    """Return N such that ``Path(__file__).resolve().parents[N]`` is the backend."""
    return len(PurePosixPath(path).parts) - 1


def _renumber_root_hop(text: str, from_path: str, to_path: str) -> str:
    source, target = _root_index(from_path), _root_index(to_path)
    if source == target:
        return text

    def replace(match: re.Match[str]) -> str:
        if int(match.group(2)) != source:
            return match.group(0)
        return f"{match.group(1)}{target}{match.group(3)}"

    return _ROOT_HOP.sub(replace, text)


def _segment_pattern(path: str) -> re.Pattern[str]:
    anchor = (
        r"(?<![\w.])_?BACKEND\b"
        rf"|Path\(__file__\)\.resolve\(\)\.parents\[{_root_index(path)}\]"
    )
    return re.compile(rf"(?P<anchor>{anchor})(?P<sep>\s*/\s*)(?=\"{_PKG}\")")


def _segment_inverse_pattern(path: str) -> re.Pattern[str]:
    anchor = (
        r"(?<![\w.])_?BACKEND\b"
        rf"|Path\(__file__\)\.resolve\(\)\.parents\[{_root_index(path)}\]"
    )
    return re.compile(
        rf"(?P<anchor>{anchor})(?P<sep>\s*/\s*)\"context\"\s*/\s*"
        rf"\"table_maintenance\"\s*/\s*(?=\"{_PKG}\")"
    )


def forward_python(text: str, old: str, new: str) -> str:
    """Apply rules R1 to R6 to the text of one Python file."""
    text = _renumber_root_hop(text, old, new)
    for before, after in DERIVED_ROOT_HOPS.get(new, ()):
        text = text.replace(before, after)
    text = _DOTTED.sub(CONTEXT_DOTTED, text)
    text = _TESTS_DOTTED.sub(f"tests.{CONTEXT_DOTTED}", text)
    text = _PATH_LITERAL.sub(f"{CONTEXT_DIR}/", text)
    text = _SUBDIRS_ARG.sub(f"{CONTEXT_DIR}/", text)
    return _segment_pattern(new).sub(r'\g<anchor>\g<sep>"context"\g<sep>"table_maintenance"\g<sep>', text)


def inverse_python(text: str, old: str, new: str) -> str:
    """Undo rules R7 to R1 on the text of one Python file."""
    text = _WRAPPED_NOQA_INV.sub("\\1\n)\\2", text)
    text = _segment_inverse_pattern(new).sub(r"\g<anchor>\g<sep>", text)
    text = _PATH_LITERAL_INV.sub("", text)
    text = _TESTS_DOTTED_INV.sub("tests.", text)
    text = _DOTTED_INV.sub("", text)
    for before, after in DERIVED_ROOT_HOPS.get(new, ()):
        text = text.replace(after, before)
    return _renumber_root_hop(text, new, old)


def _map_importlinter(text: str, pattern: re.Pattern[str], prefix: str) -> str:
    lines = []
    key = ""
    for line in text.splitlines(keepends=True):
        mapped = line
        if found := _IMPORTLINTER_KEY.match(line):
            key = found.group(1)
        elif line.startswith("["):
            key = ""
        elif key != "root_packages" and (found := pattern.match(line)):
            mapped = f"{found.group(1)}{prefix}{found.group(2)}\n"
        lines.append(mapped)
    return "".join(lines)


def forward_importlinter(text: str) -> str:
    """Apply rule I to ``.importlinter``."""
    return _map_importlinter(text, _IMPORTLINTER_MODULE, CONTEXT_DOTTED)


def inverse_importlinter(text: str) -> str:
    """Undo rule I on ``.importlinter``."""
    return _map_importlinter(text, _IMPORTLINTER_MODULE_INV, "")


def move() -> None:
    """Move the packages, write the structural packages and rewrite references."""
    for source, target in MOVES:
        if not (BACKEND / source).is_dir() or (BACKEND / target).exists():
            sys.exit(f"cannot move {source} to {target}: already moved?")
    for source, target in MOVES:
        (BACKEND / target).parent.mkdir(parents=True, exist_ok=True)
        _git("mv", f"{BACKEND_REL}/{source}", f"{BACKEND_REL}/{target}")
    for path, content in STRUCTURAL_INITS.items():
        (BACKEND / path).write_text(content)
    tracked = _git("ls-files", "--", BACKEND_REL, capture=True).splitlines()
    python_files = [p.removeprefix(f"{BACKEND_REL}/") for p in tracked if p.endswith(".py")]
    for new in python_files:
        file = BACKEND / new
        text = file.read_text()
        rewritten = forward_python(text, old_path(new), new)
        if rewritten != text:
            file.write_text(rewritten)
    config = BACKEND / ".importlinter"
    config.write_text(forward_importlinter(config.read_text()))
    _run(_uv(), "run", "--project", str(BACKEND), "--directory", str(BACKEND), "ruff", "format", ".")
    for new in python_files:
        file = BACKEND / new
        text = file.read_text()
        rewritten = _WRAPPED_NOQA.sub("\\1\\2\n)", text)
        if rewritten != text:
            file.write_text(rewritten)


def _normalize_python(pairs: dict[str, tuple[str, str]]) -> dict[str, tuple[str, str]]:
    """Format both sides of every pair with the same layout-insensitive ruff run."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for side, index in (("old", 0), ("new", 1)):
            for name, texts in pairs.items():
                target = root / side / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(texts[index])
        _run(
            _uv(),
            "run",
            "--project",
            str(BACKEND),
            "ruff",
            "format",
            "--quiet",
            "--isolated",
            "--target-version",
            "py314",
            "--line-length",
            "88",
            "--config",
            "format.skip-magic-trailing-comma = true",
            str(root),
        )
        return {name: ((root / "old" / name).read_text(), (root / "new" / name).read_text()) for name in pairs}


def _residuals(old_text: str, new_text: str, actual: list[str]) -> list[tuple[int, str]]:
    before, after = old_text.splitlines(), new_text.splitlines()
    found: list[tuple[int, str]] = []
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        found.extend((j1 + 1, f"(removed) {line.strip()}") for line in before[i1:i2])
        for j in range(j1, j2):
            text = after[j].strip()
            line_no = next((n + 1 for n, a in enumerate(actual) if a.strip() == text), j + 1)
            found.append((line_no, text))
    return found


def check(base: str) -> int:
    """Compare the moved backend with ``base`` after undoing the rules."""
    listing = _git("ls-tree", "-r", "--name-only", base, "--", BACKEND_REL, capture=True)
    old_files = [p.removeprefix(f"{BACKEND_REL}/") for p in listing.splitlines()]
    failures = 0
    python: dict[str, tuple[str, str]] = {}
    plain: dict[str, tuple[str, str]] = {}
    for old in old_files:
        new = new_path(old)
        file = BACKEND / new
        if not file.is_file():
            print(f"missing: {new}")
            failures += 1
            continue
        old_text = _git("show", f"{base}:{BACKEND_REL}/{old}", capture=True)
        text = file.read_text()
        if new.endswith(".py"):
            python[new] = (old_text, inverse_python(text, old, new))
        elif new == ".importlinter":
            plain[new] = (old_text, inverse_importlinter(text))
        else:
            plain[new] = (old_text, text)
    expected = {new_path(old) for old in old_files} | set(STRUCTURAL_INITS)
    present = _git(
        "ls-files", "--cached", "--others", "--exclude-standard", "--", BACKEND_REL, capture=True
    ).splitlines()
    for path in sorted({p.removeprefix(f"{BACKEND_REL}/") for p in present} - expected):
        if (BACKEND / path).exists():
            print(f"unexpected: {path}")
            failures += 1
    for source, _ in MOVES:
        if (BACKEND / source).exists():
            print(f"leftover: {source}")
            failures += 1
    compared = {**_normalize_python(python), **plain}
    residual_count = 0
    for new in sorted(compared):
        old_text, new_text = compared[new]
        actual = (BACKEND / new).read_text().splitlines()
        for line_no, text in _residuals(old_text, new_text, actual):
            residual_count += 1
            allowed = (new, text) in ALLOWED_RESIDUALS
            print(f"residual: {new}:{line_no}: {text}{'' if allowed else '  [NOT ALLOWED]'}")
            failures += 0 if allowed else 1
    print(f"compared {len(compared)} files, {residual_count} residual lines, {failures} failures")
    return 0 if failures == 0 else 1


def main() -> int:
    """Parse the command line and run ``move`` or ``check``."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("move", help="move the packages and rewrite references")
    check_parser = commands.add_parser("check", help="verify the move against BASE")
    check_parser.add_argument("base", help="commit the move started from")
    args = parser.parse_args()
    if args.command == "move":
        move()
        return 0
    return check(args.base)


if __name__ == "__main__":
    sys.exit(main())
