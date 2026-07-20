import argparse
import getpass
from datetime import datetime
from pathlib import Path

import xnat

# The on-disk prearchive folder layout is <prearchive_root>/<project>/<timestamp>/<leaf-folder>.
# Whether <leaf-folder> matches folder_name (JSON field "folderName") or name/label has not been
# verified against a real XNAT server (xnatpy's own test fixtures use mismatched dummy values for
# these fields). This constant is the single place to change if verification against a local test
# XNAT instance shows "name" is correct instead.
PREARCHIVE_FOLDER_FIELD = "folder_name"

def main(xnat_url, username, password, project, retention_days, prearchive_path):
    with xnat.connect(xnat_url, user=username, password=password) as session:
        print(f"Connected to {xnat_url}")
        cleanup_prearchive(session, project, retention_days, prearchive_path)
        print("Disconnected.")

def cleanup_prearchive(xnat_session, project, retention_days, prearchive_path):
    now = datetime.now()
    project_filter = "unassigned"
    sessions = list_prearchive_sessions(xnat_session, project_filter)
    expired_sessions = filter_expired_sessions(sessions, retention_days, now)

    checked = len(expired_sessions)
    deleted = 0
    disk_warnings = 0
    errors = 0

    for prearchive_session in expired_sessions:
        result = delete_prearchive_session(prearchive_session)
        if result["error"] is not None:
            errors += 1
        else:
            deleted += 1
            if not result["disk_verified"]:
                disk_warnings += 1

    print(
        f"Prearchive cleanup for project filter '{project}' complete: "
        f"{checked} checked, {deleted} deleted, {disk_warnings} disk warning(s), {errors} error(s)."
    )

    return {"checked": checked, "deleted": deleted, "disk_warnings": disk_warnings, "errors": errors}

def list_prearchive_sessions(xnat_session, project_filter):
    return xnat_session.prearchive.sessions(project=project_filter)

def is_expired(timestamp, retention_days, current_timestamp):
    age_days = (current_timestamp - timestamp).days
    return age_days > retention_days

def filter_expired_sessions(sessions, retention_days, now):
    return [session for session in sessions if is_expired(session.timestamp, retention_days, now)]

def build_prearchive_disk_path(prearchive_path, project, timestamp_raw, folder_name):
    return Path(prearchive_path) / project / timestamp_raw / folder_name

def delete_prearchive_session(prearchive_session):
    try:
        prearchive_session.delete(asynchronous=False)
        print(f"Session deleted: {prearchive_session.session_id}")
        return None
    except Exception as e:
        print(f"Session deletion failed: {prearchive_session.session_id} - error: {e}")
        return e

def is_disk_path_deleted(disk_path):
    return not disk_path.exists()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove old XNAT prearchive uploads and verify removal from disk")
    parser.add_argument("--xnat_url", type=str, required=True,
                        help="URL for the XNAT instance (e.g., https://xnat.health-ri.nl)")
    parser.add_argument("--project", type=str, default="unassigned",
                        help="Project to filter prearchive sessions by. Use a specific project ID to target only "
                             "that project, 'unassigned' to target uploads that were not associated with a project "
                             "(default), or 'all' to process every project including 'unassigned'.")
    parser.add_argument("--retention_days", type=int, default=90,
                        help="Retention period in days; prearchive sessions with an upload timestamp older than "
                             "this will be removed (default: 90)")
    parser.add_argument("--project_root", type=str, required=True,
                        help="Absolute path to the XNAT prearchive path directory on disk (e.g., "
                             "/data/xnat/prearchive), used to verify that deleted sessions are actually gone "
                             "from disk. Must be reachable from wherever this script runs.")
    args = parser.parse_args()

    # Prompt for username and password
    username = input("Enter your XNAT username: ")
    password = getpass.getpass("Enter your XNAT password: ")

    main(args.xnat_url, username, password, args.project, args.retention_days, args.project_root)
