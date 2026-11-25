"""Test the Helm chart mutation tool: which mutants it makes and how it judges them."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

_SPEC = importlib.util.spec_from_file_location("mutate_chart", Path(__file__).resolve().parents[1] / "mutate_chart.py")
assert _SPEC and _SPEC.loader
mutate_chart = importlib.util.module_from_spec(_SPEC)
sys.modules["mutate_chart"] = mutate_chart
_SPEC.loader.exec_module(mutate_chart)

TEMPLATE = """\
{{- if and .Values.a .Values.b }}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "x.fullname" . }}
data:
  key: {{ get (dict "s" "size_s") "s" | quote }}
  limit: {{ gt (int .Values.n) 1 }}
{{- end }}
{{- if not .Values.c }}
{{- fail "c is required" }}
{{- end }}
"""


def _mutants(text: str = TEMPLATE, path: str = "templates/x.yaml") -> list:
    return mutate_chart.template_mutants(path, text)


def _by(operator: str, text: str = TEMPLATE) -> list:
    return [m for m in _mutants(text) if m.operator == operator]


def test_a_fail_line_is_removed():
    """A refusal the chart makes is dropped, so a test that expects it must notice."""
    (mutant,) = _by("remove-fail")
    assert mutant.original == '{{- fail "c is required" }}'
    assert mutant.mutated == ""


def test_an_if_is_negated():
    """Each condition, plain or `else if`, is turned around."""
    negated = {m.mutated for m in _by("negate-if")}
    assert "{{- if not (and .Values.a .Values.b) }}" in negated
    assert "{{- if not (not .Values.c) }}" in negated


def test_and_becomes_or_and_or_becomes_and():
    """Each `and` or `or` in an action is swapped on its own."""
    (mutant,) = _by("swap-and-or")
    assert mutant.mutated == "{{- if or .Values.a .Values.b }}"
    (back,) = _by("swap-and-or", "{{- if or .Values.a (and .Values.b .Values.c) }}\n")[:1]
    assert back.mutated == "{{- if and .Values.a (and .Values.b .Values.c) }}"


def test_each_string_literal_in_an_action_is_changed_once():
    """A key or a value written in a template changes, one literal per mutant."""
    changed = [m for m in _by("change-string") if m.line == 7]
    assert {m.mutated for m in changed} == {
        '  key: {{ get (dict "s-mutant" "size_s") "s" | quote }}',
        '  key: {{ get (dict "s" "size_s-mutant") "s" | quote }}',
        '  key: {{ get (dict "s" "size_s") "s-mutant" | quote }}',
    }


def test_the_name_given_to_include_is_left_alone():
    """Renaming a helper only breaks rendering, which every test catches; it says nothing about the tests."""
    assert not [m for m in _by("change-string") if m.line == 5]


def test_a_number_in_an_action_is_moved_by_one():
    """A limit written in a template moves by one."""
    (mutant,) = _by("change-number")
    assert mutant.mutated == "  limit: {{ gt (int .Values.n) 2 }}"


def test_a_plain_yaml_line_is_deleted_but_control_lines_are_not():
    """Deleting an `end` or a parent key only breaks the template, so those lines are kept."""
    deleted = {m.original for m in _by("delete-line")}
    assert "kind: ConfigMap" in deleted
    assert "  limit: {{ gt (int .Values.n) 1 }}" in deleted
    assert "{{- end }}" not in deleted
    assert "{{- if not .Values.c }}" not in deleted
    assert "metadata:" not in deleted


def test_applying_a_mutant_changes_only_its_line():
    """The rest of the file stays as it was, line for line."""
    (mutant,) = _by("remove-fail")
    lines = mutate_chart.apply(TEMPLATE, mutant).splitlines()
    original = TEMPLATE.splitlines()
    assert len(lines) == len(original)
    assert [i for i, (a, b) in enumerate(zip(lines, original, strict=True)) if a != b] == [mutant.line - 1]


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["external"],
    "properties": {
        "external": {"type": "object", "properties": {"type": {"type": "string", "enum": ["temporal"]}}},
        "replicas": {"type": "integer", "minimum": 1, "maximum": 1},
        "name": {"type": "string", "minLength": 1, "pattern": "^[a-z]+$"},
    },
}


def test_each_schema_constraint_is_removed_once():
    """Each limit the schema puts on a value is dropped on its own, leaving the others."""
    mutants = mutate_chart.schema_mutants("values.schema.json", json.dumps(SCHEMA, indent=2))
    assert {(m.original, m.operator) for m in mutants} == {
        ("/additionalProperties", "remove-constraint"),
        ("/required", "remove-constraint"),
        ("/properties/external/properties/type/enum", "remove-constraint"),
        ("/properties/replicas/minimum", "remove-constraint"),
        ("/properties/replicas/maximum", "remove-constraint"),
        ("/properties/name/minLength", "remove-constraint"),
        ("/properties/name/pattern", "remove-constraint"),
    }
    (enum,) = [m for m in mutants if m.original.endswith("/enum")]
    schema = json.loads(mutate_chart.apply("", enum))
    assert "enum" not in schema["properties"]["external"]["properties"]["type"]
    assert schema["properties"]["replicas"]["minimum"] == 1


def _chart(tmp_path: Path) -> Path:
    chart = tmp_path / "chart"
    (chart / "templates").mkdir(parents=True)
    (chart / "templates" / "x.yaml").write_text(TEMPLATE)
    (chart / "values.schema.json").write_text(json.dumps(SCHEMA, indent=2))
    return chart


def test_a_mutant_the_tests_reject_is_killed_and_one_they_accept_survives(tmp_path: Path):
    """The verdict is the test command's exit status."""
    chart = _chart(tmp_path)
    (mutant,) = _by("remove-fail")
    assert mutate_chart.killed(chart, mutant, ["false"]) is True
    assert mutate_chart.killed(chart, mutant, ["true"]) is False


