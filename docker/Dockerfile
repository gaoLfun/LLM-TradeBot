FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (exclude docker and docs in build context)
COPY . .

# Create necessary directories
RUN mkdir -p data logs models data/kline data/live data/analytics data/execution data/agents data/risk

# Expose port
EXPOSE 8000

# Health check using curl (always available)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/info || exit 1

# Default command - continuous mode
CMD ["python", "main.py", "--mode", "continuous"]
