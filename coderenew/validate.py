"""Checks a candidate rewrite: it must compile, keep tests green, and not add legacy idioms."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .scanner import scan_source


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    findings_before: int = 0
    findings_after: int = 0

    def feedback(self, max_chars: int = 4000) -> str:
        """Error text to give the model in a repair step."""
        return "\n\n".join(self.errors)[:max_chars]


def find_compiler(preferred: str | None = None) -> str:
    for cxx in [preferred, "g++", "clang++"]:
        if cxx and shutil.which(cxx):
            return cxx
    raise RuntimeError("no C++ compiler found (install g++ or clang++)")


def syntax_check(
    path: Path, std: str, include_dirs: list[Path], cxx: str, timeout: int = 60
) -> str | None:
    """Return compiler diagnostics, or None if the file compiles cleanly."""
    lang = ["-x", "c++-header"] if path.suffix in {".h", ".hpp", ".hh", ".hxx"} else []
    cmd = [cxx, f"-std={std}", "-fsyntax-only", "-Wall", "-Wextra", *lang]
    for d in include_dirs:
        cmd += ["-I", str(d)]
    cmd.append(str(path))
    # LC_ALL=C keeps diagnostics in plain ASCII so they read the same everywhere.
    env = {**os.environ, "LC_ALL": "C"}
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    if proc.returncode != 0:
        return proc.stderr.strip() or "compiler failed without output"
    return None


def run_tests(workdir: Path, test_cmd: str, timeout: int = 300) -> str | None:
    """Run the project's own test command. Return its output on failure, else None."""
    try:
        proc = subprocess.run(
            test_cmd, shell=True, cwd=workdir, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"test command timed out after {timeout}s"
    if proc.returncode != 0:
        out = (proc.stdout + "\n" + proc.stderr).strip()
        return f"test command `{test_cmd}` failed (exit {proc.returncode}):\n{out[-3000:]}"
    return None


def validate_candidate(
    project_root: Path,
    rel_path: Path,
    original: str,
    candidate: str,
    *,
    std: str = "c++17",
    test_cmd: str | None = None,
    cxx: str | None = None,
) -> ValidationResult:
    """Validate `candidate` as a replacement for `rel_path` inside a scratch copy of the project."""
    before = len(scan_source(original))
    after = len(scan_source(candidate))
    result = ValidationResult(ok=True, findings_before=before, findings_after=after)

    if candidate.strip() == original.strip():
        result.ok = False
        result.errors.append("the rewrite is identical to the original")
        return result
    if after > before:
        result.ok = False
        result.errors.append(
            f"the rewrite has more legacy findings ({after}) than the original ({before})"
        )

    compiler = find_compiler(cxx)
    with tempfile.TemporaryDirectory(prefix="coderenew-") as tmp:
        work = Path(tmp) / "project"
        shutil.copytree(project_root, work, ignore=shutil.ignore_patterns(".git", "build"))
        target = work / rel_path
        target.write_text(candidate)

        diag = syntax_check(target, std, [target.parent, work], compiler)
        if diag:
            result.ok = False
            result.errors.append(f"compiler errors in {rel_path}:\n{diag}")
        elif test_cmd:
            failure = run_tests(work, test_cmd)
            if failure:
                result.ok = False
                result.errors.append(failure)
    return result
