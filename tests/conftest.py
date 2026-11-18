import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXAMPLE = ROOT / "examples" / "legacy_inventory"

needs_compiler = pytest.mark.skipif(
    not (shutil.which("g++") or shutil.which("clang++")) or not shutil.which("make"),
    reason="needs a C++ compiler and make",
)


@pytest.fixture
def project(tmp_path) -> Path:
    """A fresh copy of the legacy example project."""
    dest = tmp_path / "legacy_inventory"
    shutil.copytree(EXAMPLE, dest)
    return dest


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()
