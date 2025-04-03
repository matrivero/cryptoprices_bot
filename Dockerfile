FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install poetry==2.1.2

WORKDIR /app

COPY pyproject.toml poetry.lock ./
COPY src ./src

# Install Python dependencies using Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Set the default command to run your application
CMD ["poetry", "run", "python", "src/bot.py"]