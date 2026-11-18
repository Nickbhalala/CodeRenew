"""Finds pre-C++11 idioms with lightweight pattern rules.

Comments and string literals are blanked out first (keeping line numbers), so a
"NULL" inside a comment or a "new" inside a string is not reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CPP_SUFFIXES = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx"}


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]
    message: str
    suggestion: str


RULES: list[Rule] = [
    Rule("null-macro", re.compile(r"\bNULL\b"), "NULL macro", "use nullptr"),
    Rule(
        "raw-new", re.compile(r"\bnew\s+[A-Za-z_]"), "raw new", "use std::make_unique / containers"
    ),
    Rule(
        "raw-delete",
        re.compile(r"\bdelete\s*(\[\s*\])?\s*[A-Za-z_(]"),
        "manual delete",
        "let RAII types own memory",
    ),
    Rule(
        "c-style-cast",
        # `(void)x` (discarding a value) is idiomatic, so bare void is not matched.
        re.compile(
            r"\((?:const\s+)?(?:unsigned\s+)?(?:(?:int|long|short|char|float|double|bool|"
            r"size_t)\s*\**|void\s*\*+)\s*\)\s*[A-Za-z_(]"
        ),
        "C-style cast",
        "use static_cast / reinterpret_cast",
    ),
    Rule("typedef", re.compile(r"^\s*typedef\b", re.MULTILINE), "typedef", "use a using alias"),
    Rule(
        "define-constant",
        re.compile(r"^\s*#\s*define\s+[A-Z_][A-Z0-9_]*\s+[-\d.]+\s*$", re.MULTILINE),
        "#define constant",
        "use constexpr",
    ),
    Rule(
        "auto-ptr",
        re.compile(r"\bstd::auto_ptr\b"),
        "std::auto_ptr (removed in C++17)",
        "use std::unique_ptr",
    ),
    Rule(
        "malloc-free",
        re.compile(r"\b(?:std::)?(?:malloc|calloc|realloc|free)\s*\("),
        "malloc/free",
        "use containers or smart pointers",
    ),
    Rule(
        "unsafe-c-string",
        re.compile(r"\b(?:std::)?(?:strcpy|strcat|sprintf|gets)\s*\("),
        "unbounded C string function",
        "use std::string / snprintf",
    ),
    Rule(
        "index-loop",
        re.compile(
            r"for\s*\(\s*(?:int|size_t|unsigned)\s+(\w+)\s*=\s*0\s*;\s*\1\s*<\s*[\w.>-]+"
            r"(?:\.size\(\))?\s*;\s*(?:\1\+\+|\+\+\1)\s*\)"
        ),
        "index-based loop",
        "consider a range-based for loop",
    ),
    Rule(
        "private-copy-ctor",
        re.compile(r"^\s*(\w+)\s*\(\s*const\s+\1\s*&\s*\w*\s*\)\s*;", re.MULTILINE),
        "copy constructor declared but not defined (C++98 non-copyable idiom)",
        "use = delete",
    ),
    Rule(
        "throw-spec",
        re.compile(r"\)\s*throw\s*\(\s*\)"),
        "dynamic exception specification",
        "use noexcept",
    ),
]


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    message: str
    suggestion: str
    snippet: str

    def __str__(self) -> str:
        return f"L{self.line} [{self.rule}] {self.message}: {self.suggestion}"


_TOKEN = re.compile(
    r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'',
    re.DOTALL,
)


def strip_comments_and_strings(source: str) -> str:
    """Replace comments and literals with spaces, preserving newlines and offsets."""

    def blank(m: re.Match[str]) -> str:
        text = m.group(0)
        if text.startswith(("'", '"')):
            return text[0] + re.sub(r"[^\n]", " ", text[1:-1]) + text[-1]
        return re.sub(r"[^\n]", " ", text)

    return _TOKEN.sub(blank, source)


def scan_source(source: str) -> list[Finding]:
    code = strip_comments_and_strings(source)
    lines = source.splitlines()
    findings: list[Finding] = []
    for rule in RULES:
        for m in rule.pattern.finditer(code):
            line_no = code.count("\n", 0, m.start()) + 1
            # MULTILINE '^\s*' matches can start on a preceding blank line.
            while line_no <= len(lines) and not lines[line_no - 1].strip():
                line_no += 1
            snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
            findings.append(Finding(rule.id, line_no, rule.message, rule.suggestion, snippet))
    return sorted(findings, key=lambda f: (f.line, f.rule))


def iter_cpp_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(p for p in root.rglob("*") if p.suffix in CPP_SUFFIXES and p.is_file())


def scan_path(root: Path) -> dict[Path, list[Finding]]:
    return {p: scan_source(p.read_text()) for p in iter_cpp_files(root)}
