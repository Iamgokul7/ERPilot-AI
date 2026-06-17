# Use official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of the application code
COPY . .

# Expose port 5000
EXPOSE 5000

# Run database.py to initialize tables if they don't exist, then start gunicorn
CMD python database.py && gunicorn --bind 0.0.0.0:$PORT app:app
