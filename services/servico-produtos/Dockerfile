# services/servico-produtos/Dockerfile
FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico-produtos

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8007

CMD ["python", "api/index.py"]
