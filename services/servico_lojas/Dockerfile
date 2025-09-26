FROM python:3.9-slim-bullseye

WORKDIR /app/services/servico_lojas

COPY . /app/services/servico_lojas

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8005

CMD ["python", "api/index.py"]
