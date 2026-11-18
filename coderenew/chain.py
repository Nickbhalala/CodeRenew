"""The modernization pipeline: scan -> plan -> rewrite -> validate -> (repair)* -> accept."""

from __future__ import annotations

import difflib
import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import prompts
from .llm import LLMClient
from .scanner import Finding, iter_cpp_files, scan_source
from .validate import run_tests, validate_candidate

_CODE_BLOCK = re.compile(r"```(?:cpp|c\+\+|cc|hpp)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_JSON_BLOCK = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code(reply: str) -> str:
    m = _CODE_BLOCK.search(reply)
    code = m.group(1) if m else reply
    return code.rstrip() + "\n"


def extract_plan(reply: str) -> list[dict[str, Any]]:
    m = _JSON_BLOCK.search(reply)
    text = (m.group(1) if m else reply).strip()
    data = json.loads(text)
    if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
        raise ValueError("plan must be a JSON array of objects")
    return data


@dataclass
class FileResult:
    path: Path
    status: str  # "modernized" | "rejected" | "skipped" | "clean"
    findings_before: int = 0
    findings_after: int = 0
    attempts: int = 0
    plan: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    diff: str = ""


class BaselineError(RuntimeError):
    """The project's tests fail before any change, so rewrites can't be validated."""


class Modernizer:
    def __init__(
        self,
        llm: LLMClient,
        *,
        std: str = "c++17",
        test_cmd: str | None = None,
        max_repairs: int = 2,
        max_file_lines: int = 800,
        cxx: str | None = None,
    ):
        self.llm = llm
        self.std = std
        self.test_cmd = test_cmd
        self.max_repairs = max_repairs
        self.max_file_lines = max_file_lines
        self.cxx = cxx
        self.system = prompts.SYSTEM.format(std=std)

    def run(self, root: Path, only: list[Path] | None = None) -> tuple[list[FileResult], Path]:
        """Modernize files under `root` in a scratch copy. Returns results and the copy's path.

        Each accepted file is written into the scratch copy, so later files are validated
        against earlier accepted changes. Nothing in `root` is modified.
        """
        root = root.resolve()
        workspace = Path(tempfile.mkdtemp(prefix="coderenew-ws-")) / root.name
        shutil.copytree(root, workspace, ignore=shutil.ignore_patterns(".git"))

        if self.test_cmd:
            failure = run_tests(workspace, self.test_cmd)
            if failure:
                raise BaselineError(f"tests fail before any change:\n{failure}")

        files = [p.resolve() for p in only] if only else iter_cpp_files(root)
        results = [self._process(root, workspace, p.relative_to(root)) for p in files]
        return results, workspace

    def _process(self, root: Path, workspace: Path, rel: Path) -> FileResult:
        source = (workspace / rel).read_text()
        findings = scan_source(source)
        result = FileResult(
            rel, "clean", findings_before=len(findings), findings_after=len(findings)
        )
        if not findings:
            return result
        if source.count("\n") > self.max_file_lines:
            result.status = "skipped"
            result.errors.append(f"file has more than {self.max_file_lines} lines")
            return result

        # Step 1: analyze -> plan
        try:
            plan = extract_plan(
                self.llm.complete(
                    self.system,
                    prompts.ANALYZE.format(
                        path=rel, findings=_format_findings(findings), source=source
                    ),
                )
            )
        except (ValueError, json.JSONDecodeError) as e:
            result.status = "skipped"
            result.errors.append(f"could not parse plan: {e}")
            return result
        result.plan = plan
        if not plan:
            result.status = "skipped"
            result.errors.append("model proposed no safe changes")
            return result

        # Step 2: rewrite, then validate / repair
        reply = self.llm.complete(
            self.system,
            prompts.REWRITE.format(path=rel, plan=json.dumps(plan, indent=2), source=source),
        )
        for attempt in range(1, self.max_repairs + 2):
            candidate = extract_code(reply)
            result.attempts = attempt
            check = validate_candidate(
                workspace,
                rel,
                source,
                candidate,
                std=self.std,
                test_cmd=self.test_cmd,
                cxx=self.cxx,
            )
            result.findings_after = check.findings_after
            if check.ok:
                (workspace / rel).write_text(candidate)
                result.status = "modernized"
                result.errors = []
                result.diff = "".join(
                    difflib.unified_diff(
                        source.splitlines(keepends=True),
                        candidate.splitlines(keepends=True),
                        fromfile=f"a/{rel}",
                        tofile=f"b/{rel}",
                    )
                )
                return result
            result.errors = check.errors
            if attempt > self.max_repairs:
                break
            reply = self.llm.complete(
                self.system,
                prompts.REPAIR.format(
                    path=rel, errors=check.feedback(), candidate=candidate, source=source
                ),
            )

        result.status = "rejected"
        result.findings_after = result.findings_before
        return result


def _format_findings(findings: list[Finding]) -> str:
    return "\n".join(f"- {f}  `{f.snippet}`" for f in findings)


def write_report(results: list[FileResult], out_dir: Path) -> tuple[Path, Path]:
    """Write changes.patch (git-applyable) and report.md."""
    out_dir.mkdir(parents=True, exist_ok=True)
    patch = out_dir / "changes.patch"
    patch.write_text("".join(r.diff for r in results if r.diff))

    lines = [
        "# CodeRenew report",
        "",
        "| File | Status | Legacy findings (before -> after) | Attempts |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| `{r.path}` | {r.status} | {r.findings_before} -> {r.findings_after} "
            f"| {r.attempts} |"
        )
    for r in results:
        if r.plan or r.errors:
            lines += ["", f"## `{r.path}`", ""]
            for item in r.plan:
                lines.append(
                    f"- **{item.get('id', '?')}** ({item.get('risk', '?')} risk): "
                    f"{item.get('change', '')}"
                )
            if r.errors:
                lines += ["", "Last validation errors:", "", "```text", *r.errors, "```"]
    report = out_dir / "report.md"
    report.write_text("\n".join(lines) + "\n")
    return patch, report


def apply_results(results: list[FileResult], workspace: Path, root: Path) -> list[Path]:
    applied = []
    for r in results:
        if r.status == "modernized":
            shutil.copyfile(workspace / r.path, root / r.path)
            applied.append(r.path)
    return applied
