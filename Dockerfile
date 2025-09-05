FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables for USD
ENV PATH="/app/usdzconvert:${PATH}"
ENV PYTHONPATH="/app/USD/lib/python:${PYTHONPATH}"

# Create a volume mount point for input/output files
VOLUME ["/data"]

# Default working directory for conversions
WORKDIR /data

# Make the unified tool executable
RUN chmod +x /app/usd_tool.py

# Set the entrypoint to the unified tool
ENTRYPOINT ["python3", "/app/usd_tool.py"]

# Default command shows help
CMD ["--help"]