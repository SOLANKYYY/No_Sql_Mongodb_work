FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/cache/huggingface FASTEMBED_CACHE_PATH=/cache/fastembed OMP_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false
WORKDIR /kit
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip --isolated install --no-cache-dir --timeout 120 --retries 10 --index-url https://pypi.org/simple -v -r requirements.txt
COPY scripts scripts
COPY tests tests
COPY docs docs
COPY data data
COPY results results
COPY *.ps1 *.yml README.md Dockerfile ./
ENTRYPOINT ["python","scripts/main.py"]
CMD ["test"]
