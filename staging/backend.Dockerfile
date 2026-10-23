# syntax=docker/dockerfile:1
FROM python:3.12.13-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOME=/var/lib/japanxtheworld
ENV OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 NUMEXPR_NUM_THREADS=4
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home app
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/config/*.py /app/backend/config/
COPY backend/controllers/*.py /app/backend/controllers/
COPY backend/middleware/*.py /app/backend/middleware/
COPY backend/models/*.py /app/backend/models/
COPY backend/models/management/*.py /app/backend/models/management/
COPY backend/models/management/commands/*.py /app/backend/models/management/commands/
COPY backend/models/migrations/*.py /app/backend/models/migrations/
COPY backend/routes/*.py /app/backend/routes/
COPY backend/security/*.py /app/backend/security/
COPY backend/services/*.py /app/backend/services/
COPY backend/services/ai/*.py /app/backend/services/ai/
COPY backend/services/classification/*.py /app/backend/services/classification/
COPY backend/services/documentAnalysis/*.py /app/backend/services/documentAnalysis/
COPY backend/services/documentAnalysis/fields/*.py /app/backend/services/documentAnalysis/fields/
COPY backend/services/ocr/*.py /app/backend/services/ocr/
COPY backend/services/trustedContent/*.py /app/backend/services/trustedContent/
COPY backend/manage.py /app/backend/manage.py
COPY backend/staging_tools/*.py /app/backend/staging_tools/
COPY deploy/gunicorn.conf.py /app/deploy/gunicorn.conf.py
USER 10001:10001
ENTRYPOINT ["python", "/app/backend/staging_tools/entrypoint.py"]
CMD ["serve"]

FROM runtime AS model-setup
USER root
RUN python -m pip install --no-cache-dir huggingface-hub==2.2.0
COPY backend/download_ocr_models.py /app/backend/download_ocr_models.py
USER 10001:10001
ENTRYPOINT ["python", "/app/backend/download_ocr_models.py"]
CMD ["--size", "medium", "--root", "/opt/models"]

FROM runtime AS qa
USER root
RUN apt-get update && apt-get install -y --no-install-recommends fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements-dev.txt /app/backend/requirements-dev.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements-dev.txt
COPY backend/tests/*.py /app/backend/tests/
COPY backend/evaluation/*.py /app/backend/evaluation/
COPY backend/check_production_local.py /app/backend/check_production_local.py
USER 10001:10001
