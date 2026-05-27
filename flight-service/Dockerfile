FROM python:3.12-slim

WORKDIR /app

COPY flight-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY proto proto
COPY flight-service/app app
COPY flight-service/tests tests

RUN python -m grpc_tools.protoc \
      -Iproto \
      --python_out=. \
      --grpc_python_out=. \
      proto/flight.proto

ENV PYTHONPATH=/app

CMD ["python", "-m", "app.server"]
