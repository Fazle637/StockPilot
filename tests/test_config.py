from pathlib import Path


def test_run_py_does_not_enable_debug_mode():
    run_py = Path(__file__).resolve().parent.parent / "run.py"
    source = run_py.read_text(encoding="utf-8")

    assert "debug=True" not in source
