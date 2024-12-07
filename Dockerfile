FROM python:3.9-slim

WORKDIR /app

# Copy only the requirements file first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

ENV PYTHONPATH=/app

# Set the default command to run the application
CMD ["python", "app/main.py"]
