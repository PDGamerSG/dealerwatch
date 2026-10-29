FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DW_DATA=/data/generated DW_RUNTIME=/data/runtime
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
    && groupadd --gid 10001 dealerwatch \
    && useradd --uid 10001 --gid 10001 --create-home dealerwatch \
    && mkdir /data && chown dealerwatch:dealerwatch /data
COPY --chown=dealerwatch:dealerwatch dealerwatch ./dealerwatch
COPY --chown=dealerwatch:dealerwatch toolkit ./toolkit
COPY --chown=dealerwatch:dealerwatch data/reference ./data/reference
USER dealerwatch
EXPOSE 8077
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8077/api/ready', timeout=4)"
CMD ["python", "-m", "dealerwatch", "--host", "0.0.0.0", "--port", "8077"]
