FROM python:3.11-slim
WORKDIR /app
COPY requirements-cloud.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY app ./app
COPY policy ./policy
COPY fixtures ./fixtures
COPY scripts ./scripts
ENV PORT=8080 PYTHONUNBUFFERED=1
CMD ["sh","-c","uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
