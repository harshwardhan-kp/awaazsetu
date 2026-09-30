FROM node:22-alpine AS web
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY backend/ backend/
COPY data/ data/
COPY --from=web /app/frontend/dist frontend/dist
RUN mkdir -p /home/awaazsetu && useradd --uid 10001 --create-home appuser && chown -R appuser /app /home/awaazsetu
USER appuser
ENV DATABASE_URL=sqlite:////home/awaazsetu/awaazsetu.db
EXPOSE 8000
CMD ["python","-m","uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000","--no-access-log"]
