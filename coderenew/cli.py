"""coderenew scan <path> | coderenew modernize <project> [options]"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from .scanner import scan_path


def cmd_scan(args: argparse.Namespace) -> int:
    total = 0
    root = Path(args.path)
    for path, findings in scan_path(root).items():
        if not findings:
            continue
        print(f"{path}: {len(findings)} findings")
        for f in findings:
            print(f"  {f}")
        total += len(findings)
    print(f"\n{total} legacy findings")
    return 0


def cmd_modernize(args: argparse.Namespace) -> int:
    from dotenv import load_dotenv

    from .chain import BaselineError, Modernizer, apply_results, write_report
    from .llm import OpenAIClient

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("error: OPENAI_API_KEY is not set (see .env.example)", file=sys.stderr)
        return 2
    root = Path(args.project).resolve()
    llm = OpenAIClient(model=os.getenv("CODERENEW_MODEL", "gpt-4o"))
    modernizer = Modernizer(llm, std=args.std, test_cmd=args.test_cmd, max_repairs=args.max_repairs)
    only = [root / f for f in args.files] if args.files else None
    try:
        results, workspace = modernizer.run(root, only)
    except BaselineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    patch, report = write_report(results, Path(args.out))
    for r in results:
        print(f"{r.status:>10}  {r.path}  ({r.findings_before} -> {r.findings_after} findings)")
    print(f"\nreport: {report}\npatch:  {patch}")
    if args.apply:
        applied = apply_results(results, workspace, root)
        print(f"applied {len(applied)} file(s) to {root}")
    shutil.rmtree(workspace.parent, ignore_errors=True)
    return 0 if all(r.status != "rejected" for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="coderenew", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="list legacy C++ idioms (no LLM)")
    scan.add_argument("path")
    scan.set_defaults(func=cmd_scan)

    mod = sub.add_parser("modernize", help="rewrite files with an LLM, validated by the compiler")
    mod.add_argument("project", help="project root (copied; not modified unless --apply)")
    mod.add_argument("files", nargs="*", help="files to process, relative to the project root")
    mod.add_argument("--std", default="c++17")
    mod.add_argument("--test-cmd", help='e.g. "make test"; must pass before and after each change')
    mod.add_argument("--max-repairs", type=int, default=2)
    mod.add_argument("--out", default="coderenew-out")
    mod.add_argument("--apply", action="store_true", help="write accepted files back")
    mod.set_defaults(func=cmd_modernize)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
