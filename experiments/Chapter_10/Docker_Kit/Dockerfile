FROM python:3.12-slim
WORKDIR /lab
COPY requirements.txt /lab/
RUN pip install --no-cache-dir -r requirements.txt
COPY lab10.py transactions.py report.py test_transactions.py /lab/
COPY compose.yaml Dockerfile Dockerfile.submission .dockerignore requirements.txt README.md IMPLEMENTATION.md start.ps1 run-all.ps1 run-experiments.ps1 make-report.ps1 publish.ps1 demo-published.ps1 run.sh /kit/
COPY lab10.py transactions.py report.py test_transactions.py /kit/
ENV RESULTS_DIR=/results
ENV MPLCONFIGDIR=/tmp/matplotlib
ENTRYPOINT ["python", "-u", "/lab/lab10.py"]
CMD ["--help"]
