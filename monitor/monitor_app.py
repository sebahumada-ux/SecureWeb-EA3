"""Aplicacion Flask segura instrumentada para la monitorizacion local de la EV3."""
from time import perf_counter

from flask import Response, g, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app_secure import app

REQUESTS = Counter(
    "secureweb_http_requests_total",
    "Cantidad de peticiones HTTP recibidas por SecureWeb",
    ["method", "endpoint", "status"],
)

DURATION = Histogram(
    "secureweb_http_request_duration_seconds",
    "Duracion de las peticiones HTTP en segundos",
    ["endpoint"],
)


@app.before_request
def start_request_timer():
    g.request_started = perf_counter()


@app.after_request
def record_request_metrics(response):
    if request.path != "/metrics":
        endpoint = request.url_rule.rule if request.url_rule else "not_found"
        REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
        DURATION.labels(endpoint).observe(
            perf_counter() - getattr(g, "request_started", perf_counter())
        )
    return response


@app.get("/health")
def health():
    return "OK", 200


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
