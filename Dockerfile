# Use Python 3.10 as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/output

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port for API
EXPOSE 8000

# Command to run the application
# Use environment variable to determine the mode
ENV APP_MODE=api
CMD if [ "$APP_MODE" = "api" ]; then \
        python main.py --api; \
    elif [ "$APP_MODE" = "analyze" ]; then \
        python main.py --analyze; \
    elif [ "$APP_MODE" = "periodic" ]; then \
        python main.py --periodic --interval ${UPDATE_INTERVAL:-3600}; \
    else \
        echo "Invalid APP_MODE. Use 'api', 'analyze', or 'periodic'"; \
        exit 1; \
    fi