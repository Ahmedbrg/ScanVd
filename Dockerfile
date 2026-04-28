FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies (ffmpeg is required for Whisper, libgl1 for OpenCV/YOLO)
RUN apt-get update && \
    apt-get install -y ffmpeg libgl1 libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create the uploads directory and give permissions
RUN mkdir -p backend/uploads && chmod 777 backend/uploads

# Expose the port (Hugging Face Spaces uses 7860 by default)
EXPOSE 7860

# Start the application
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
