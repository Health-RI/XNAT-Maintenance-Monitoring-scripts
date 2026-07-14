import argparse
import errno, os, stat, sys
import shutil
from datetime import datetime

def cleanup(dir_path, retention_days):
    if not os.path.exists(dir_path):
        print(f"Path does not exist: {dir_path}")
        return

    if not os.path.isdir(dir_path):
        print(f"Path is not a directory: {dir_path}")
        return

    for entry in os.listdir(dir_path):
        entry_path = os.path.join(dir_path, entry)
        handle_path(entry_path, retention_days)

    print(f"Cleaned up {dir_path}")


def handle_path(path, retention_days):
    if os.path.isdir(path):
        handle_directory(path, retention_days)
    elif os.path.isfile(path):
        handle_file_removal(path, retention_days)


def handle_directory(directory, retention_days):
    contents = os.listdir(directory)
    if not contents:
        handle_directory_removal(directory)
        return

    for entry in contents:
        entry_path = os.path.join(directory, entry)
        handle_path(entry_path, retention_days)

    if not os.listdir(directory):
        handle_directory_removal(directory)

def handle_file_removal(file_path, retention_days):
    last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
    last_modified_days = (datetime.now() - last_modified).days
    if last_modified_days <= retention_days:
        return

    try:
        os.remove(file_path)
    except OSError:
        try:
            remove_readonly(os.remove, file_path, sys.exc_info())
        except OSError as e:
            print(f"Could not remove file {file_path}: {e}")
            return

    print(f"Removed file {file_path} - last modified {last_modified_days} days")

def handle_directory_removal(path):
    try:
        shutil.rmtree(path, ignore_errors=False, onerror=remove_readonly)
        print(f"Removed directory {path}")
    except OSError as e:
        print(f"Could not remove directory or file {path}: {e}")

def remove_readonly(func, path, exc):
    # onerror callback for shutil.rmtree: whenever a delete fails partway through the tree, instead of aborting the whole rmtree.
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
      # Windows marks some OneDrive files read-only, which makes rmdir/remove raise
      # "access denied" (EACCES). Clearing the attribute and retrying fixes that case.
      os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
      func(path)
    else:
      # Not a read-only issue (e.g. an ACL delete-deny) - re-raise the original exception.
      # Works because rmtree calls onerror() from inside its own except block, so the
      # exception context is still live for a bare `raise` to pick up.
      raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean up old files in target folder (e.g: in XNAT cache, temp and deleted folders)')
    parser.add_argument('--dir_path', type=str, required=True,
                        help='Path to directory to clean up')
    parser.add_argument('--retention_days', type=int, default=90,
                        help='Retention period in days, every file and empty directory older than this value will be cleaned up (default: 90)')
    args = parser.parse_args()

    cleanup(args.dir_path, args.retention_days)
