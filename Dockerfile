# Use an official Python runtime as a parent image
FROM python:3.10

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the poetry.lock and pyproject.toml files
COPY poetry.lock pyproject.toml /app/

# Install poetry
RUN pip install poetry

# Install project dependencies using Poetry
RUN poetry config virtualenvs.create false
RUN    poetry install --no-interaction --no-ansi

# Copy the rest of the application code
COPY . /app/

# Run the application
CMD ["poetry", "run", "python", "main.py"]
