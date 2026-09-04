# MRPL Agentic Workbench
# Build: docker build -t mrpl-workbench .
# Run:   docker compose up

FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create data directories
RUN mkdir -p data/sample_docs data/audit_logs

# Generate sample data
RUN python scripts/generate_sample_data.py

# Expose ports
EXPOSE 8000 8501

# Start both FastAPI + Streamlit
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8000 & streamlit run ui/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true"]
