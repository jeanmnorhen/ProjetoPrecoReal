# services/servico-usuarios/Dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico-usuarios

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["python", "api/index.py"]
