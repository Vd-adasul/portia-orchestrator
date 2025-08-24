# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# This command will run inside the container during the build
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code into the container at /app
COPY . .


