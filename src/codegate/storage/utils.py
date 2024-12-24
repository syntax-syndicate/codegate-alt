import os
import shutil


def restore_storage_backup(backup_path: str, backup_name: str):
    """
    Restore a SQLite database backup.

    Args:
        backup_path: The directory containing the backup
        backup_name: The name of the backup file
    """
    backup_file = os.path.join(backup_path, backup_name)
    target_dir = "./sqlite_data"
    target_file = os.path.join(target_dir, "vectordb.db")

    if not os.path.exists(backup_file):
        print(f"Backup file not found: {backup_file}")
        return

    try:
        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)

        # Copy the backup file to the target location
        shutil.copy2(backup_file, target_file)
        print(f"Successfully restored backup from {backup_file}")
    except Exception as e:
        print(f"Failed to restore backup: {e}")
