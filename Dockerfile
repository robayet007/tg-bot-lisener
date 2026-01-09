# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create sessions directory (will be mounted as volume in Fly.io)
RUN mkdir -p /app/sessions && chmod 755 /app/sessions

# Expose port (Fly.io will set PORT env var)
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
