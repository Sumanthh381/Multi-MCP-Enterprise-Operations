# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV ENTERPRISE_ROOT=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.lock pyproject.toml ./
RUN --mount=type=bind,source=.,target=/context \
    if [ -d /context/.build-wheels ]; then pip install --no-index --find-links=/context/.build-wheels -r requirements.lock; else pip install -r requirements.lock; fi
COPY --chown=10001:10001 src ./src
RUN pip install --no-deps --no-build-isolation . && useradd --create-home --uid 10001 copilot && mkdir /app/.runtime && chown copilot:copilot /app/.runtime
COPY --chown=10001:10001 apps ./apps
COPY --chown=10001:10001 rag ./rag
USER copilot
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "enterprise.backend:app", "--host", "0.0.0.0", "--port", "8080"]
