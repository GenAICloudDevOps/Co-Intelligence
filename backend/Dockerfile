FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PIP_PREFER_BINARY=1
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TINKER_BASE_PATH=/app

# Install tinker and tinker-cookbook without heavy deps (torch), relying on minimal deps from requirements
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps tinker==0.7.0 tinker-cookbook==0.1.0

ENV PYTHONUNBUFFERED=1

CMD uvicorn main:app --host 0.0.0.0 --port 8000
