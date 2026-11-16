FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./
RUN uv pip install --system -e ".[dev]"
ENV PYTHONPATH=/app/src
EXPOSE 8080
