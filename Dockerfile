FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install locked dependencies first so this layer is cached between code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY server.py ./
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "server.py"]
