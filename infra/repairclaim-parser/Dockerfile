FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir 'pymupdf>=1.25,<2'
WORKDIR /app
COPY apps/repairclaim-api/src/repairclaim_api /app/repairclaim_api
USER 65534:65534
ENTRYPOINT ["python", "-I", "/app/repairclaim_api/parser_child.py"]
