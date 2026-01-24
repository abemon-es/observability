FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Default port
ENV PORT=9090
ENV SCRAPE_INTERVAL=60

EXPOSE 9090

CMD ["python", "main.py"]
