# services/servico-agentes-ia/Dockerfile
# Use a full python image to have build tools available
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies for llama-cpp-python compilation and others
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements to leverage Docker cache
COPY services/servico-agentes-ia/requirements.txt .

# Set build-time environment variables for llama-cpp-python
# This forces compilation with OpenBLAS for AVX2 acceleration
ENV FORCE_CMAKE=1
ENV CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"

# Install python dependencies, forcing llama-cpp-python to be rebuilt
RUN pip install --no-cache-dir -r requirements.txt --force-reinstall --no-binary :all: llama-cpp-python

# Create a directory for the models and download them
RUN mkdir -p /app/models
RUN wget -O /app/models/bakllava-1-7b.Q4_K_M.gguf https://huggingface.co/TheBloke/BakLLaVA-1-7B-GGUF/resolve/main/bakllava-1-7b.Q4_K_M.gguf
RUN wget -O /app/models/mmproj-model-f16.gguf https://huggingface.co/TheBloke/BakLLaVA-1-7B-GGUF/resolve/main/mmproj-model-f16.gguf

# Copy the rest of the application code
COPY . .

# Set the working directory for the service
WORKDIR /app/services/servico-agentes-ia

EXPOSE 8004

# Command to run the FastAPI application using uvicorn and the Celery worker.
# For production, it's recommended to run the web server and worker in separate containers.
CMD ["sh", "-c", "celery -A api.celery_worker worker --loglevel=info & uvicorn api.main:app --host 0.0.0.0 --port 8004"]