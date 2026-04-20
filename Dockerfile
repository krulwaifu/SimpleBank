FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-interaction --no-ansi --no-root

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
