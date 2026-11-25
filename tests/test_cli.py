from asts.cli import ascii_curve, main


def test_ascii_curve_shape():
    out = ascii_curve([100 + i for i in range(200)], width=30, height=8)
    lines = out.splitlines()
    assert len(lines) == 8
    assert all("|" in ln for ln in lines)
    assert out.count("*") == 30


def test_run_chart_flag(capsys):
    assert main(["run", "--suite", "suite3", "--synthetic", "--stocks", "10", "--chart"]) == 0
    assert "Equity curve" in capsys.readouterr().out
