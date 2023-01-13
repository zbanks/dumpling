FROM python:3.10-slim-bullseye
RUN pip install poetry==1.3.1

WORKDIR app
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-dev --no-root

COPY static /app/static
COPY dumpling.py /app/
ENTRYPOINT ["poetry", "run", "gunicorn", "dumpling:app"]
