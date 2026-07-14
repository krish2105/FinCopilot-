FROM python:3.11-slim

# System deps for lxml/psycopg and sentence-transformers runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the int8 cross-encoder into the image so a cold start never pays to download
# it (Render's disk is ephemeral, so a runtime download would repeat on every wake).
RUN python -c "\
from huggingface_hub import hf_hub_download; \
hf_hub_download('Xenova/ms-marco-MiniLM-L-6-v2', 'onnx/model_quantized.onnx'); \
hf_hub_download('Xenova/ms-marco-MiniLM-L-6-v2', 'tokenizer.json'); \
print('reranker cached')"

# App source
COPY . .

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
