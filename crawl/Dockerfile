FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/huggingface \
    PYTHONPATH=/app

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY scripts ./scripts
COPY src ./src
COPY data/raw ./data/raw

RUN pip install --no-cache-dir .[payments] \
    && python scripts/ingest_domain.py traffic \
    && python scripts/ingest_domain.py labor \
    && python scripts/ingest_domain.py accounting

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
