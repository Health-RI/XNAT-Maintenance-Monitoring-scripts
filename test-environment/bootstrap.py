"""Finish the first-run setup of a fresh XNAT container.

A newly created XNAT has an unusable REST API: the admin password is unknown
and every request is redirected to the setup wizard. This script sets a known
admin password and marks the site as initialized, both directly in the
database, so the environment can be brought up without any manual clicking.

Only meant for a throwaway local test instance.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

import bcrypt

PREFERENCES = {
    "initialized": "true",
    "siteId": "XNATTEST",
    "adminEmail": "admin@example.org",
}


def psql(db_container: str, sql: str) -> str:
    result = subprocess.run(
        ["docker", "exec", db_container, "psql", "-U", "xnat", "-d", "xnat", "-tAc", sql],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main(db_container: str, xnat_container: str, admin_password: str, site_url: str) -> None:
    # XNAT stores passwords as bcrypt with the 2a prefix.
    hashed = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt(10, prefix=b"2a")).decode()

    psql(
        db_container,
        f"update xdat_user set primary_password='{{bcrypt}}{hashed}', enabled=1, verified=1 where login='admin';",
    )
    print("Set the admin password.")

    for name, value in {**PREFERENCES, "siteUrl": site_url}.items():
        psql(db_container, f"update xhbm_preference set value='{value}' where name='{name}';")
    print("Marked the site as initialized.")

    subprocess.run(["docker", "restart", xnat_container], check=True, stdout=subprocess.DEVNULL)
    print(f"Restarted {xnat_container}; XNAT needs a minute to come back up.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap a fresh XNAT test container")
    parser.add_argument("--db_container", default="xnat-test-db")
    parser.add_argument("--xnat_container", default="xnat-test")
    parser.add_argument("--admin_password", default="admin", help="Password to set for the admin account")
    parser.add_argument("--site_url", default="http://localhost:8080")
    args = parser.parse_args()

    try:
        main(args.db_container, args.xnat_container, args.admin_password, args.site_url)
    except subprocess.CalledProcessError as error:
        print(f"Error: {error.stderr or error}", file=sys.stderr)
        sys.exit(1)
