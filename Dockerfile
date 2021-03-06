FROM python:3.7-slim-bullseye
RUN pip install poetry==1.1.12

WORKDIR app
COPY poetry.lock pyproject.toml /app/
RUN poetry install --no-dev --no-root

COPY static /app/static
COPY dumpling.py /app/
ENTRYPOINT ["poetry", "run", "gunicorn", "dumpling:app"]
