# services/servico-busca/Dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico-busca

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["python", "api/index.py"]
