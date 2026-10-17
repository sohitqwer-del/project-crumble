FROM python:3.12-slim
ARG EXTRAS=""
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HF_HOME=/models
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY crumble ./crumble
RUN pip install --no-cache-dir ".${EXTRAS:+[$EXTRAS]}" \
    && useradd --create-home --uid 10001 crumble \
    && mkdir -p /data /models \
    && chown -R crumble:crumble /data /models
USER crumble
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=4)"
CMD ["crumble", "--workspace", "/data", "serve", "--host", "0.0.0.0"]
