# Pin to a specific digest for supply chain security before production deployment.
# Retrieve digest: docker pull python:3.12-slim && docker inspect --format='{{index .RepoDigests 0}}' python:3.12-slim
# Then use: FROM python:3.12-slim@sha256:<digest>
FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=60s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=4)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
