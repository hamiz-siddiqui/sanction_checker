# Use an official minimal Python image
FROM python:3.11.9

# Install OS-level dependencies (Tesseract and friends)
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory to backend/
WORKDIR /app

# Copy only the backend code
COPY backend/ /app

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Expose port
EXPOSE 8000

# Run the FastAPI app (assumes `api.py` has `
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]