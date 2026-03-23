FROM python:3.12-slim AS base
RUN pip install --no-cache-dir ruff==0.8.6
RUN useradd --create-home --shell /bin/false sandbox
USER sandbox
WORKDIR /home/sandbox
COPY --chown=sandbox:sandbox run_eval.py /home/sandbox/run_eval.py
ENTRYPOINT ["python3", "/home/sandbox/run_eval.py"]
