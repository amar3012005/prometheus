FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    dnsutils \
    curl \
    git \
    lsb-release \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_23.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install ElevenLabs CLI via NPM (Conversational AI CLI)
RUN npm install -g elevenlabs

# Copy requirements and install Python dependencies
COPY requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --timeout=300 --retries=10 -r requirements.txt

# Python dependencies already include elevenlabs library

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/vault /app/davinci-agent-chart

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8099
ENV VAULT_BASE_PATH=/app/vault
ENV HELM_CHART_PATH=/app/davinci-agent-chart

# Expose port
EXPOSE 8099

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]
