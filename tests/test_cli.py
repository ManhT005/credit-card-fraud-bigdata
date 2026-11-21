"""Smoke tests for the scaffold CLI."""

from fraud_detection.cli import main


def test_info(capsys):
    assert main(["info"]) == 0
    output = capsys.readouterr().out
    assert "OpenML 1597" in output
    assert "skeleton" in output


def test_help(capsys):
    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out
