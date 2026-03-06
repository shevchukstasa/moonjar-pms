FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY business/ ./business/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
