from coderenew import cli
from tests.conftest import EXAMPLE


def test_scan_command(capsys):
    assert cli.main(["scan", str(EXAMPLE)]) == 0
    out = capsys.readouterr().out
    assert "inventory.h: 4 findings" in out
    assert "[typedef]" in out


def test_modernize_requires_key(monkeypatch, capsys, project):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    assert cli.main(["modernize", str(project)]) == 2
    assert "OPENAI_API_KEY" in capsys.readouterr().err
