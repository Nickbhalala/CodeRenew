import json
from pathlib import Path

import pytest

from coderenew.chain import (
    BaselineError,
    Modernizer,
    apply_results,
    extract_code,
    extract_plan,
    write_report,
)
from coderenew.llm import ScriptedLLM
from tests.conftest import fixture, needs_compiler

PLAN = json.dumps(
    [
        {
            "id": "nullptr",
            "lines": [7, 10],
            "change": "NULL -> nullptr",
            "risk": "low",
            "reason": "same semantics",
        },
        {
            "id": "report-buffer",
            "lines": [83, 88],
            "change": "bounded snprintf into std::string",
            "risk": "medium",
            "reason": "removes overflow risk, same output",
        },
    ]
)


def code(name: str) -> str:
    return f"Here you go:\n```cpp\n{fixture(name)}```\n"


def test_extractors():
    assert extract_code("```cpp\nint x;\n```") == "int x;\n"
    assert extract_code("int y;") == "int y;\n"
    assert extract_plan(f"```json\n{PLAN}\n```")[0]["id"] == "nullptr"
    with pytest.raises(ValueError):
        extract_plan('{"not": "a list"}')


@needs_compiler
def test_modernizes_file_and_leaves_original_untouched(project, tmp_path):
    llm = ScriptedLLM([PLAN, code("inventory_modern.cpp")])
    m = Modernizer(llm, test_cmd="make -s test")
    results, workspace = m.run(project, only=[project / "inventory.cpp"])

    [r] = results
    assert r.status == "modernized" and r.attempts == 1
    assert r.findings_after < r.findings_before
    assert "+Inventory::Inventory() : items_(nullptr), size_(0) {" in r.diff
    assert "NULL" in (project / "inventory.cpp").read_text()  # root untouched
    assert "nullptr" in (workspace / "inventory.cpp").read_text()

    # The model saw the scanner's findings and the approved plan.
    assert "[null-macro]" in llm.calls[0][1]
    assert "report-buffer" in llm.calls[1][1]

    patch, report = write_report(results, tmp_path / "out")
    assert patch.read_text() == r.diff
    assert "| `inventory.cpp` | modernized |" in report.read_text()


@needs_compiler
def test_repairs_after_compiler_error(project):
    llm = ScriptedLLM([PLAN, code("inventory_syntax_error.cpp"), code("inventory_modern.cpp")])
    [r], _ = Modernizer(llm, test_cmd="make -s test").run(project, [project / "inventory.cpp"])
    assert r.status == "modernized" and r.attempts == 2
    repair_prompt = llm.calls[2][1]
    assert "expected ';'" in repair_prompt
    assert "return size_\n" in repair_prompt  # the rejected candidate is shown


@needs_compiler
def test_rejects_behavior_change_after_repairs(project):
    bad = code("inventory_reorders.cpp")
    llm = ScriptedLLM([PLAN, bad, bad])
    [r], ws = Modernizer(llm, test_cmd="make -s test", max_repairs=1).run(
        project, [project / "inventory.cpp"]
    )
    assert r.status == "rejected" and r.attempts == 2
    assert "failed" in r.errors[0]
    assert "NULL" in (ws / "inventory.cpp").read_text()  # rejected change not kept


@needs_compiler
def test_header_then_source_in_one_run_and_apply(project):
    header_plan = json.dumps(
        [
            {
                "id": "constexpr",
                "lines": [9, 10],
                "change": "constexpr",
                "risk": "low",
                "reason": "same values",
            }
        ]
    )
    llm = ScriptedLLM(
        [header_plan, fixture("inventory_modern.h"), PLAN, code("inventory_modern.cpp")]
    )
    results, ws = Modernizer(llm, test_cmd="make -s test").run(
        project, [project / "inventory.h", project / "inventory.cpp"]
    )
    assert [r.status for r in results] == ["modernized", "modernized"]
    applied = apply_results(results, ws, project)
    assert applied == [Path("inventory.h"), Path("inventory.cpp")]
    assert "constexpr int MAX_ITEMS" in (project / "inventory.h").read_text()


def test_unparseable_plan_skips_file(project):
    [r], _ = Modernizer(ScriptedLLM(["I think you should use nullptr."])).run(
        project, [project / "inventory.cpp"]
    )
    assert r.status == "skipped" and "could not parse plan" in r.errors[0]


def test_empty_plan_skips_file(project):
    [r], _ = Modernizer(ScriptedLLM(["[]"])).run(project, [project / "inventory.cpp"])
    assert r.status == "skipped"


@needs_compiler
def test_baseline_must_pass(project):
    (project / "inventory_tests.cpp").write_text("int main() { return 1; }\n")
    with pytest.raises(BaselineError):
        Modernizer(ScriptedLLM([]), test_cmd="make -s test").run(project)
