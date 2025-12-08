FROM python:3.12-slim

WORKDIR /app

RUN pip install --upgrade pip
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PIP_PREFER_BINARY=1
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD uvicorn main:app --host 0.0.0.0 --port 8000
