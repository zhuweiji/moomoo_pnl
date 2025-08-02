# Use Python 3.11 on Ubuntu as base image
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/
COPY moomoo_OpenD_8.6.4608_Ubuntu16.04/ moomoo_OpenD/

# Make the OpenD executable runnable
RUN chmod +x /app/moomoo_OpenD/moomoo_OpenD_8.6.4608_Ubuntu16.04/OpenD

# Install Python dependencies
RUN pip install --no-cache-dir ".[all]"

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port your FastAPI app runs on
EXPOSE 14231

# Start both OpenD and the FastAPI application
CMD ["sh", "-c", "python src/main.py"]