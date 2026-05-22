FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# Install CPU-only torch + torchvision — must be in one step so pip doesn't re-resolve
# torch from PyPI (default index = GPU build, pulls ~2 GB of CUDA libs)
RUN pip install --no-cache-dir torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model to avoid cold start latency on first request
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
