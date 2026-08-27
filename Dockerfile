FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Install dependencies first so this layer is cached when only app code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev

# Playwright needs its browser binary plus OS-level libraries to render PDF reports.
RUN uv run playwright install --with-deps chromium

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m app.main"]
