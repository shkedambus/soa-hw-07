FROM python:3.12-slim

WORKDIR /load

COPY load/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY load/locustfile.py locustfile.py

CMD ["sh", "-c", "locust -f locustfile.py --host ${TARGET_HOST:-http://booking-service:8080} --headless -u 10 -r 10 -t 30s --only-summary --csv=/artifacts/load --csv-full-history"]
