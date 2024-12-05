# Builder stage: Install dependencies and build the application
FROM python:3.12-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.8.4 && rm -rf /root/.cache/pip

# Set the working directory
WORKDIR /app
COPY pyproject.toml poetry.lock* /app/

# Configure Poetry and install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev

# Copy the rest of the application
COPY . /app

# Build the webapp
FROM node:20.18-slim AS webbuilder

# Install curl for downloading the webapp from GH and unzip to extract it
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip

WORKDIR /usr/src/

# Download the webapp from GH
# -O to save the file with the same name as the remote file
# -L to follow redirects
# -s to silence the progress bar
# -k to allow curl to make insecure connections
# -H to pass the GITHUB_TOKEN as a header
RUN --mount=type=secret,id=gh_token \
    curl -OLSsk "https://github.com/stacklok/codegate-ui/archive/refs/heads/main.zip" \
    -H "Authorization: Bearer $(cat /run/secrets/gh_token)"

# Extract the downloaded zip file
RUN unzip main.zip
RUN rm main.zip
# Rename the extracted folder
RUN mv codegate-ui-main webapp

WORKDIR /usr/src/webapp

# Install the webapp dependencies and build it
RUN npm install
RUN npm run build

# Runtime stage: Create the final lightweight image
FROM python:3.12-slim AS runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN useradd -m -u 1000 -r codegate 

# Create a non-root user
RUN adduser --system --no-create-home codegate --uid 1000

# Set permissions for user codegate to run nginx
RUN chown -R codegate /var/lib/nginx && \
    chown -R codegate /var/log/nginx && \
    chown -R codegate /run

# Switch to codegate user
USER codegate
WORKDIR /app

# Copy necessary artifacts from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app

# Copy necessary artifacts from the webbuilder stage
COPY --from=webbuilder /usr/src/webapp/dist /var/www/html
# Expose nginx
EXPOSE 80

# Set the PYTHONPATH environment variable
ENV PYTHONPATH=/app/src

# Set the container's default entrypoint
EXPOSE 8989
ENTRYPOINT ["/app/scripts/entrypoint.sh", "/app/weaviate_backup", "backup"]
