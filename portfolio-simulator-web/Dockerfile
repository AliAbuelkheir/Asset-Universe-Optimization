FROM node:22-bookworm-slim AS client-build

WORKDIR /app

COPY package.json package-lock.json ./
COPY client/package.json client/package.json
RUN npm ci

COPY client client
RUN npm run build

FROM python:3.12-slim

ENV ENVIRONMENT=production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY ml-service/requirements.txt ml-service/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r ml-service/requirements.txt

COPY ml-service ml-service
COPY model-artifacts model-artifacts
COPY --from=client-build /app/client/dist client/dist

CMD ["sh", "-c", "uvicorn app.main:app --app-dir ml-service --host 0.0.0.0 --port ${PORT:-8000}"]
