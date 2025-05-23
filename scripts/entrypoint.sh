#!/bin/bash

# those are hardcoded on the image, will not change
BACKUP_NAME="backup"
MODEL_BASE_PATH="/app/codegate_volume/models"
CODEGATE_DB_FILE="/app/codegate_volume/db/codegate.db"
CODEGATE_VEC_DB_FILE="/app/sqlite_data/vectordb.db"
CODEGATE_CERTS="/app/codegate_volume/certs"

# Function to restore backup if paths are provided
restore_backup() {
    if [ -n "$BACKUP_PATH" ] && [ -n "$BACKUP_NAME" ]; then
        if [ -d "$BACKUP_PATH" ] && [ -d "$BACKUP_PATH/$BACKUP_NAME" ]; then
            echo "Restoring backup from $BACKUP_PATH/$BACKUP_NAME..."
            python -m src.codegate.cli restore-backup --backup-path "$BACKUP_PATH" --backup-name "$BACKUP_NAME"
        else
            echo "No backup found at $BACKUP_PATH/$BACKUP_NAME. Skipping restore."
        fi
    else
        echo "Backup path or mode not provided. Skipping restore."
    fi
}

generate_certs() {
    echo "Generating certificates..."
    python -m src.codegate.cli generate-certs --certs-out-dir "$CODEGATE_CERTS"
}

# Function to start Nginx server for the dashboard
start_dashboard() {
    echo "Starting the dashboard..."
    
    envsubst '${DASHBOARD_API_BASE_URL}' < /var/www/html/index.html > /var/www/html/index.html.tmp && mv /var/www/html/index.html.tmp /var/www/html/index.html

    nginx -g 'daemon off;' &
}

# Function to start the main application
start_application() {
    # first restore the models
    mkdir -p /app/codegate_volume/models
    cp /app/default_models/* /app/codegate_volume/models
    CMD_ARGS="--port 8989 --host 0.0.0.0 --model-base-path $MODEL_BASE_PATH --db-path $CODEGATE_DB_FILE --vec-db-path $CODEGATE_VEC_DB_FILE"

    # Check and append additional URLs if they are set
    [ -n "$CODEGATE_OPENAI_URL" ] && CMD_ARGS+=" --openai-url $CODEGATE_OPENAI_URL"
    [ -n "$CODEGATE_ANTHROPIC_URL" ] && CMD_ARGS+=" --anthropic-url $CODEGATE_ANTHROPIC_URL"
    [ -n "$CODEGATE_OLLAMA_URL" ] && CMD_ARGS+=" --ollama-url $CODEGATE_OLLAMA_URL"
    [ -n "$CODEGATE_VLLM_URL" ] && CMD_ARGS+=" --vllm-url $CODEGATE_VLLM_URL"
    [ -n "$CODEGATE_LM_STUDIO_URL" ] && CMD_ARGS+=" --lm-studio-url $CODEGATE_LM_STUDIO_URL"

    # Check and append debug level if set
    [ -n "$CODEGATE_APP_LOG_LEVEL" ] && CMD_ARGS+=" --log-level $CODEGATE_APP_LOG_LEVEL"
    [ -n "$CODEGATE_LOG_FORMAT" ] && CMD_ARGS+=" --log-format $CODEGATE_LOG_FORMAT"
    echo "Starting the application with args: $CMD_ARGS"

    exec python -m src.codegate.cli serve $CMD_ARGS
}

# Main execution flow
echo "Initializing entrypoint script..."


# Step 1: Restore backup if applicable
restore_backup

# Step 2: Generate certificates
generate_certs

# Step 3: Start the dashboard
start_dashboard

# Step 4: Start the main application
start_application
