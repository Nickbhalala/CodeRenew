from pathlib import Path

from coderenew.validate import validate_candidate
from tests.conftest import fixture, needs_compiler

CPP = Path("inventory.cpp")


@needs_compiler
def test_accepts_good_rewrite(project):
    original = (project / CPP).read_text()
    r = validate_candidate(
        project, CPP, original, fixture("inventory_modern.cpp"), test_cmd="make -s test"
    )
    assert r.ok, r.errors
    assert r.findings_after < r.findings_before


@needs_compiler
def test_reports_compiler_errors(project):
    original = (project / CPP).read_text()
    r = validate_candidate(project, CPP, original, fixture("inventory_syntax_error.cpp"))
    assert not r.ok
    assert "compiler errors in inventory.cpp" in r.errors[0]
    assert "expected ';'" in r.errors[0]


@needs_compiler
def test_catches_behavior_change_through_tests(project):
    original = (project / CPP).read_text()
    r = validate_candidate(
        project, CPP, original, fixture("inventory_reorders.cpp"), test_cmd="make -s test"
    )
    assert not r.ok
    assert "test command `make -s test` failed" in r.errors[0]


@needs_compiler
def test_rejects_identical_and_regressing_rewrites(project):
    original = (project / CPP).read_text()
    assert "identical" in validate_candidate(project, CPP, original, original).errors[0]
    worse = original + "\nvoid extra() { int* p = NULL; (void)p; }\n"
    r = validate_candidate(project, CPP, original, worse)
    assert not r.ok and "more legacy findings" in r.errors[0]


@needs_compiler
def test_scratch_copy_leaves_project_untouched(project):
    original = (project / CPP).read_text()
    validate_candidate(
        project, CPP, original, fixture("inventory_modern.cpp"), test_cmd="make -s test"
    )
    assert (project / CPP).read_text() == original
    assert not (project / "inventory_tests").exists()
