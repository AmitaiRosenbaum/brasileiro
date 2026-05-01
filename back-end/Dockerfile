FROM python:3.14-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/usr/src/app/.venv/bin:$PATH"

# For Postgres
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
RUN ["mkdir", "songAPI"]

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

# Install packages 
RUN ["uv", "sync", "--locked", "--no-dev"]

COPY ./entrypoint.sh ./songAPI
COPY ./songAPI ./songAPI
WORKDIR /usr/src/app/songAPI

RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
