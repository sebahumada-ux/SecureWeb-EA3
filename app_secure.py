
from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    )
    return response

@app.route("/hello")
def hello():
    name = request.args.get("name", "")
    return f"Hello, {escape(name)}!"

if __name__ == "__main__":
    app.run(debug=False)
