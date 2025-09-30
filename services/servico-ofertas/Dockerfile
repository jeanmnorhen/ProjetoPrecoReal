# services/servico_ofertas/Dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico_ofertas

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8006

CMD ["python", "api/index.py"]
