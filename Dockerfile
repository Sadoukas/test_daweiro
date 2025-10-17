# Use official Playwright image as base
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config.env.example .env

# Create directories for data and logs
RUN mkdir -p data logs

# Set environment variables
ENV PYTHONPATH=/app

# Default command
CMD ["python", "src/scraper.py"]
