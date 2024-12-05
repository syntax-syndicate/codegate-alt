#!/bin/bash

# Check if the backup directory exists and handle the restore
if [ -d "$1" ] && [ -d "$1/$2" ]; then
    echo "Restoring backup from $1/$2..."
    # Your restore logic here, e.g., running a Python script or restoring a database
    python -m src.codegate.cli restore-backup --backup-path "$1" --backup-name "$2"
else
    echo "No backup found at $1/$2. Skipping restore."
fi

# Step 2: Start the main application (serve)
echo "Starting the application..."
exec python -m src.codegate.cli serve --port 8989 --host 0.0.0.0 --vllm-url https://inference.codegate.ai

# Step 3: Start the Nginx server with FE
nginx -g 'daemon off;'
