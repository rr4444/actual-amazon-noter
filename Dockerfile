FROM python:3.11-alpine

WORKDIR /app

# Install build dependencies if needed, then copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Ensure the python script is executable
RUN chmod +x actual-amazon-noter

EXPOSE 8080

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-w", "2", "-t", "300", "-b", "0.0.0.0:8080", "app:app"]
