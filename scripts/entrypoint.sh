#!/bin/bash
DEFAULT_VLLM_URL="https://inference.codegate.ai"
VLLM_URL=${VLLM_URL:-$DEFAULT_VLLM_URL}

# Parse arguments
BACKUP_PATH=$1
BACKUP_MODE=$2

# Function to restore backup if paths are provided
restore_backup() {
    if [ -n "$BACKUP_PATH" ] && [ -n "$BACKUP_MODE" ]; then
        if [ -d "$BACKUP_PATH" ] && [ -d "$BACKUP_PATH/$BACKUP_MODE" ]; then
            echo "Restoring backup from $BACKUP_PATH/$BACKUP_MODE..."
            python -m src.codegate.cli restore-backup --backup-path "$BACKUP_PATH" --backup-name "$BACKUP_MODE"
        else
            echo "No backup found at $BACKUP_PATH/$BACKUP_MODE. Skipping restore."
        fi
    else
        echo "Backup path or mode not provided. Skipping restore."
    fi
}

# Function to start Nginx server for the dashboard
start_dashboard() {
    echo "Starting the dashboard..."
    nginx -g 'daemon off;' &
}

# Function to start the main application
start_application() {
    echo "Starting the application with VLLM URL: $VLLM_URL"
    exec python -m src.codegate.cli serve --port 8989 --host 0.0.0.0 --vllm-url "$VLLM_URL" --model-base-path /app/models
}

# Main execution flow
echo "Initializing entrypoint script..."

# Step 1: Restore backup if applicable
restore_backup

# Step 2: Start the dashboard
start_dashboard

# Step 3: Start the main application
start_application