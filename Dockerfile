# Use an official Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt ./
RUN pip install --upgrade pip

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your entire project
COPY . .

# Avoid Python output buffering issues
ENV PYTHONUNBUFFERED=1

# Start your Discord bot using main.py
CMD ["python", "main.py"]