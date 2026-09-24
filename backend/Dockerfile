FROM python:3.12.14-slim-bookworm AS builder
WORKDIR /build
# Only pyproject.toml is copied here, so this layer is rebuilt when dependencies change, not on every source edit.
COPY pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > requirements.txt \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.14-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Pick up Debian security fixes published after the base image was built (Trivy gates on HIGH/CRITICAL with a fix).
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=builder /install /usr/local
COPY alembic.ini entrypoint.sh ./
COPY alembic ./alembic
COPY app ./app
RUN chmod +x entrypoint.sh
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
