FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN pip install --no-cache-dir mcp httpx mcp-proxy

COPY server.py .
COPY auth_middleware.py .

EXPOSE 8000

CMD ["python", "server.py"]
