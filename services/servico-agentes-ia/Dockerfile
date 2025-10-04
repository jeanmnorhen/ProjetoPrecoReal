# services/servico-agentes-ia/Dockerfile
FROM python:3.11-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    wget \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Set build-time environment variables for llama-cpp-python compilation
ENV FORCE_CMAKE=1
ENV CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"

# Install python dependencies, forcing llama-cpp-python to be rebuilt
RUN LDFLAGS="-pthread" pip install --no-cache-dir -r requirements.txt --force-reinstall --no-binary :all: llama-cpp-python

# Create a directory for the models and download them
RUN mkdir -p /app/models
RUN wget -O /app/models/bakllava-1-7b.Q4_K_M.gguf https://huggingface.co/TheBloke/BakLLaVA-1-7B-GGUF/resolve/main/bakllava-1-7b.Q4_K_M.gguf
RUN wget -O /app/models/mmproj-model-f16.gguf https://huggingface.co/TheBloke/BakLLaVA-1-7B-GGUF/resolve/main/mmproj-model-f16.gguf

# Copy the rest of the application code from the build context
COPY . .

EXPOSE 8004

# Command to run the application
# The python path will resolve api.celery_worker and api.main correctly from the /app WORKDIR
CMD ["sh", "-c", "celery -A api.celery_worker worker --loglevel=info & uvicorn api.main:app --host 0.0.0.0 --port 8004"]
