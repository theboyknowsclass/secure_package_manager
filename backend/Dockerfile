FROM python:3.11-slim

WORKDIR /app

# Install system dependencies, Trivy, Node.js and npm
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    lsb-release \
    gnupg \
    && rm -rf /var/lib/apt/lists/* \
    && wget -qO- https://github.com/aquasecurity/trivy/releases/download/v0.50.2/trivy_0.50.2_Linux-64bit.tar.gz | tar -xz -C /usr/local/bin trivy \
    && chmod +x /usr/local/bin/trivy \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && && apt-get install -y nodejs

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create package cache directory
RUN mkdir -p /app/package_cache

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
