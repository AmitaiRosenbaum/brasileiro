FROM python:3

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PATH="/usr/src/app/.venv/bin:$PATH"

WORKDIR /usr/src/app
RUN ["mkdir", "songAPI"]

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

# Install packages 
RUN ["uv", "sync", "--locked", "--no-dev"]

COPY ./entrypoint.sh ./songAPI
COPY ./songAPI ./songAPI
WORKDIR ./songAPI

RUN chmod +x ./entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
