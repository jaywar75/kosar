FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN pip install --upgrade pip && pip install poetry
RUN poetry install --no-root
COPY . /app
CMD ["poetry", "run", "python", "run.py"]