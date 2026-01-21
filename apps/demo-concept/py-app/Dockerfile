# Dockerfile for local minikube development
FROM python:3.13-slim

WORKDIR /app

# Copy application code
COPY src/ /app/

# Install dependencies if needed
# COPY pyproject.toml uv.lock ./
# RUN pip install uv && uv sync

# Run the application
CMD ["python", "main.py"]
