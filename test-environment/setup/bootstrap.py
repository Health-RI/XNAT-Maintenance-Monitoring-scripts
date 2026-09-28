"""Finish the first-run setup of a fresh XNAT container.

A newly created XNAT has an unusable REST API: the admin password is unknown
and every request is redirected to the setup wizard. This script sets a known
admin password and marks the site as initialized, both directly in the
database, so the environment can be brought up without any manual clicking.

Runs as the `xnat-setup` compose service and exits once the REST API answers,
so other services can wait on it with `service_completed_successfully`. It is
idempotent: on an already-bootstrapped instance it only waits.

Only meant for a throwaway local test instance.
"""

from __future__ import annotations

import os
import subprocess
import sys

import bcrypt
import pg8000.dbapi
from wait_for_api import wait_for_api, wait_for_tomcat

# XNAT_DATA in docker-compose.yml; the data volume is mounted here.
XNAT_DATA = "/xnatdata"

# XNAT verifies these at startup and refuses to come up cleanly if they do not
# exist. They default to /data/xnat/..., which is not where the volume is
# mounted, so they have to be pointed at XNAT_DATA explicitly.
PATH_PREFERENCES = {
    "archivePath": f"{XNAT_DATA}/archive",
    "prearchivePath": f"{XNAT_DATA}/prearchive",
    "cachePath": f"{XNAT_DATA}/cache",
    "buildPath": f"{XNAT_DATA}/build",
    "ftpPath": f"{XNAT_DATA}/ftp",
    "pipelinePath": f"{XNAT_DATA}/pipeline",
    "inboxPath": f"{XNAT_DATA}/prearchive/inbox",
}

PREFERENCES = {
    "initialized": "true",
    "siteId": "XNATTEST",
    "adminEmail": "admin@example.org",
}

# Work factor for the admin password hash. The cost is stored in the hash
# itself, so XNAT re-derives it when verifying; 12 is the current baseline for
# bcrypt and costs a fraction of a second here.
BCRYPT_ROUNDS = 12


def connect(host: str, name: str, user: str, password: str):
    return pg8000.dbapi.connect(host=host, database=name, user=user, password=password)


def already_initialized(connection) -> bool:
    cursor = connection.cursor()
    cursor.execute("select value from xhbm_preference where name = 'initialized';")
    row = cursor.fetchone()
    cursor.close()
    return bool(row) and row[0] == "true"


def set_preferences(connection, preferences: dict[str, str]) -> None:
    cursor = connection.cursor()
    for name, value in preferences.items():
        cursor.execute("update xhbm_preference set value = %s where name = %s;", (value, name))
    cursor.close()
    connection.commit()


def set_admin_password(connection, password: str) -> None:
    # XNAT stores passwords as bcrypt with the 2a prefix.
    salt = bcrypt.gensalt(BCRYPT_ROUNDS, prefix=b"2a")
    hashed = bcrypt.hashpw(password.encode(), salt).decode()
    cursor = connection.cursor()
    cursor.execute(
        "update xdat_user set primary_password = %s, enabled = 1, verified = 1 where login = 'admin';",
        (f"{{bcrypt}}{hashed}",),
    )
    cursor.close()
    connection.commit()


def docker(*arguments: str) -> None:
    subprocess.run(["docker", *arguments], check=True, stdout=subprocess.DEVNULL)


def main() -> None:
    xnat_url = os.environ["XNAT_URL"]
    xnat_container = os.environ["XNAT_CONTAINER"]
    admin_password = os.environ["ADMIN_PASSWORD"]
    site_url = os.environ["SITE_URL"]

    # The database schema is only created once XNAT itself has started, so the
    # preferences cannot be written before that.
    wait_for_tomcat(xnat_url)

    connection = connect(
        os.environ["DB_HOST"],
        os.environ["DB_NAME"],
        os.environ["DB_USER"],
        os.environ["DB_PASSWORD"],
    )

    try:
        if already_initialized(connection):
            print("XNAT is already bootstrapped; waiting for the REST API.")
        else:
            # The data directories must exist before XNAT verifies them on startup.
            docker("exec", xnat_container, "mkdir", "-p", *PATH_PREFERENCES.values())
            print("Created the data directories.")

            set_admin_password(connection, admin_password)
            print("Set the admin password.")

            set_preferences(connection, {**PATH_PREFERENCES, **PREFERENCES, "siteUrl": site_url})
            print("Set the data paths and marked the site as initialized.")

            docker("restart", xnat_container)
            print(f"Restarted {xnat_container}.")
    finally:
        connection.close()

    wait_for_api(xnat_url, "admin", admin_password)


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, TimeoutError, pg8000.dbapi.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
