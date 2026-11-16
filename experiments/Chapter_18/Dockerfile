FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /kit
COPY requirements.txt .
RUN python -m pip --isolated install --no-cache-dir --timeout 120 --retries 10 --index-url https://pypi.org/simple -r requirements.txt
COPY scripts scripts
COPY tests tests
COPY docs docs
COPY data data
COPY results results
COPY *.ps1 *.yml README.md Dockerfile ./
ENTRYPOINT ["python","scripts/main.py"]
CMD ["test"]
