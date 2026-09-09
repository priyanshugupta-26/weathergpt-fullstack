FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY models/ models/
COPY --from=frontend /build/dist/client frontend/dist/client
RUN useradd --create-home --uid 10001 weather && mkdir -p data && chown -R weather:weather /app
USER weather
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn","backend.main:app","--host","0.0.0.0","--port","8000"]
