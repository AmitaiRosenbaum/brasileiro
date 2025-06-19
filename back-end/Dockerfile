FROM python:3

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

# Install Poetry package management
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

ENV POETRY_VIRTUALENVS_CREATE=false


# # Virtual environment (not strictly necessary)
# RUN python -m venv .venv
# ENV PATH='.venv/bin:$PATH'
# ENV PATH="/usr/src/app/.venv/bin:$PATH"


RUN ["poetry", "--version"]

COPY pyproject.toml poetry.lock ./

# Install packages 
RUN ["poetry", "install"]

COPY . .

RUN ["python", "songAPI/manage.py", "migrate"]
RUN ["python", "songAPI/manage.py", "makemigrations"]

EXPOSE 8000

CMD ["python", "songAPI/manage.py", "runserver", "0.0.0.0:8000"]