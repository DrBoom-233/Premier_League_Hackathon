FROM node:24-bookworm-slim AS frontend
WORKDIR /web
COPY src/frontend/package*.json ./
RUN npm ci
COPY src/frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY src/backend/ src/backend/
COPY src/__init__.py src/__init__.py
COPY scripts/animation/motion.py scripts/animation/run_vlm.py scripts/animation/
COPY data/daily_records.csv data/injury_history.csv data/scenario_mapping.json data/
COPY data/animation/runtime/ data/animation/runtime/
COPY data/demo/runtime/ data/demo/runtime/
COPY --from=frontend /web/dist/ src/frontend/dist/
RUN useradd --create-home app && chown -R app:app /app
USER app
ENV PYTHONUNBUFFERED=1 PITCHGUARD_LOCAL_ONLY=false
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
