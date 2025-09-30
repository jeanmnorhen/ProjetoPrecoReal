# services/servico_agentes_ia/Dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico_agentes_ia

# Install system dependencies required for confluent-kafka
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    librdkafka-dev \
    gcc \
    apt-transport-https \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8004

CMD ["python", "api/index.py"]