def test_the_tests_run_on_a_copy_that_holds_the_mutant(tmp_path: Path):
    """The tests see the mutant, and the chart itself is never changed."""
    chart = _chart(tmp_path)
    (mutant,) = _by("remove-fail")
    command = ["sh", "-c", 'grep -q "c is required" "$1"/templates/x.yaml', "sh", "{chart}"]
    assert mutate_chart.killed(chart, mutant, command) is True
    assert "c is required" in (chart / "templates" / "x.yaml").read_text()


def test_an_ignored_mutant_is_not_run(tmp_path: Path):
    """A mutant named in the ignore file is skipped; the others still run."""
    chart = _chart(tmp_path)
    (chart / "mutation-ignore.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "file": "templates/x.yaml",
                    "operator": "remove-fail",
                    "original": '{{- fail "c is required" }}',
                    "reason": "test",
                }
            ]
        )
    )
    mutants = mutate_chart.all_mutants(chart)
    assert not [m for m in mutants if m.operator == "remove-fail"]
    assert [m for m in mutants if m.operator == "negate-if"]


def test_an_ignore_entry_without_a_reason_is_refused(tmp_path: Path):
    """Every ignored mutant says why it cannot change what the chart renders."""
    chart = _chart(tmp_path)
    (chart / "mutation-ignore.yaml").write_text(
        yaml.safe_dump([{"file": "templates/x.yaml", "operator": "remove-fail", "original": "x"}])
    )
    try:
        mutate_chart.all_mutants(chart)
    except ValueError as error:
        assert "reason" in str(error)
    else:
        raise AssertionError("an ignore entry without a reason was accepted")


def test_the_command_line_fails_when_a_mutant_survives(tmp_path: Path, capsys):
    """A survivor is listed with where it is, and fails the run."""
    chart = _chart(tmp_path)
    assert mutate_chart.main([str(chart), "--jobs", "2", "--test-command", "true"]) == 1
    out = capsys.readouterr().out
    assert "survived" in out
    assert "templates/x.yaml:11 remove-fail" in out
    assert mutate_chart.main([str(chart), "--jobs", "2", "--test-command", "false"]) == 0


def test_the_command_line_can_run_one_file(tmp_path: Path, capsys):
    """`--only` limits the run to the files it names."""
    chart = _chart(tmp_path)
    mutate_chart.main([str(chart), "--only", "values.schema.json", "--test-command", "false"])
    out = capsys.readouterr().out
    assert "templates/x.yaml" not in out
    assert "7 mutants, 7 killed" in out


def test_an_indent_width_is_left_alone():
    """A wrong indent either breaks the YAML, which every test catches, or renders the same document."""
    assert not _by("change-number", "    {{- toYaml .Values.x | nindent 4 }}\n  {{ indent 2 .y }}\n")
