FROM python:3.12-slim

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    wget \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
COPY requirements.in .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for pgvector
RUN pip install --no-cache-dir psycopg2-binary pgvector

# Install Playwright
RUN pip install --no-cache-dir playwright
RUN playwright install --with-deps chromium

# Copy package.json and install Node.js dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy TypeScript config and compile MCP server
COPY tsconfig.json ./
COPY mcp_servers/ ./mcp_servers/
RUN npm run build

# Copy application code
COPY . .

# Create storage and scraped content directories
RUN mkdir -p /app/storage /app/scraped_content

# Expose port for potential web interface
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "src/rag_system_pgvector.py", "stats"]
