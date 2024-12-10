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
FROM node:23.3-slim AS webbuilder

# Install curl for downloading the webapp from GH and unzip to extract it
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    unzip\
    ca-certificates

WORKDIR /usr/src/

# Get the latest commit sha as a build arg
# This is needed otherwise Docker will cache the git clone step. With this workaround
# we can force Docker to re-run the git clone step if the latest commit sha changes.
# --build-arg LATEST_COMMIT_SHA=$(curl \
#     -LSsk "https://api.github.com/repos/stacklok/codegate-ui/commits?per_page=1" \
#     -H "Authorization: Bearer $GH_CI_TOKEN" | jq -r '.[0].sha')
ARG LATEST_COMMIT_SHA=LATEST
RUN echo "Latest FE commit: $LATEST_COMMIT_SHA"
# Download the webapp from GH
# -L to follow redirects
RUN --mount=type=secret,id=gh_token \
    LATEST_COMMIT_SHA=${LATEST_COMMIT_SHA} \
    curl -L -o main.zip "https://api.github.com/repos/stacklok/codegate-ui/zipball/main" \
    -H "Authorization: Bearer $(cat /run/secrets/gh_token)"

# Extract the downloaded zip file
RUN unzip main.zip
RUN rm main.zip
# Rename the extracted folder
RUN mv *codegate-ui* webapp

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

# Create a non-root user
RUN useradd -m -u 1000 -r codegate

# Copy backup if needed
RUN mkdir -p /tmp/weaviate_backup
# will not fail if the file does not exist
COPY weaviate_backu[p] /tmp/weaviate_backup
RUN chown -R codegate /tmp/weaviate_backup

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

# Expose additional env vars
ENV CODEGATE_VLLM_URL=https://inference.codegate.ai
ENV CODEGATE_OPENAI_URL=
ENV CODEGATE_ANTHROPIC_URL=
ENV CODEGATE_OLLAMA_URL=
ENV CODEGATE_APP_LOG_LEVEL=WARNING
ENV CODEGATE_LOG_FORMAT=TEXT

# Set the container's default entrypoint
EXPOSE 8989
ENTRYPOINT ["/app/scripts/entrypoint.sh"]