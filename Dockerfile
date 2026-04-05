# --- Stage 1: Builder ---
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Build Python wheels to a specialized directory
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt


# --- Stage 2: Runner ---
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

WORKDIR /app

# Create a non-root system user for security
RUN addgroup --system kisangroup && adduser --system --group kisanuser

# Install limited runtime dependencies (only what's needed for libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder stage and install them
COPY --from=builder /app/wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir /wheels/*

# Copy the application code
COPY . .

# Adjust permissions for the non-root user
RUN chown -R kisanuser:kisangroup /app

# Switch to the non-root user
USER kisanuser

# Expose port (metadata)
EXPOSE 8000

# Healthcheck to monitor app availability
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1

# Launch the app
CMD ["python", "main.py"]
