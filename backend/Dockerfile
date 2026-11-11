FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN pip install --no-cache-dir -e ".[dev]" || pip install --no-cache-dir -e .
ENV PYTHONPATH=/app:/app/src
WORKDIR /app
CMD ["uvicorn", "src.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]