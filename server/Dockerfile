# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r calendar && useradd -r -g calendar calendar

# Install runtime dependencies and fonts
RUN apt-get update && apt-get install -y \
    imagemagick \
    fonts-dejavu \
    fonts-liberation \
    fonts-noto \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/calendar/.local

# Create necessary directories
RUN mkdir -p /app/output /app/credentials /app/assets \
    && chown -R calendar:calendar /app

# Copy application code
COPY --chown=calendar:calendar *.py ./
COPY --chown=calendar:calendar assets/ ./assets/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/home/calendar/.local/bin:$PATH

# Font environment variables for the container
ENV FONT_REGULAR=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
ENV FONT_BOLD=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf

# Switch to non-root user
USER calendar

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/status || exit 1

# Default command
CMD ["python", "web_server.py"]