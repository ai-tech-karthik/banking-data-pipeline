# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for DuckDB and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/
COPY dbt_project/ ./dbt_project/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create directories for data and ensure proper permissions
RUN mkdir -p /app/data/inputs /app/data/outputs /app/data/duckdb && \
    chmod -R 777 /app/data

# Expose Dagster webserver port
EXPOSE 3000

# Set environment variables
ENV DAGSTER_HOME=/app/dagster_home
ENV PYTHONUNBUFFERED=1

# Create Dagster home directory
RUN mkdir -p $DAGSTER_HOME

# Health check for the container
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import dagster; print('healthy')" || exit 1

# Default command (will be overridden in docker-compose)
CMD ["dagster", "dev", "-h", "0.0.0.0", "-p", "3000"]
