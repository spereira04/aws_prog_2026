FROM python:3.11-slim

WORKDIR /app

# Ensure logs are flushed immediately to stdout/stderr
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY simulator.py .

# Simply execute the script. Once the script finishes, Fargate destroys the container.
CMD ["python", "simulator.py"]
