FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# poppler-utils is needed for pdf2image if used by document processor
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
