# MIDE Engine - local image. No data leaves the container; mount your data read-only.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MIDE_HOME=/data/mide

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY mide ./mide
COPY scripts ./scripts
RUN pip install ".[ui]" && mkdir -p /data/mide /workspace

# Usage (demo):  docker run --rm -v mide-data:/data/mide mide-engine demo
# Your data:     docker run --rm -v /path/to/data:/workspace/data:ro -v mide-data:/data/mide mide-engine scan
COPY scripts/docker-entrypoint.sh /usr/local/bin/mide-entrypoint
RUN chmod +x /usr/local/bin/mide-entrypoint
WORKDIR /workspace
VOLUME ["/data/mide"]
EXPOSE 8501
ENTRYPOINT ["mide-entrypoint"]
CMD ["doctor"]
