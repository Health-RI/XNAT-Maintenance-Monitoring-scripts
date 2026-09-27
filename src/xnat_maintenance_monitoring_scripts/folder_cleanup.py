import argparse
import os
from datetime import datetime

def cleanup(dir_path, retention_days):
    if not os.path.exists(dir_path):
        print(f"Stopping cleanup - path does not exist: {dir_path}")
        return

    if not os.path.isdir(dir_path):
        print(f"Stopping cleanup - path is not a directory: {dir_path}")
        return

    if os.path.islink(dir_path):
        print(f"Stopping cleanup - path is a symbolic link, : {dir_path}")
        return

    for entry in os.listdir(dir_path):
        entry_path = os.path.join(dir_path, entry)
        handle_path(entry_path, retention_days)

    if not os.listdir(dir_path):
        handle_directory_removal(dir_path, retention_days)

    print(f"Successfully cleaned up directory {dir_path} - with retention days: {retention_days}")


def handle_path(path, retention_days):
    if os.path.islink(path):
        print(f"Ignoring path - object is a symbolic link: {path}")
        return

    if os.path.isdir(path):
        handle_directory(path, retention_days)
    elif os.path.isfile(path):
        handle_file_removal(path, retention_days)


def handle_directory(dir_path, retention_days):
    if is_dir_empty(dir_path):
        handle_directory_removal(dir_path, retention_days)
        return

    for entry in os.listdir(dir_path):
        entry_path = os.path.join(dir_path, entry)
        handle_path(entry_path, retention_days)

    if is_dir_empty(dir_path):
        handle_directory_removal(dir_path, retention_days)


def handle_file_removal(file_path, retention_days):
    after_retention, last_modified_days = is_after_retention_period(file_path, retention_days)

    if not after_retention:
        print(f"File unchanged {file_path} - last modified {last_modified_days} days")
        return

    try:
        os.remove(file_path)
        print(f"Removed file {file_path} - last modified {last_modified_days} days")
    except OSError as e:
        print(f"Could not remove file {file_path}: {e}")


def handle_directory_removal(dir_path, retention_days):
    after_retention, last_modified_days = is_after_retention_period(dir_path, retention_days)

    if not after_retention:
        print(f"Directory unchanged {dir_path} - last modified {last_modified_days} days")
        return

    try:
        os.rmdir(dir_path)
        print(f"Removed directory {dir_path} - last modified {last_modified_days} days")
    except OSError as e:
        print(f"Could not remove directory or file {dir_path}: {e}")


def is_after_retention_period(path, retention_days):
    last_modified = datetime.fromtimestamp(os.path.getmtime(path))
    last_modified_days = (datetime.now() - last_modified).days

    if last_modified_days > retention_days:
        return True, last_modified_days
    else:
        return False, last_modified_days


def is_dir_empty(dir_path):
    if os.listdir(dir_path):
        return False
    else:
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean up old files in target folder (e.g: in XNAT cache, temp and deleted folders)')
    parser.add_argument('--dir_path', type=str, required=True,
                        help='Path to directory to clean up')
    parser.add_argument('--retention_days', type=int, default=90,
                        help='Retention period in days, every file and empty directory older than this value will be cleaned up (default: 90)')
    args = parser.parse_args()

    cleanup(args.dir_path, args.retention_days)
