FROM python:3.12-slim

WORKDIR /app

# Install docker CLI (static binary for reliability)
RUN apt-get update && apt-get install -y --no-install-recommends git curl && \
    curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-24.0.7.tgz | tar xz -C /tmp && \
    mv /tmp/docker/docker /usr/local/bin/docker && \
    rm -rf /tmp/docker && \
    chmod +x /usr/local/bin/docker && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --no-deps tinker==0.7.0 tinker-cookbook==0.1.0 && \
    find /usr/local/lib/python3.12/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /usr/local/lib/python3.12/site-packages/torch/test && \
    rm -rf /usr/local/lib/python3.12/site-packages/torch/include && \
    rm -rf /usr/local/lib/python3.12/site-packages/torch/share && \
    rm -rf /root/.cache

COPY . .

RUN if [ -d /app/test-tinker/scripts ]; then \
    find /app/test-tinker/scripts -type f -name "*.sh" -exec sed -i 's/\r$//' {} +; \
  fi

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TINKER_BASE_PATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
