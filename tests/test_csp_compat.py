import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"


def test_templates_have_no_inline_event_handlers():
    offenders = []

    for path in sorted(TEMPLATES.glob("*.html")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            if re.search(r"\son[a-z]+\s*=", line):
                offenders.append(f"{path.name}:{number}")

    assert not offenders, "Inline event handlers: " + ", ".join(offenders)


def test_templates_have_no_inline_scripts():
    offenders = []

    for path in sorted(TEMPLATES.glob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"<script\b([^>]*)>", text):
            if "src=" not in match.group(1):
                offenders.append(path.name)

    assert not offenders, "Inline scripts: " + ", ".join(offenders)


def test_confirm_script_is_served(client):
    response = client.get("/static/confirm.js")

    assert response.status_code == 200