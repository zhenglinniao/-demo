FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

ENV DATABASE_URL=sqlite:///./app.db
ENV JWT_SECRET=dev_secret_change_me
ENV JWT_EXPIRES_MINUTES=120
ENV AI_FAIL_RATE=0.1
ENV AI_MAX_RETRIES=2
ENV AI_REPLY_STRATEGY=all
ENV SEED_USERS=

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
