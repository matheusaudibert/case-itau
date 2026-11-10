FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN mkdir -p data

EXPOSE 8000

# A API fica atrás do Nginx do frontend, em /api (por isso o --root-path).
CMD ["uvicorn", "estoque.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/api", "--proxy-headers", "--forwarded-allow-ips", "*"]
