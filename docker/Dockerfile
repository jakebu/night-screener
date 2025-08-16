# Dockerfile
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install dependencies (assuming requirements.txt is at repo root)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only your app folder into container’s /app
COPY docker/app/ . 

# Expose port and run the app
EXPOSE 8080
CMD ["python", "app.py"]
