#!/bin/bash
# List of extensions to install
extensions=(
    "continue.continue"
)

for extension in "${extensions[@]}"; do
    echo "Installing $extension..."
    code --install-extension "$extension" --force
done

echo "Continue extension installed successfully!"
echo
echo "Setting up config to use stacklok-hosted model..."
echo
echo "Note: This script will modify the configuration file at $HOME/.continue/config.json."
echo "If you have an existing configuration file, it will be backed up to $HOME/.continue/config.json.bak."
echo "Please make sure to back up your configuration file before running this script."
echo "If this script fails, you can add the following model manually to the configuration file:"
echo
echo '```json'
echo '{
    "title": "stacklok-hosted",
    "provider": "vllm",
    "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
    "apiKey": "key",
    "apiBase": "http://localhost:8989/vllm"
}'
echo '```'
echo

# Path to the configuration file
CONFIG_FILE="$HOME/.continue/config.json"

# New model to add
NEW_MODEL=$(cat <<EOF
{
    "title": "stacklok-hosted",
    "provider": "vllm",
    "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
    "apiKey": "key",
    "apiBase": "http://localhost:8989/vllm"
}
EOF
)

# Update for tabAutocompleteModel
NEW_TAB_AUTOCOMPLETE_MODEL=$(cat <<EOF
{
    "title": "stacklok-hosted",
    "provider": "vllm",
    "model": "Qwen/Qwen2.5-Coder-14B-Instruct",
    "apiKey": ""
}
EOF
)

# Create config directory if it doesn't exist
mkdir -p "$HOME/.continue"

# Ensure the configuration file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Configuration file not found at $CONFIG_FILE. Creating a new configuration file."
    echo '{
        "models": [],
        "modelRoles": {
            "default": "stacklok-hosted"
        }
    }' > "$CONFIG_FILE"
fi

# Backup the configuration file
cp "$CONFIG_FILE" "$CONFIG_FILE.bak"

# Use jq to handle JSON
if command -v jq >/dev/null 2>&1; then
    echo "Using jq for JSON manipulation..."
    
    # Check if the model already exists
    MODEL_EXISTS=$(jq --arg title "stacklok-hosted" '.models[] | select(.title == $title)' "$CONFIG_FILE")
    if [[ -n "$MODEL_EXISTS" ]]; then
        echo "Model 'stacklok-hosted' already exists in the configuration file."
    else
        # Add the model
        jq --argjson newModel "$NEW_MODEL" '.models += [$newModel]' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
        echo "Model added successfully."
    fi

    # Ensure modelRoles exists and set default
    if ! jq -e '.modelRoles' "$CONFIG_FILE" >/dev/null 2>&1; then
        echo "Adding modelRoles section..."
        jq '. + {"modelRoles": {"default": "stacklok-hosted"}}' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    else
        echo "Updating modelRoles default..."
        jq '.modelRoles.default = "stacklok-hosted"' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    fi

    # Update tabAutocompleteModel
    jq --argjson newTabAutoComplete "$NEW_TAB_AUTOCOMPLETE_MODEL" '.tabAutocompleteModel = $newTabAutoComplete' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    echo "Updated tabAutocompleteModel in the configuration."
else
    echo "jq is not installed. Using basic text manipulation..."
    
    # Create a temporary file for modifications
    TEMP_FILE="${CONFIG_FILE}.tmp"
    
    # Read the entire file
    content=$(<"$CONFIG_FILE")
    
    # Check if the model already exists
    if echo "$content" | grep -q '"title": "stacklok-hosted"'; then
        echo "Model 'stacklok-hosted' already exists in the configuration file."
    else
        # Insert the new model into the models array
        content=$(echo "$content" | sed '/"models": \[/a\
        '"$NEW_MODEL"',' )
    fi
    
    # Check if modelRoles exists
    if ! echo "$content" | grep -q '"modelRoles"'; then
        # Add modelRoles section after the models array
        content=$(echo "$content" | sed '/"models": \[/,/\]/!b;/\]/a\
    ,\n    "modelRoles": {\n        "default": "stacklok-hosted"\n    }')
    else
        # Update existing modelRoles
        content=$(echo "$content" | sed -E 's/"default": "[^"]*"/"default": "stacklok-hosted"/')
    fi
    
    # Update tabAutocompleteModel
    if echo "$content" | grep -q '"tabAutocompleteModel"'; then
        content=$(echo "$content" | sed '/"tabAutocompleteModel": {/,/}/c\
    "tabAutocompleteModel": '"$NEW_TAB_AUTOCOMPLETE_MODEL"'')
    else
        # Add tabAutocompleteModel after modelRoles
        content=$(echo "$content" | sed '/"modelRoles": {/,/}/!b;/}/a\
    ,\n    "tabAutocompleteModel": '"$NEW_TAB_AUTOCOMPLETE_MODEL"'')
    fi
    
    # Write the modified content back to the file
    echo "$content" > "$CONFIG_FILE"
    echo "Configuration updated successfully."
fi

echo "Done with configuration setup!"

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "$1 is not installed. Please install it and try again."
        exit 1
    fi
}

# Check if Docker is installed
echo "Checking if Docker is installed..."
check_command "docker"

# Check if Docker Compose is installed (or included in Docker)
echo "Checking if Docker Compose is installed..."
if docker compose version &>/dev/null; then
    # Docker Compose is included in Docker
    COMPOSE_COMMAND="docker compose"
elif command -v docker-compose &>/dev/null; then
    # Legacy Docker Compose is installed
    COMPOSE_COMMAND="docker-compose"
else
    echo "Docker Compose is not installed. Please install it and try again."
    exit 1
fi

echo "Docker and Docker Compose are installed."

# Define the docker-compose file path
COMPOSE_FILE="./docker-compose.yml"

# Create the docker-compose.yml file
echo "Creating docker-compose.yml file..."
cat > "$COMPOSE_FILE" <<EOF
version: "3.9"

services:
  codegate-proxy:
    networks:
      - codegatenet
    build:
      context: .
      dockerfile: docker/Dockerfile
    image: ghcr.io/stacklok/codegate:latest
    ports:
      - 8989:8989
    extra_hosts:
      - "host.docker.internal:host-gateway"
    command:
      - -vllm=https://inference.codegate.ai # For hosted LLM
      - -ollama-embed=http://host.docker.internal:11434
      - -package-index=/opt/rag-in-a-box/data/
      - -db=rag-db
    depends_on:
      - rag-qdrant-db

  rag-qdrant-db:
    image: ghcr.io/stacklok/codegate/qdrant-codegate@sha256:fccd830f8eaf9079972fee1eb95908ffe42d4571609be8bffa32fd26610481f7
    container_name: rag-db
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - codegatenet

networks:
  codegatenet:
    driver: bridge
EOF

echo "docker-compose.yml file created successfully."

# Run docker-compose up
echo "Running docker-compose up -d with file: $COMPOSE_FILE"
$COMPOSE_COMMAND -f "$COMPOSE_FILE" up -d

if [[ $? -eq 0 ]]; then
    echo "Containers started successfully."
    echo
    echo "You can now open Visual Studio Code and start using the Codegate extension."
    echo "If you have any issues, please check the logs of the containers using 'docker logs <container-name>'."
    echo
    echo "Last of all, you will need a key to use the stacklok inference model, please contact stacklok for a key."
    echo "You can add the key to the configuration file at $HOME/.continue/config.json."
    echo "In the apiKey field, replace 'key' with the actual key."
else
    echo "Failed to start containers. Check the output above for errors."
    exit 1
fi
