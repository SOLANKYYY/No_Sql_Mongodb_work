# Reuses the mongo:7.0 layers already used in Exercise 13.
FROM mongo:7.0
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/labenv
ENV PATH="/opt/labenv/bin:${PATH}" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /kit
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ scripts/
COPY tests/ tests/
COPY docs/ docs/
COPY results/ results/
COPY *.ps1 *.yml README.md Dockerfile .dockerignore .gitignore ./
ENTRYPOINT ["python", "scripts/main.py"]
CMD ["--help"]
