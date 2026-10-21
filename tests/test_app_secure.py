
from app_secure import app


def test_hello():
    client = app.test_client()
    response = client.get("/hello?name=TEST")

    assert response.status_code == 200
    assert b"Hello, TEST!" in response.data


def test_xss_protection():
    client = app.test_client()
    response = client.get(
        "/hello?name=<script>alert(1)</script>"
    )

    html = response.get_data(as_text=True)

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_security_headers():
    client = app.test_client()
    response = client.get("/hello?name=TEST")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers
