FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app_secure.py ./

EXPOSE 5000

CMD ["flask", "--app", "app_secure", "run", "--host=0.0.0.0", "--port=5000", "--no-reload"]
