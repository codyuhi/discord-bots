FROM python:3.12-slim

# Install the timezone database
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY poll.py /app/poll.py

# Ensure logs are flushed immediately to stdout
ENV PYTHONUNBUFFERED=1

CMD ["python", "poll.py"]