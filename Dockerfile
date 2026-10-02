# GrantPilot backend image.
#
# Containerises the FastAPI API and the artifacts the pipeline needs at runtime
# (the trained models and the Chroma vector index). It does NOT contain Ollama:
# the LLM lives outside this image, and /assess reaches it via the OLLAMA_URL
# environment variable. The deterministic endpoints (eligibility, budget, risk,
# search) work with no LLM at all.
#
# Build and run locally (from the repo root):
#   docker build -t grantpilot-api .
#   docker run -p 8000:8000 -e OLLAMA_URL=http://host.docker.internal:11434/api/generate grantpilot-api
# Then open http://localhost:8000/docs
#
# host.docker.internal lets the container reach Ollama running on the host
# machine. On Linux hosts, add --add-host=host.docker.internal:host-gateway.

FROM python:3.11-slim

WORKDIR /app

# build-essential covers the few packages without prebuilt wheels on slim.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install deps first so this layer caches unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code plus the runtime artifacts. data/raw (the big CSVs) is excluded via
# .dockerignore; the pipeline needs only the models and the Chroma index.
COPY src/ ./src/
COPY backend/ ./backend/
COPY models/ ./models/
COPY data/chroma/ ./data/chroma/

ENV PYTHONUNBUFFERED=1
# Default assumes Ollama on the host; override at run time or in deploy config.
ENV OLLAMA_URL=http://host.docker.internal:11434/api/generate
ENV OLLAMA_MODEL=qwen2.5:3b

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
