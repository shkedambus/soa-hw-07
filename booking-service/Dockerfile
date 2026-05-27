FROM python:3.12-slim

WORKDIR /app

COPY booking-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY proto proto
COPY booking-service/app app
COPY booking-service/tests tests

RUN python -m grpc_tools.protoc \
      -Iproto \
      --python_out=. \
      --grpc_python_out=. \
      proto/flight.proto

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
