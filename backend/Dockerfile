# syntax=docker/dockerfile:1
# Production image for the GDG TUM Build Arena API.
#
# Build (from the repository root):
#   docker build -t build-arena-api ./backend
# Run (migrations + server; DATABASE_URL must point at PostgreSQL):
#   docker run --rm -p 8000:8000 -e DATABASE_URL=... build-arena-api

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# Copy only project metadata first so the dependency layer is cached across code changes.
COPY pyproject.toml README.md ./
RUN python -c "import pathlib, tomllib; project = tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']; pathlib.Path('/tmp/requirements.txt').write_text('\n'.join(project['dependencies']) + '\n')"
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install the application itself (no dependency resolution needed anymore).
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps .

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# Migrations are intentionally NOT run here; run them as a release/init step
# (see docker-compose.yml for the local-development pattern).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
