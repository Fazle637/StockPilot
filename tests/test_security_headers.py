import re

import pytest

PATHS = ["/login", "/register", "/health", "/does-not-exist"]


@pytest.mark.parametrize("path", PATHS)
def test_responses_carry_security_headers(client, path):
    headers = client.get(path).headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "same-origin"

    csp = headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp


def test_csp_does_not_allow_inline_or_eval_scripts(client):
    csp = client.get("/login").headers.get("Content-Security-Policy", "")

    script_src = re.search(r"script-src([^;]*)", csp)
    assert script_src, "CSP has no script-src directive"
    assert "'unsafe-inline'" not in script_src.group(1)
    assert "'unsafe-eval'" not in csp