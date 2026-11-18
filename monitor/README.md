# Monitorizacion de SecureWeb (EV3)

Este servicio ejecuta `app_secure.py` (la aplicacion corregida), sin exponer la variante vulnerable `app.py`.

## Preparacion

Desde la raiz del repositorio, en Docker Desktop:

```cmd
docker build -f monitor/Dockerfile -t secureweb-ea3-monitor:ev3 .
docker run -d --name secureweb-monitor-ea3 --network ea3-net --memory=192m -p 127.0.0.1:5005:5000 secureweb-ea3-monitor:ev3
```

Probar `http://localhost:5005/hello?name=TEST`, `http://localhost:5005/health` y `http://localhost:5005/metrics`.

Para configurar Prometheus existente, copiar el archivo y reiniciar:

```cmd
docker cp monitor/prometheus.yml prometheus-ea3:/etc/prometheus/prometheus.yml
docker restart prometheus-ea3
```

En `http://localhost:9090/targets`, el job `secureweb-flask` debe figurar en estado UP.

En Grafana, con la fuente Prometheus (`http://prometheus-ea3:9090`), consultar:

- `up{job="secureweb-flask"}`
- `sum(secureweb_http_requests_total{endpoint="/hello"})`
- `sum(rate(secureweb_http_requests_total{endpoint="/hello"}[1m]))`

## Evidencias

1. `http://localhost:5005/metrics` con `secureweb_http_requests_total`.
2. Targets de Prometheus con `secureweb-flask` en UP.
3. Panel Grafana con metricas de Flask.

Este entorno es de laboratorio local, no un servicio de produccion publico.
