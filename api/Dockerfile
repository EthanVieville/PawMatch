FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# Install CPU-only torch first — avoids pulling multi-GB CUDA libraries (no GPU on EC2)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model to avoid cold start latency on first request
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
