# services/servico-healthcheck/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação
COPY . .

# Expor a porta e rodar a aplicação
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
