FROM python:3.12-slim
WORKDIR /kit
COPY requirements.txt .
COPY Dockerfile .dockerignore .gitignore ./
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ scripts/
COPY k8s/ k8s/
COPY terraform/ terraform/
COPY monitoring/ monitoring/
COPY docs/ docs/
COPY results/ results/
COPY *.ps1 *.yml README.md ./
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "/kit/scripts/lab.py"]
CMD ["help"]
