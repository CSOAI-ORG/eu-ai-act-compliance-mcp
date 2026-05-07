FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/shared:$PYTHONPATH

RUN pip install --no-cache-dir mcp httpx

COPY shared/ ./shared/
COPY server.py .

EXPOSE 8000

CMD ["python", "server.py"]
