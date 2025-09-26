# services/servico-monitoramento/Dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico-monitoramento

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8003

CMD ["python", "api/index.py"]
