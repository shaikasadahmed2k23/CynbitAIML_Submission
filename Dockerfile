# ---- stage 1: build the React frontend
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: FastAPI serving API + built frontend
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY app ./app
COPY api ./api
COPY data/samples ./data/samples
COPY docs ./docs
COPY eval/results.md ./eval/results.md
COPY --from=web /web/dist ./frontend/dist
# Render injects $PORT; default 8000 for local `docker run`
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port ${PORT}"]
