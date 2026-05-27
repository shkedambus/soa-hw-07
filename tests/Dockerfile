FROM python:3.12-slim

WORKDIR /workspace

COPY tests/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY tests tests
COPY scripts scripts

CMD ["pytest", "-q", "tests"]
