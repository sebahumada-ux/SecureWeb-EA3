FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY monitor/requirements-monitor.txt /app/requirements-monitor.txt

RUN python -m pip install --no-cache-dir \
    -r /app/requirements.txt \
    -r /app/requirements-monitor.txt

COPY app_secure.py /app/app_secure.py
COPY monitor/monitor_app.py /app/monitor_app.py

EXPOSE 5000

CMD ["python", "monitor_app.py"]
